"""
Unit tests for backend/app/nlp/pipeline._segment_clauses.

Validates the three-tier clause splitting strategy:
  1. Per-line heading regex (well-formatted documents).
  2. Inline scan over flowing text (PDFs that lost line breaks).
  3. Punctuation fallback (last resort).

These are pure regex tests — no BERT model is loaded.
"""

from __future__ import annotations

from backend.app.nlp.pipeline import _segment_clauses


def test_segments_chinese_headings():
    text = (
        "第一条 合同期限\n本合同期限为24个月。\n"
        "第二条 工资待遇\n月薪5000元，每月10日支付。\n"
        "第三条 工作地点\n伦敦办公室。"
    )
    clauses = _segment_clauses(text)
    assert len(clauses) >= 3
    headings = [c["heading"] for c in clauses]
    assert any("第一条" in h for h in headings)
    assert any("第二条" in h for h in headings)
    assert any("第三条" in h for h in headings)
    # index_num is 1-based monotonic
    assert [c["index_num"] for c in clauses] == list(range(1, len(clauses) + 1))


def test_segments_english_article_headings():
    text = (
        "Article 1 Term\nThis Agreement begins on 2024-01-01 and lasts 24 months.\n"
        "Article 2 Salary\n5000 USD per month.\n"
        "Article 3 Termination\nEither party may terminate with 30 days notice."
    )
    clauses = _segment_clauses(text)
    assert len(clauses) >= 3
    assert any("Article 1" in c["heading"] for c in clauses)
    assert any("Article 2" in c["heading"] for c in clauses)


def test_segments_numbered_headings():
    text = (
        "1. Term\nContract is for 24 months.\n"
        "2. Salary\n5000 USD per month.\n"
        "3. Termination\n30 days notice required."
    )
    clauses = _segment_clauses(text)
    assert len(clauses) >= 3


def test_inline_fallback_when_line_breaks_missing():
    """Tier 2: text without newlines must still split via inline scan."""
    text = (
        "Article 1 Term This Agreement is for 24 months. "
        "Article 2 Salary The monthly salary shall be 5000 USD. "
        "Article 3 Termination Either party may terminate with 30 days notice."
    )
    clauses = _segment_clauses(text)
    assert len(clauses) >= 3
    headings = " ".join(c["heading"] for c in clauses)
    assert "Article 1" in headings
    assert "Article 2" in headings
    assert "Article 3" in headings


def test_punctuation_fallback_when_no_headings():
    """Tier 3: fully unstructured text should still produce >=2 chunks."""
    text = (
        "This is the first sentence with enough length to be a clause.  "
        "This is the second sentence which should land as a separate clause.  "
        "And yet another sentence which forms a third chunk with sufficient length."
    )
    clauses = _segment_clauses(text)
    # Either tier 2 (no inline match) or tier 3 (punctuation split) returns
    # multiple chunks; we only assert that we got at least 2.
    assert len(clauses) >= 2
    for c in clauses:
        assert "index_num" in c
        assert c["heading"]
        assert c["content"]


def test_empty_text_returns_empty_list():
    assert _segment_clauses("") == []
    assert _segment_clauses("   \n\n   ") == []


def test_index_num_is_strictly_monotonic():
    text = "\n".join(f"第{i}条 标题{i}\n正文内容{i}" for i in range(1, 6))
    clauses = _segment_clauses(text)
    indices = [c["index_num"] for c in clauses]
    assert indices == sorted(indices)
    assert len(set(indices)) == len(indices)
