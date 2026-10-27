import json
import logging
import re
import socket
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from typing import Callable, Dict, List, Optional, Tuple
from urllib import error, request

from flask import current_app
from .desensitizer import desensitize_text

logger = logging.getLogger(__name__)


def _build_ssl_context():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _strip_markdown(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"`{1,3}", "", cleaned)
    cleaned = re.sub(r"[*#>-]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _truncate_words(text: str, max_words: int = 200) -> str:
    words = (text or "").split()
    if len(words) <= max_words:
        return text
    trimmed = " ".join(words[:max_words]).strip()
    dot = trimmed.rfind(".")
    if dot > 0:
        return trimmed[: dot + 1]
    return trimmed


def _postprocess_output(text: str) -> str:
    cleaned = _strip_markdown(text)
    cleaned = _truncate_words(cleaned, max_words=200)
    return cleaned


def _build_messages(clause_text: str, risk_type: str, risk_level: str) -> List[Dict]:
    system_prompt = (
        "You are a legal risk analyst specialising in employment contracts. "
        "Your task is to explain why a specific clause in an employment contract "
        "poses a risk to the employee. Write in clear, accessible English that "
        "a non-lawyer can understand."
    )
    user_prompt = (
        f'The following clause from an employment contract has been flagged as a "{risk_type}" '
        f"risk (severity: {risk_level}).\n\n"
        f"── Clause Text ──\n{clause_text[:800]}\n──────────────────\n\n"
        "Please provide a concise explanation (3-5 sentences) that:\n"
        "1. Identifies the specific wording or provisions in this clause that create the risk.\n"
        "2. Explains the practical impact on the employee.\n"
        "3. Suggests what the employee could negotiate or look out for.\n\n"
        "Do not paste the full clause text. You may quote at most one short phrase "
        "(<=12 words) from the clause. Do not provide formal legal advice."
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _chat_completion(messages: List[Dict], cfg: Dict) -> Tuple[Optional[str], Optional[str]]:
    base_url = (cfg.get("LLM_BASE_URL") or "").rstrip("/")
    api_key = cfg.get("LLM_API_KEY") or ""
    model = cfg.get("LLM_MODEL", "qwen3.5-flash")
    timeout = int(cfg.get("LLM_TIMEOUT", 8))
    max_tokens = int(cfg.get("LLM_MAX_TOKENS", 300))
    temperature = float(cfg.get("LLM_TEMPERATURE", 0.3))
    retry_count = int(cfg.get("LLM_RETRY_COUNT", 1))

    if not api_key:
        return None, "invalid_api_key"

    endpoint = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    for attempt in range(retry_count + 1):
        req = request.Request(endpoint, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=timeout, context=_build_ssl_context()) as resp:
                raw = resp.read().decode("utf-8")
                body = json.loads(raw)
                content = (
                    (((body.get("choices") or [{}])[0].get("message") or {}).get("content"))
                    or ""
                )
                if content:
                    return content, None
                return None, "provider_error"
        except error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            logger.warning(
                "LLM HTTP error status=%s model=%s endpoint=%s body=%s",
                exc.code,
                model,
                endpoint,
                body[:500],
            )
            if exc.code in (429, 500, 502, 503, 504) and attempt < retry_count:
                time.sleep(0.5 * (2 ** attempt))
                continue
            return None, "provider_error"
        except error.URLError as exc:
            reason = str(getattr(exc, "reason", "")).lower()
            logger.warning("LLM URL error model=%s endpoint=%s reason=%s", model, endpoint, reason)
            if "timed out" in reason:
                return None, "timeout"
            return None, "network_error"
        except (socket.timeout, TimeoutError):
            logger.warning("LLM socket timeout model=%s endpoint=%s timeout=%ss", model, endpoint, timeout)
            return None, "timeout"
        except Exception as exc:
            logger.exception("LLM unexpected error model=%s endpoint=%s error=%s", model, endpoint, exc)
            return None, "provider_error"

    return None, "provider_error"


def explain_risk(
    clause_text: str,
    risk_type: str,
    risk_level: str,
    static_explanation: str,
    cfg: Optional[Dict] = None,
) -> Dict:
    runtime_cfg = cfg or current_app.config
    enabled = bool(runtime_cfg.get("LLM_ENABLED", True))
    if not enabled:
        return {
            "llm_explanation": None,
            "llm_status": "skipped",
            "llm_error_code": None,
            "llm_latency_ms": None,
        }

    started = time.time()
    messages = _build_messages(clause_text=clause_text, risk_type=risk_type, risk_level=risk_level)
    content, err = _chat_completion(messages, runtime_cfg)
    latency_ms = int((time.time() - started) * 1000)

    if err == "invalid_api_key":
        return {
            "llm_explanation": None,
            "llm_status": "skipped",
            "llm_error_code": "invalid_api_key",
            "llm_latency_ms": latency_ms,
        }

    if content:
        final_text = _postprocess_output(content)
        if len(final_text.split()) >= 10:
            return {
                "llm_explanation": final_text,
                "llm_status": "generated",
                "llm_error_code": None,
                "llm_latency_ms": latency_ms,
            }

    # keep static_explanation in signature for explicit fallback contract
    _ = static_explanation
    return {
        "llm_explanation": None,
        "llm_status": "fallback_static",
        "llm_error_code": err or "provider_error",
        "llm_latency_ms": latency_ms,
    }


def explain_risks_batch(
    risks: List[Dict],
    clauses: List[Dict],
    progress_callback: Optional[Callable[[int, str], None]] = None,
    progress_start: int = 75,
    progress_end: int = 90,
) -> List[Dict]:
    if not risks:
        if progress_callback:
            progress_callback(progress_end, "Risk explanation completed")
        return risks

    cfg = dict(current_app.config)
    clause_map = {int(c.get("index_num", -1)): (c.get("content") or "") for c in clauses or []}
    timeout_sec = int(cfg.get("LLM_CONTRACT_TIMEOUT", 30))
    max_workers = max(1, int(cfg.get("LLM_MAX_CONCURRENCY", 3)))

    def _run_one(risk: Dict) -> Dict:
        idx = int(risk.get("index_num", -1))
        clause_text = clause_map.get(idx) or (risk.get("evidence_sentence") or "")
        clause_text = desensitize_text(str(clause_text)).redacted_text
        return explain_risk(
            clause_text=clause_text,
            risk_type=str(risk.get("risk_type", "")),
            risk_level=str(risk.get("risk_level", "")),
            static_explanation=str(risk.get("explanation", "")),
            cfg=cfg,
        )

    future_to_idx: Dict = {}
    total = len(risks)
    done = 0
    if progress_callback:
        progress_callback(progress_start, f"Generating risk explanations (0/{total})")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i, risk in enumerate(risks):
            future_to_idx[executor.submit(_run_one, risk)] = i

        done_indexes = set()
        try:
            for future in as_completed(future_to_idx, timeout=timeout_sec):
                i = future_to_idx[future]
                done_indexes.add(i)
                try:
                    payload = future.result()
                except Exception:
                    payload = {
                        "llm_explanation": None,
                        "llm_status": "fallback_static",
                        "llm_error_code": "provider_error",
                        "llm_latency_ms": None,
                    }
                risks[i].update(payload)
                done += 1
                if progress_callback:
                    percent = progress_start + int((progress_end - progress_start) * (done / max(1, total)))
                    progress_callback(percent, f"Generating risk explanations ({done}/{total})")
        except TimeoutError:
            pass

        for future, i in future_to_idx.items():
            if i in done_indexes:
                continue
            future.cancel()
            risks[i].update(
                {
                    "llm_explanation": None,
                    "llm_status": "fallback_static",
                    "llm_error_code": "contract_timeout",
                    "llm_latency_ms": None,
                }
            )

    if progress_callback:
        progress_callback(progress_end, "Risk explanation completed")
    return risks
