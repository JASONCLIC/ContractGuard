"""
Unit tests for backend/app/services/llm_explainer.py.

Approach: monkeypatch `_chat_completion` to deterministically return
(content, error_code) for each scenario, so the tests verify the explain_risk
status machine without calling the real Qwen API.
"""

from __future__ import annotations

import pytest


from backend.app.services import llm_explainer


# ── explain_risk ─────────────────────────────────────────────────────────────


def _cfg(**overrides):
    base = {
        "LLM_ENABLED": True,
        "LLM_API_KEY": "test-key",
        "LLM_BASE_URL": "https://example.invalid/v1",
        "LLM_MODEL": "qwen3.5-flash",
        "LLM_TIMEOUT": 5,
        "LLM_MAX_TOKENS": 200,
        "LLM_TEMPERATURE": 0.3,
        "LLM_RETRY_COUNT": 0,
        "LLM_CONTRACT_TIMEOUT": 5,
        "LLM_MAX_CONCURRENCY": 2,
    }
    base.update(overrides)
    return base


def test_explain_risk_skipped_when_disabled():
    out = llm_explainer.explain_risk(
        clause_text="Either party may terminate at will.",
        risk_type="vague_termination",
        risk_level="high",
        static_explanation="default static explanation",
        cfg=_cfg(LLM_ENABLED=False),
    )
    assert out["llm_explanation"] is None
    assert out["llm_status"] == "skipped"
    assert out["llm_error_code"] is None
    assert out["llm_latency_ms"] is None


def test_explain_risk_invalid_api_key(monkeypatch):
    monkeypatch.setattr(
        llm_explainer, "_chat_completion", lambda messages, cfg: (None, "invalid_api_key")
    )
    out = llm_explainer.explain_risk(
        clause_text="x", risk_type="x", risk_level="high",
        static_explanation="static", cfg=_cfg(LLM_API_KEY=""),
    )
    assert out["llm_status"] == "skipped"
    assert out["llm_error_code"] == "invalid_api_key"
    assert out["llm_explanation"] is None


def test_explain_risk_generated_when_provider_returns_content(monkeypatch):
    long_response = (
        "This clause shifts liability entirely onto the employee. "
        "It removes any recourse for unpaid wages. "
        "Negotiate to add a written notice period."
    )
    monkeypatch.setattr(
        llm_explainer, "_chat_completion", lambda messages, cfg: (long_response, None)
    )
    out = llm_explainer.explain_risk(
        clause_text="The employee bears all risks without remedy.",
        risk_type="unilateral_exemption",
        risk_level="high",
        static_explanation="static fallback",
        cfg=_cfg(),
    )
    assert out["llm_status"] == "generated"
    assert out["llm_explanation"] is not None
    assert len(out["llm_explanation"].split()) >= 10
    # Markdown chars should be stripped
    assert "*" not in out["llm_explanation"]
    assert "#" not in out["llm_explanation"]


def test_explain_risk_short_content_falls_back(monkeypatch):
    """LLM returns < 10 words → status should drop to fallback_static."""
    monkeypatch.setattr(
        llm_explainer, "_chat_completion", lambda messages, cfg: ("Too short.", None)
    )
    out = llm_explainer.explain_risk(
        clause_text="x", risk_type="x", risk_level="medium",
        static_explanation="static", cfg=_cfg(),
    )
    assert out["llm_status"] == "fallback_static"
    assert out["llm_explanation"] is None


def test_explain_risk_provider_error(monkeypatch):
    monkeypatch.setattr(
        llm_explainer, "_chat_completion", lambda messages, cfg: (None, "provider_error")
    )
    out = llm_explainer.explain_risk(
        clause_text="x", risk_type="x", risk_level="low",
        static_explanation="static", cfg=_cfg(),
    )
    assert out["llm_status"] == "fallback_static"
    assert out["llm_error_code"] == "provider_error"
    assert out["llm_explanation"] is None


def test_explain_risk_timeout(monkeypatch):
    monkeypatch.setattr(
        llm_explainer, "_chat_completion", lambda messages, cfg: (None, "timeout")
    )
    out = llm_explainer.explain_risk(
        clause_text="x", risk_type="x", risk_level="low",
        static_explanation="static", cfg=_cfg(),
    )
    assert out["llm_status"] == "fallback_static"
    assert out["llm_error_code"] == "timeout"


# ── explain_risks_batch ──────────────────────────────────────────────────────


def _make_risk(idx, level="medium", risk_type="generic"):
    return {
        "index_num": idx,
        "risk_level": level,
        "risk_type": risk_type,
        "evidence_sentence": f"Evidence sentence for risk {idx}.",
        "explanation": "static explanation",
    }


def test_batch_empty_progress_jumps_to_end():
    progress = []

    def cb(percent, msg):
        progress.append((percent, msg))

    out = llm_explainer.explain_risks_batch([], [], progress_callback=cb)
    assert out == []
    assert progress[-1][0] == 90  # default progress_end


def test_batch_all_succeed(app, monkeypatch):
    risks = [_make_risk(1), _make_risk(2)]
    clauses = [
        {"index_num": 1, "content": "Clause one full text used by LLM."},
        {"index_num": 2, "content": "Clause two text used by LLM."},
    ]
    long = (
        "This clause shifts liability and removes employee recourse, leaving "
        "the worker without protection in the event of disputes."
    )
    monkeypatch.setattr(
        llm_explainer, "_chat_completion", lambda messages, cfg: (long, None)
    )

    with app.app_context():
        # Provide the runtime config the batch reads from current_app.config
        app.config["LLM_ENABLED"] = True
        app.config["LLM_API_KEY"] = "test-key"
        app.config["LLM_BASE_URL"] = "https://example.invalid/v1"
        app.config["LLM_TIMEOUT"] = 5
        app.config["LLM_CONTRACT_TIMEOUT"] = 5
        app.config["LLM_MAX_CONCURRENCY"] = 2
        app.config["LLM_MAX_TOKENS"] = 200
        app.config["LLM_TEMPERATURE"] = 0.3
        app.config["LLM_RETRY_COUNT"] = 0
        app.config["LLM_MODEL"] = "qwen3.5-flash"

        out = llm_explainer.explain_risks_batch(risks, clauses)

    assert all(r["llm_status"] == "generated" for r in out)
    assert all(r["llm_explanation"] for r in out)


def test_batch_all_skipped_when_disabled(app, monkeypatch):
    risks = [_make_risk(1)]
    monkeypatch.setattr(
        llm_explainer, "_chat_completion", lambda messages, cfg: ("ignored", None)
    )
    with app.app_context():
        app.config["LLM_ENABLED"] = False
        app.config["LLM_API_KEY"] = "test-key"
        out = llm_explainer.explain_risks_batch(risks, [])
    assert out[0]["llm_status"] == "skipped"


def test_batch_provider_error_leads_to_fallback(app, monkeypatch):
    risks = [_make_risk(1), _make_risk(2)]
    clauses = [{"index_num": 1, "content": "x"}, {"index_num": 2, "content": "y"}]
    monkeypatch.setattr(
        llm_explainer, "_chat_completion", lambda messages, cfg: (None, "provider_error")
    )
    with app.app_context():
        app.config["LLM_ENABLED"] = True
        app.config["LLM_API_KEY"] = "test-key"
        app.config["LLM_BASE_URL"] = "https://example.invalid/v1"
        app.config["LLM_CONTRACT_TIMEOUT"] = 5
        app.config["LLM_MAX_CONCURRENCY"] = 2
        out = llm_explainer.explain_risks_batch(risks, clauses)

    assert all(r["llm_status"] == "fallback_static" for r in out)
    assert all(r["llm_error_code"] == "provider_error" for r in out)


def test_batch_individual_exception_isolated(app, monkeypatch):
    """If a worker raises, that one risk gets fallback_static; others succeed."""
    risks = [_make_risk(1), _make_risk(2)]
    clauses = [{"index_num": 1, "content": "Boom"}, {"index_num": 2, "content": "Ok"}]

    def fake_explain(*args, **kwargs):
        clause_text = kwargs.get("clause_text") or (args[0] if args else "")
        if "Boom" in clause_text:
            raise RuntimeError("simulated worker failure")
        return {
            "llm_explanation": (
                "Long enough explanation that passes the ten word minimum length "
                "check applied by the post processor."
            ),
            "llm_status": "generated",
            "llm_error_code": None,
            "llm_latency_ms": 5,
        }

    monkeypatch.setattr(llm_explainer, "explain_risk", fake_explain)

    with app.app_context():
        app.config["LLM_ENABLED"] = True
        app.config["LLM_API_KEY"] = "test-key"
        app.config["LLM_CONTRACT_TIMEOUT"] = 5
        app.config["LLM_MAX_CONCURRENCY"] = 2
        out = llm_explainer.explain_risks_batch(risks, clauses)

    statuses = sorted(r["llm_status"] for r in out)
    assert "generated" in statuses
    assert "fallback_static" in statuses


# ── postprocessing helpers ───────────────────────────────────────────────────


def test_strip_markdown_removes_formatting():
    cleaned = llm_explainer._strip_markdown("**bold** *italic* # heading > quote ` code `")
    assert "**" not in cleaned
    assert "#" not in cleaned
    assert "`" not in cleaned


def test_truncate_words_breaks_at_sentence_boundary():
    text = " ".join([f"word{i}" for i in range(150)]) + ". After end."
    truncated = llm_explainer._truncate_words(text, max_words=20)
    assert len(truncated.split()) <= 21


@pytest.mark.parametrize(
    "raw,expected_substr",
    [
        ("**Hello** world this is a long enough explanation.", "Hello world this is"),
        ("# Heading", "Heading"),
    ],
)
def test_postprocess_combined(raw, expected_substr):
    out = llm_explainer._postprocess_output(raw)
    assert expected_substr in out
