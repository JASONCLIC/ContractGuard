"""
P0/P1 system tests for /api/export.

Covers:
- POST /api/export/<id>/pdf            create export job (auth, ownership, ready-state)
- GET  /api/export/<id>/pdf/<job_id>   download PDF (auth, ownership, missing cache)
- GET  /api/export/<id>/desensitized   on-demand desensitization (auth, ownership)
"""

from __future__ import annotations

from io import BytesIO


def _login_other(app, email="other.export@test.local"):
    other = app.test_client()
    other.post(
        "/api/auth/register",
        json={"name": "Other", "email": email, "password": "Strong#1234"},
    )
    other.post("/api/auth/login", json={"email": email, "password": "Strong#1234"})
    return other


# ── POST /pdf ─────────────────────────────────────────────────────────────────


def test_create_pdf_requires_login(app):
    res = app.test_client().post("/api/export/1/pdf")
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_create_pdf_unknown_contract_returns_404(authed_client):
    res = authed_client.post("/api/export/999999/pdf")
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001


def test_create_pdf_other_user_returns_403(authed_client, app, done_contract):
    other = _login_other(app)
    res = other.post(f"/api/export/{done_contract}/pdf")
    assert res.status_code == 403
    assert res.get_json()["code"] == 2002


def test_create_pdf_when_not_done_returns_409(authed_client, app, pdf_factory):
    res = authed_client.post(
        "/api/contract/upload",
        data={
            "file": (BytesIO(pdf_factory()), "labor.pdf", "application/pdf"),
            "contract_type": "labor",
        },
        content_type="multipart/form-data",
    )
    cid = res.get_json()["data"]["contract_id"]

    res = authed_client.post(f"/api/export/{cid}/pdf")
    assert res.status_code == 409
    assert res.get_json()["code"] == 2003


def test_create_pdf_succeeds_for_done_contract(authed_client, done_contract):
    """P0-EXP-01 part 1: returns job_id, status=success."""
    res = authed_client.post(f"/api/export/{done_contract}/pdf")
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    assert body["code"] == 0
    assert body["data"]["status"] == "success"
    assert body["data"]["job_id"] > 0


# ── GET /pdf/<job_id> ─────────────────────────────────────────────────────────


def test_download_pdf_requires_login(app):
    res = app.test_client().get("/api/export/1/pdf/1")
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_download_pdf_after_create(authed_client, done_contract):
    """P0-EXP-01 part 2: subsequent GET streams PDF bytes with proper headers."""
    create = authed_client.post(f"/api/export/{done_contract}/pdf").get_json()["data"]
    jid = create["job_id"]

    res = authed_client.get(f"/api/export/{done_contract}/pdf/{jid}")
    assert res.status_code == 200
    assert res.mimetype == "application/pdf"
    cd = res.headers.get("Content-Disposition", "")
    assert "attachment" in cd.lower()
    assert f"ContractGuard_Report_{done_contract}.pdf" in cd
    body = res.get_data()
    # Real PDF bytes start with %PDF-
    assert body[:5] == b"%PDF-"
    assert len(body) > 200


def test_download_pdf_missing_job_in_cache_returns_404(authed_client, done_contract):
    """P2-EXP-03: invalid job_id (not in _export_cache) → 404/3001."""
    res = authed_client.get(f"/api/export/{done_contract}/pdf/999999")
    assert res.status_code == 404
    assert res.get_json()["code"] == 3001


def test_download_pdf_other_user_returns_403(authed_client, app, done_contract):
    create = authed_client.post(f"/api/export/{done_contract}/pdf").get_json()["data"]
    jid = create["job_id"]

    other = _login_other(app)
    res = other.get(f"/api/export/{done_contract}/pdf/{jid}")
    assert res.status_code == 403
    assert res.get_json()["code"] == 2002


def test_download_pdf_unknown_contract_returns_404(authed_client):
    res = authed_client.get("/api/export/999999/pdf/1")
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001


# ── GET /desensitized ─────────────────────────────────────────────────────────


def test_desensitized_requires_login(app):
    res = app.test_client().get("/api/export/1/desensitized")
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_desensitized_returns_existing_text(authed_client, done_contract):
    """done_contract fixture pre-populates desensitized_text + summary."""
    res = authed_client.get(f"/api/export/{done_contract}/desensitized")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "[EMPLOYER]" in data["desensitized_text"]
    assert data["total_redactions"] == 3
    assert any(item["type"] == "EMAIL" for item in data["redaction_summary"])


def test_desensitized_lazy_compute_when_missing(authed_client, app, pdf_factory):
    """If desensitized_text is empty, the route must compute and persist it."""
    res = authed_client.post(
        "/api/contract/upload",
        data={
            "file": (BytesIO(pdf_factory()), "labor.pdf", "application/pdf"),
            "contract_type": "labor",
        },
        content_type="multipart/form-data",
    )
    cid = res.get_json()["data"]["contract_id"]

    with app.app_context():
        from backend.app.extensions import db
        from backend.app.models.contract import Contract

        c = Contract.query.get(cid)
        c.status = "done"
        c.raw_text = "Contact us at admin@example.com or +44 7700 900123 for support."
        c.desensitized_text = None
        c.redaction_summary = None
        c.total_redactions = 0
        db.session.commit()

    res = authed_client.get(f"/api/export/{cid}/desensitized")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "[EMAIL]" in data["desensitized_text"]
    assert data["total_redactions"] >= 1


def test_desensitized_other_user_returns_403(authed_client, app, done_contract):
    other = _login_other(app)
    res = other.get(f"/api/export/{done_contract}/desensitized")
    assert res.status_code == 403
    assert res.get_json()["code"] == 2002


def test_desensitized_unknown_contract_returns_404(authed_client):
    res = authed_client.get("/api/export/999999/desensitized")
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001
