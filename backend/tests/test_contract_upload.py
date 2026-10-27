"""
P0/P1 system tests for contract upload + paste endpoints.

Covers:
- Upload happy path: contract_id + job_id, AnalysisJob row created (P0-UPL-01)
- Duplicate upload of `done` contract → duplicated=True (P1-UPL-02)
- Re-upload after error → previous row deleted, fresh job (P1-UPL-03)
- Negative branches in validate_upload (P0-UPL-04):
  * no file
  * wrong extension
  * wrong mimetype
  * fake PDF header
  * oversized > 10MB
- Login requirement on both upload and paste
- Paste positive + empty + too-long (P1-UPL-05)
- get/delete contract + ownership check
"""

from __future__ import annotations

import io


def _post_pdf(client, filename, data, *, mimetype="application/pdf", contract_type="labor"):
    return client.post(
        "/api/contract/upload",
        data={
            "file": (io.BytesIO(data), filename, mimetype),
            "contract_type": contract_type,
        },
        content_type="multipart/form-data",
    )


# ── /api/contract/upload ──────────────────────────────────────────────────────


def test_upload_requires_login(client, pdf_factory):
    res = _post_pdf(client, "labor.pdf", pdf_factory())
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_upload_valid_pdf_starts_job(authed_client, app, pdf_factory):
    """P0-UPL-01: legal PDF → contract_id + job_id; AnalysisJob row persisted."""
    res = _post_pdf(authed_client, "labor.pdf", pdf_factory())
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    assert body["code"] == 0

    data = body["data"]
    assert data["contract_id"] > 0
    assert data["job_id"] > 0

    with app.app_context():
        from backend.app.models.analysis_job import AnalysisJob
        from backend.app.models.contract import Contract

        contract = Contract.query.get(data["contract_id"])
        job = AnalysisJob.query.get(data["job_id"])
        assert contract is not None
        assert contract.title == "labor.pdf"
        assert contract.contract_type == "labor"
        assert contract.status == "uploaded"
        assert contract.file_hash and len(contract.file_hash) == 64
        assert contract.file_size > 0
        assert job is not None
        assert job.contract_id == contract.id
        assert job.job_type == "full_analysis"
        # Background analysis is monkeypatched away → job stays in initial "running" state.
        assert job.status == "running"
        assert job.progress_percent == 3


def test_upload_duplicate_done_returns_duplicated_flag(authed_client, app, pdf_factory):
    """P1-UPL-02: re-upload of identical content already analysed → duplicated=True."""
    pdf_bytes = pdf_factory()
    first = _post_pdf(authed_client, "labor.pdf", pdf_bytes).get_json()["data"]

    with app.app_context():
        from backend.app.extensions import db
        from backend.app.models.contract import Contract

        contract = Contract.query.get(first["contract_id"])
        contract.status = "done"
        db.session.commit()

    res = _post_pdf(authed_client, "labor.pdf", pdf_bytes)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["duplicated"] is True
    assert data["job_id"] is None
    assert data["contract_id"] == first["contract_id"]


def test_upload_after_previous_error_recreates(authed_client, app, pdf_factory):
    """P1-UPL-03: previous analysis errored → existing row removed and fresh job created."""
    pdf_bytes = pdf_factory()
    first = _post_pdf(authed_client, "labor.pdf", pdf_bytes).get_json()["data"]

    with app.app_context():
        from backend.app.extensions import db
        from backend.app.models.contract import Contract

        Contract.query.get(first["contract_id"]).status = "error"
        db.session.commit()

    res = _post_pdf(authed_client, "labor.pdf", pdf_bytes)
    assert res.status_code == 200
    data = res.get_json()["data"]
    # SQLite without AUTOINCREMENT can re-use the deleted row's id, so we
    # verify the recreate behaviour by row state instead of id comparison.
    assert data["job_id"] is not None
    with app.app_context():
        from backend.app.models.contract import Contract

        contracts = Contract.query.all()
        assert len(contracts) == 1
        assert contracts[0].status == "uploaded"
        assert contracts[0].id == data["contract_id"]


def test_upload_no_file_returns_1002(authed_client):
    res = authed_client.post(
        "/api/contract/upload",
        data={"contract_type": "labor"},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert res.get_json()["code"] == 1002


def test_upload_wrong_extension_returns_1002(authed_client, pdf_factory):
    res = _post_pdf(authed_client, "labor.docx", pdf_factory(), mimetype="application/pdf")
    assert res.status_code == 400
    assert res.get_json()["code"] == 1002
    assert "extension" in res.get_json()["message"].lower()


def test_upload_wrong_mimetype_returns_1002(authed_client, pdf_factory):
    res = _post_pdf(authed_client, "labor.pdf", pdf_factory(), mimetype="text/plain")
    assert res.status_code == 400
    assert res.get_json()["code"] == 1002


def test_upload_fake_pdf_header_returns_1002(authed_client, fake_pdf_bytes):
    res = _post_pdf(authed_client, "labor.pdf", fake_pdf_bytes, mimetype="application/pdf")
    assert res.status_code == 400
    body = res.get_json()
    assert body["code"] == 1002
    assert "header" in body["message"].lower()


def test_upload_oversized_returns_1002(authed_client, oversized_pdf_bytes):
    res = _post_pdf(authed_client, "huge.pdf", oversized_pdf_bytes, mimetype="application/pdf")
    assert res.status_code == 400
    body = res.get_json()
    assert body["code"] == 1002
    assert "too large" in body["message"].lower()


# ── /api/contract/paste ───────────────────────────────────────────────────────


def test_paste_requires_login(client):
    res = client.post("/api/contract/paste", json={"text": "Article 1 Term."})
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_paste_valid_text_starts_job(authed_client, app):
    res = authed_client.post(
        "/api/contract/paste",
        json={
            "text": "Article 1 Term: 24 months. Article 2 Salary: 5000 USD per month.",
            "title": "draft labor",
            "contract_type": "labor",
        },
    )
    assert res.status_code == 200, res.get_json()
    data = res.get_json()["data"]
    assert data["contract_id"] > 0
    assert data["job_id"] > 0

    with app.app_context():
        from backend.app.models.analysis_job import AnalysisJob
        from backend.app.models.contract import Contract

        contract = Contract.query.get(data["contract_id"])
        assert contract.title == "draft labor"
        assert contract.contract_type == "labor"
        job = AnalysisJob.query.get(data["job_id"])
        assert job.contract_id == contract.id


def test_paste_empty_text_returns_1001(authed_client):
    res = authed_client.post("/api/contract/paste", json={"text": "   "})
    assert res.status_code == 400
    assert res.get_json()["code"] == 1001


def test_paste_too_long_returns_1001(authed_client):
    res = authed_client.post("/api/contract/paste", json={"text": "x" * 50001})
    assert res.status_code == 400
    assert res.get_json()["code"] == 1001


def test_paste_duplicate_done_returns_duplicated_flag(authed_client, app):
    payload = {"text": "Article 1 Term: 12 months.", "title": "t1"}
    first = authed_client.post("/api/contract/paste", json=payload).get_json()["data"]

    with app.app_context():
        from backend.app.extensions import db
        from backend.app.models.contract import Contract

        Contract.query.get(first["contract_id"]).status = "done"
        db.session.commit()

    res = authed_client.post("/api/contract/paste", json=payload)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["duplicated"] is True
    assert data["job_id"] is None
    assert data["contract_id"] == first["contract_id"]


# ── /api/contract/<id> get + delete ───────────────────────────────────────────


def test_get_contract_returns_metadata(authed_client, pdf_factory):
    upload = _post_pdf(authed_client, "labor.pdf", pdf_factory()).get_json()["data"]
    cid = upload["contract_id"]

    res = authed_client.get(f"/api/contract/{cid}")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["id"] == cid
    assert data["status"] == "uploaded"
    assert data["contract_type"] == "labor"
    assert data["title"] == "labor.pdf"


def test_get_other_users_contract_returns_403(authed_client, app, pdf_factory):
    upload = _post_pdf(authed_client, "labor.pdf", pdf_factory()).get_json()["data"]
    cid = upload["contract_id"]

    other = app.test_client()
    other.post(
        "/api/auth/register",
        json={"name": "Eve", "email": "eve@test.local", "password": "Strong#1234"},
    )
    other.post(
        "/api/auth/login",
        json={"email": "eve@test.local", "password": "Strong#1234"},
    )

    res = other.get(f"/api/contract/{cid}")
    assert res.status_code == 403
    assert res.get_json()["code"] == 2002


def test_get_missing_contract_returns_404(authed_client):
    res = authed_client.get("/api/contract/999999")
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001


def test_delete_contract_succeeds(authed_client, pdf_factory):
    upload = _post_pdf(authed_client, "labor.pdf", pdf_factory()).get_json()["data"]
    cid = upload["contract_id"]

    res = authed_client.delete(f"/api/contract/{cid}")
    assert res.status_code == 200
    assert res.get_json()["data"]["deleted"] is True

    res = authed_client.get(f"/api/contract/{cid}")
    assert res.status_code == 404


def test_delete_other_users_contract_returns_403(authed_client, app, pdf_factory):
    upload = _post_pdf(authed_client, "labor.pdf", pdf_factory()).get_json()["data"]
    cid = upload["contract_id"]

    other = app.test_client()
    other.post(
        "/api/auth/register",
        json={"name": "Mallory", "email": "mallory@test.local", "password": "Strong#1234"},
    )
    other.post(
        "/api/auth/login",
        json={"email": "mallory@test.local", "password": "Strong#1234"},
    )

    res = other.delete(f"/api/contract/{cid}")
    assert res.status_code == 403
    assert res.get_json()["code"] == 2002
