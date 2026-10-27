"""
P0/P1 system tests for /api/analysis/<contract_id>/{structure,summary,risks,missing}.
"""

from __future__ import annotations


def _login_other(app, email="other.analysis@test.local"):
    other = app.test_client()
    other.post(
        "/api/auth/register",
        json={"name": "Other", "email": email, "password": "Strong#1234"},
    )
    other.post("/api/auth/login", json={"email": email, "password": "Strong#1234"})
    return other


# ── Auth & ownership gate (applies to all four endpoints) ─────────────────────


def test_analysis_endpoints_require_login(app):
    fresh = app.test_client()
    for path in ("structure", "summary", "risks", "missing"):
        res = fresh.get(f"/api/analysis/1/{path}")
        assert res.status_code == 401, path
        assert res.get_json()["code"] == 2002


def test_analysis_endpoints_404_when_contract_missing(authed_client):
    for path in ("structure", "summary", "risks", "missing"):
        res = authed_client.get(f"/api/analysis/999999/{path}")
        assert res.status_code == 404, path
        assert res.get_json()["code"] == 2001


def test_analysis_endpoints_403_for_other_user(authed_client, app, done_contract):
    other = _login_other(app)
    for path in ("structure", "summary", "risks", "missing"):
        res = other.get(f"/api/analysis/{done_contract}/{path}")
        assert res.status_code == 403, path
        assert res.get_json()["code"] == 2002


def test_analysis_endpoints_409_when_not_done(authed_client, app, pdf_factory):
    """P0-ANA-03: contract not yet finished → 409/2003."""
    from io import BytesIO

    res = authed_client.post(
        "/api/contract/upload",
        data={
            "file": (BytesIO(pdf_factory()), "labor.pdf", "application/pdf"),
            "contract_type": "labor",
        },
        content_type="multipart/form-data",
    )
    cid = res.get_json()["data"]["contract_id"]  # status stays "uploaded"

    for path in ("structure", "summary", "risks", "missing"):
        res = authed_client.get(f"/api/analysis/{cid}/{path}")
        assert res.status_code == 409, path
        assert res.get_json()["code"] == 2003


# ── Happy path payloads ───────────────────────────────────────────────────────


def test_structure_returns_clauses_in_order(authed_client, done_contract):
    res = authed_client.get(f"/api/analysis/{done_contract}/structure")
    assert res.status_code == 200
    items = res.get_json()["data"]
    assert [c["index_num"] for c in items] == [1, 2, 3]
    headings = [c["heading"] for c in items]
    assert "Article 1 Term" in headings
    assert all({"id", "heading", "content", "category"} <= set(c.keys()) for c in items)


def test_summary_returns_key_info(authed_client, done_contract):
    res = authed_client.get(f"/api/analysis/{done_contract}/summary")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["party_a"] == "Acme Corporation"
    assert data["party_b"] == "John Doe"
    assert data["work_location"] == "London Office"


def test_risks_returns_all_levels(authed_client, done_contract):
    res = authed_client.get(f"/api/analysis/{done_contract}/risks")
    assert res.status_code == 200
    items = res.get_json()["data"]
    assert len(items) == 2
    levels = {r["risk_level"] for r in items}
    assert levels == {"medium", "high"}
    # index_num is joined from the clause table by the route
    assert all("index_num" in r for r in items)


def test_risks_filtering_by_level(authed_client, done_contract):
    res = authed_client.get(f"/api/analysis/{done_contract}/risks?level=high")
    assert res.status_code == 200
    items = res.get_json()["data"]
    assert len(items) == 1
    assert items[0]["risk_level"] == "high"
    assert items[0]["risk_type"] == "vague_termination"

    res = authed_client.get(f"/api/analysis/{done_contract}/risks?level=low")
    assert res.status_code == 200
    assert res.get_json()["data"] == []


def test_missing_returns_seeded_items(authed_client, done_contract):
    res = authed_client.get(f"/api/analysis/{done_contract}/missing")
    assert res.status_code == 200
    items = res.get_json()["data"]
    assert len(items) == 1
    assert items[0]["item_name"] == "Dispute Resolution"
    assert "potential_risk" in items[0]
