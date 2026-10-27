"""
P1 system tests for /api/template (public).

Templates auto-seed from backend/data/template_library.json on first request.
"""

from __future__ import annotations


def test_categories_returns_seeded_categories(client):
    res = client.get("/api/template/categories")
    assert res.status_code == 200
    body = res.get_json()
    assert body["code"] == 0
    items = body["data"]
    assert isinstance(items, list)
    assert len(items) > 0
    keys = {it["key"] for it in items}
    # Seeded categories sourced from backend/data/template_library.json
    assert "salary" in keys


def test_items_by_category_returns_clauses(client):
    res = client.get("/api/template/salary")
    assert res.status_code == 200
    items = res.get_json()["data"]
    assert isinstance(items, list)
    assert len(items) >= 1
    sample = items[0]
    assert {"id", "title", "content", "tip"} <= set(sample.keys())
    assert sample["title"]
    assert sample["content"]


def test_items_by_unknown_category_returns_empty(client):
    res = client.get("/api/template/no-such-category")
    assert res.status_code == 200
    assert res.get_json()["data"] == []
