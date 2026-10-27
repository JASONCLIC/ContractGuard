"""
QA-based contract summary extractor.

Field assignment strategy
─────────────────────────
ENTITY fields  (short spans — QA wins)
  party_a, party_b, job_title, work_location, salary_amount, payment_cycle

CLAUSE fields  (full paragraphs — regex wins, QA is unreliable here because
  extractive QA models return only short answer spans, not entire sections)
  contract_name, probation, contract_term,
  termination_conditions, breach_liability, dispute_resolution

Model: deepset/roberta-base-squad2  (~498 MB, F1=82.9 on SQuAD2)
  Replaced deepset/minilm-uncased-squad2 (F1=78.0) for better accuracy on
  legal / contract language.
"""

import logging
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional

from .ner_extractor import extract_key_info as _regex_extract
from .ner_questions import FIELD_QUESTIONS

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

# Only run the QA model on these fields; all others fall back to regex only.
ENTITY_FIELDS = {"party_a", "party_b", "job_title", "work_location",
                 "salary_amount", "payment_cycle"}

# Minimum score for QA to override a non-empty regex result.
# (A low threshold means "trust QA even when regex already found something".)
QA_PREFER_THRESHOLD = 0.35

# Minimum score to use QA when regex returns "Not identified".
QA_FALLBACK_THRESHOLD = 0.15

# Context window fed to the model per query (RoBERTa max 512 tokens ≈ 1800 chars).
CHUNK_SIZE  = 1800
CHUNK_OVERLAP = 200

_MODEL_NAME = str(Path(__file__).resolve().parents[2] / "models" / "ner_qa_finetuned")

# Mapping: entity field → clause categories most likely to contain the answer.
# Category values are provided by bert_clause_classifier.annotate_clauses().
_FIELD_TO_CLAUSE_CATEGORIES: Dict[str, List[str]] = {
    "salary_amount":  ["salary"],
    "payment_cycle":  ["salary"],
    "work_location":  ["work_location"],
    # party_a, party_b, job_title are typically in the preamble (not a specific
    # clause category), so they skip clause-guided search and go straight to
    # full-text QA.
}

# When building focused context from clauses, limit total chars to avoid
# exceeding the model's token budget while still being broader than a single chunk.
_FOCUSED_CONTEXT_MAX_CHARS = 3000


def _build_focused_context(
    clauses: List[Dict], target_categories: List[str],
) -> Optional[str]:
    """
    Concatenate the content of clauses whose ``category`` matches one of
    *target_categories*.  Returns None if no matching clauses are found.
    """
    parts: List[str] = []
    total = 0
    for c in clauses:
        cat = c.get("category", "general")
        if cat in target_categories:
            content = c.get("content", "")
            if total + len(content) > _FOCUSED_CONTEXT_MAX_CHARS:
                break
            parts.append(content)
            total += len(content)
    return "\n".join(parts) if parts else None


# ── Singleton pipeline ────────────────────────────────────────────────────────

_lock = threading.Lock()
_qa_pipeline = None


def _get_pipeline():
    global _qa_pipeline
    if _qa_pipeline is None:
        with _lock:
            if _qa_pipeline is None:
                try:
                    from transformers import pipeline as hf_pipeline
                    logger.info("Loading QA NER model: %s", _MODEL_NAME)
                    _qa_pipeline = hf_pipeline(
                        "question-answering",
                        model=_MODEL_NAME,
                        tokenizer=_MODEL_NAME,
                        device=-1,   # CPU; switch to 0 for GPU
                    )
                    logger.info("QA NER model loaded.")
                except Exception as exc:
                    logger.warning("Failed to load QA model: %s", exc)
    return _qa_pipeline


# ── Chunking ──────────────────────────────────────────────────────────────────

def _chunks(text: str):
    """Overlapping character-level windows over the contract text."""
    start = 0
    while start < len(text):
        yield text[start: start + CHUNK_SIZE]
        if start + CHUNK_SIZE >= len(text):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP


# ── Answer retrieval ──────────────────────────────────────────────────────────

def _best_qa_answer(qa, questions, text: str):
    """
    Ask each question over every chunk; return (score, answer) for the
    answer with the highest confidence, or (0.0, None) if none found.
    """
    best_score  = 0.0
    best_answer = None

    for question in questions:
        for chunk in _chunks(text):
            try:
                result = qa(question=question, context=chunk)
            except Exception:
                continue
            if result["score"] > best_score and result["answer"].strip():
                best_score  = result["score"]
                best_answer = result["answer"].strip()

    return best_score, best_answer


# ── Answer validators ─────────────────────────────────────────────────────────

# Generic / vague answers the model sometimes produces
_INVALID_ANSWERS = {
    "employee", "employer", "intern", "party a", "party b", "party",
    "company", "the employee", "the employer", "the company",
    "n/a", "not specified", "not applicable",
}

# Salary answers must contain a currency symbol + digits.
# Covers: "USD 145,000" / "£62,000" / "145,000 AUD" / "5,200 EUR per month"
_CURRENCY_RE = re.compile(
    r"(?:"
    r"(?:GBP|USD|EUR|RMB|CNY|SGD|AUD|CAD|HKD|JPY|INR|£|\$|€|¥)\s*[\d,\.]+"  # currency before
    r"|[\d,\.]+\s*(?:GBP|USD|EUR|RMB|CNY|SGD|AUD|CAD|HKD|JPY|INR|£|\$|€|¥)"  # currency after
    r")",
    re.IGNORECASE,
)

# Payment-cycle answers must contain a frequency keyword
_PAYMENT_CYCLE_RE = re.compile(
    r"monthly|weekly|bi.?weekly|fortnightly|daily"
    r"|last\s+working\s+day|end\s+of\s+(?:each\s+)?month"
    r"|\d+(?:st|nd|rd|th)\s+of\s+(?:each\s+)?month",
    re.IGNORECASE,
)


def _is_valid(field: str, answer: str) -> bool:
    """Return True only when the QA answer looks like a real value."""
    if not answer or len(answer.strip()) < 2:
        return False
    lo = answer.strip().lower()

    # Bare article headings ("Article 9", "Section 3")
    if re.match(r'^(article|section|clause)\s+\d+$', lo):
        return False
    # Generic role / placeholder words
    if lo in _INVALID_ANSWERS:
        return False
    # Signature-block artefacts
    if re.search(r'_{4,}|(?:Signature|Witness|Date)\s*:?', answer, re.IGNORECASE):
        return False
    if answer.count('_') > len(answer) * 0.25:
        return False

    # Field-specific rules
    if field == "salary_amount":
        return bool(_CURRENCY_RE.search(answer))
    if field == "payment_cycle":
        return bool(_PAYMENT_CYCLE_RE.search(answer))

    return True


# ── Answer post-processing ────────────────────────────────────────────────────

# Prefixes the QA model sometimes returns along with the real value
_LABEL_PREFIX_RE = re.compile(
    r"^(?:employer|company|employee|intern|party\s*[ab\d]|position|role|title"
    r"|job\s*title|work\s*location|address|salary|remuneration|compensation"
    r"|employer\s*name|employee\s*name|name)\s*[:：]\s*",
    re.IGNORECASE,
)

# Long descriptive suffixes after a company name or job title
# e.g. "Horizon Technologies Inc., a Delaware corporation with principal..."
_COMPANY_SUFFIX_RE = re.compile(
    r",\s*(?:a\s+(?:\w+\s+){0,3}(?:corporation|company|ltd|llp|plc|inc|gmbh|pty|pte)"
    r"|\bregistered\b|\blocated\b|\bwith\s+its\b|\bherein)",
    re.IGNORECASE,
)


def _clean_answer(field: str, answer: str) -> str:
    """
    Strip common noise patterns from QA answers for short entity fields.
    Applied AFTER validation so we don't accidentally validate the cleaned form.
    """
    s = answer.strip()

    # Remove label prefixes ("Employer: Horizon Tech" → "Horizon Tech")
    s = _LABEL_PREFIX_RE.sub("", s).strip()

    if field == "party_a":
        # Trim long descriptions after company name
        m = _COMPANY_SUFFIX_RE.search(s)
        if m:
            s = s[:m.start()].strip()
        # Cap length – company names rarely exceed 80 chars
        if len(s) > 80:
            s = s[:80].rsplit(" ", 1)[0]

    elif field == "job_title":
        # "employed as a Senior Data Scientist" → "Senior Data Scientist"
        s = re.sub(r"^(?:employed\s+as\s+(?:an?\s+)?|appointed\s+as\s+(?:an?\s+)?|"
                   r"serving\s+as\s+(?:an?\s+)?|is\s+(?:an?\s+)?)", "", s, flags=re.IGNORECASE)
        # Cap length – job titles rarely exceed 60 chars
        if len(s) > 60:
            s = s[:60].rsplit(" ", 1)[0]

    elif field == "party_b":
        # Names rarely exceed 50 chars
        if len(s) > 50:
            s = s[:50].rsplit(" ", 1)[0]

    elif field == "salary_amount":
        # Extract just the currency+amount span if the model returned a sentence
        m = _CURRENCY_RE.search(s)
        if m:
            # Try to grab a slightly wider span (e.g. "USD 145,000 per year")
            start = max(0, m.start() - 4)
            end   = min(len(s), m.end() + 15)
            candidate = s[start:end].strip().rstrip(".,;")
            s = candidate
        else:
            # Chinese-style salary expressions often look like "15000元/月".
            # For evaluation consistency and DB historical labels, keep plain digits.
            m_cn = re.search(r"(\d[\d,\.]*)\s*(?:元|人民币)\s*(?:/月|每月|月)?", s)
            if m_cn:
                s = m_cn.group(1).replace(",", "").strip()

    return s.strip()


# ── Merge logic ───────────────────────────────────────────────────────────────

def _should_use_qa(field: str, score: float, qa_answer: str,
                   regex_answer: str) -> bool:
    """
    Decide whether to accept the QA answer for this field.

    Rules (entity fields only):
    • regex returned nothing  → accept QA if score ≥ QA_FALLBACK_THRESHOLD
    • regex returned something → accept QA if score ≥ QA_PREFER_THRESHOLD
      AND qa_answer is not obviously shorter / worse than regex result
    """
    regex_empty = regex_answer in (None, "", "Not identified")

    threshold = QA_FALLBACK_THRESHOLD if regex_empty else QA_PREFER_THRESHOLD
    if score < threshold:
        return False

    # If regex already has a good answer, QA must bring real added value
    if not regex_empty:
        if field == "job_title" and re.search(r"(岗位|职位|job\s*title|position)", regex_answer, re.IGNORECASE):
            # Regex title patterns are highly reliable; avoid QA overriding with
            # unrelated clause fragments.
            return False
        # For identity/title fields regex is usually more stable on fixed contract headers.
        # Only override when QA confidence is clearly strong.
        if field in {"party_a", "party_b", "job_title"} and score < 0.75:
            return False
        # Reject if QA is just a bare number (e.g. "90" for termination days)
        if re.match(r'^\d+$', qa_answer.strip()):
            return False
        # Reject if QA answer is a strict substring of regex (no new info)
        if qa_answer.strip().lower() in regex_answer.strip().lower():
            return False

    return True


# ── Public API ────────────────────────────────────────────────────────────────

def extract_key_info_qa(
    text: str,
    clauses: Optional[List[Dict]] = None,
) -> Dict[str, str]:
    """
    Extract all 12 summary fields.

    Entity fields  → QA model (roberta-base-squad2) with regex fallback.
    Clause fields  → regex only (_article_content is more reliable for full paragraphs).

    If *clauses* are provided (each dict must have ``category`` and ``content``
    keys, as produced by pipeline._segment_clauses + classify_clause), entity
    extraction uses a two-stage strategy:
      Stage 1 – run QA on the focused clause text (e.g. only "salary" clauses
                for salary_amount).  Narrower context → less noise.
      Stage 2 – if Stage 1 fails, fall back to full-text sliding-window QA.
    """
    regex_result = _regex_extract(text)

    qa = _get_pipeline()
    if qa is None:
        logger.warning("QA model unavailable; using regex-only extraction.")
        return regex_result

    merged: Dict[str, str] = {}

    for field in FIELD_QUESTIONS:
        regex_answer = regex_result.get(field) or "Not identified"

        if field not in ENTITY_FIELDS:
            merged[field] = regex_answer
            continue

        # ── Stage 1: clause-guided focused QA ─────────────────────────────
        score, qa_answer = 0.0, None
        if clauses and field in _FIELD_TO_CLAUSE_CATEGORIES:
            focused = _build_focused_context(
                clauses, _FIELD_TO_CLAUSE_CATEGORIES[field],
            )
            if focused:
                score, qa_answer = _best_qa_answer(
                    qa, FIELD_QUESTIONS[field], focused,
                )
                if qa_answer:
                    logger.debug(
                        "Field '%s' Stage-1 (focused) score=%.2f answer='%s'",
                        field, score, qa_answer[:80],
                    )

        # ── Stage 2: full-text fallback ───────────────────────────────────
        if not (qa_answer and _is_valid(field, qa_answer)
                and _should_use_qa(field, score, qa_answer, regex_answer)):
            score, qa_answer = _best_qa_answer(
                qa, FIELD_QUESTIONS[field], text,
            )

        # ── Merge decision ────────────────────────────────────────────────
        if qa_answer and _is_valid(field, qa_answer) \
                and _should_use_qa(field, score, qa_answer, regex_answer):
            cleaned = _clean_answer(field, qa_answer)
            merged[field] = cleaned if cleaned else regex_answer
            logger.debug(
                "Field '%s' QA (%.2f): '%s' → cleaned '%s'  [regex was '%s']",
                field, score, qa_answer[:80], cleaned[:80], regex_answer[:80],
            )
        else:
            # Apply the same cleaner to regex fallback for better format consistency.
            merged[field] = _clean_answer(field, regex_answer) if field in ENTITY_FIELDS else regex_answer

    return merged
