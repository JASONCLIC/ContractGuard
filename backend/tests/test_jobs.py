"""
P0/P1 system tests for /api/jobs.

Covers:
- POST  /api/jobs               create job (auth, ownership, type branch)
- GET   /api/jobs/<job_id>      poll status (auth, ownership, missing)
"""

from __future__ import annotations


def test_get_job_requires_login(client):
    res = client.get("/api/jobs/1")
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_get_job_not_found_returns_3001(authed_client):
    res = authed_client.get("/api/jobs/999999")
    assert res.status_code == 404
    assert res.get_json()["code"] == 3001


def test_get_own_job_returns_status(authed_client, app, done_contract):
    """The done_contract fixture ran an upload so an AnalysisJob exists for it."""
    with app.app_context():
        from backend.app.models.analysis_job import AnalysisJob

        job = AnalysisJob.query.filter_by(contract_id=done_contract).first()
        assert job is not None
        jid = job.id

    res = authed_client.get(f"/api/jobs/{jid}")
    assert res.status_code == 200
    body = res.get_json()
    assert body["code"] == 0
    assert body["data"]["job_id"] == jid
    assert body["data"]["contract_id"] == done_contract
    assert "status" in body["data"]
    assert "progress_percent" in body["data"]


def test_get_other_users_job_returns_403(authed_client, app, done_contract):
    with app.app_context():
        from backend.app.models.analysis_job import AnalysisJob

        jid = AnalysisJob.query.filter_by(contract_id=done_contract).first().id

    other = app.test_client()
    other.post(
        "/api/auth/register",
        json={"name": "Eve", "email": "eve.jobs@test.local", "password": "Strong#1234"},
    )
    other.post(
        "/api/auth/login",
        json={"email": "eve.jobs@test.local", "password": "Strong#1234"},
    )

    res = other.get(f"/api/jobs/{jid}")
    assert res.status_code == 403
    assert res.get_json()["code"] == 2002


def test_create_job_requires_login(client):
    res = client.post("/api/jobs", json={"contract_id": 1})
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_create_job_unknown_contract_returns_404(authed_client):
    res = authed_client.post("/api/jobs", json={"contract_id": 999999})
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001


def test_create_job_other_users_contract_returns_403(authed_client, app, done_contract):
    other = app.test_client()
    other.post(
        "/api/auth/register",
        json={"name": "Mallory", "email": "mallory.jobs@test.local", "password": "Strong#1234"},
    )
    other.post(
        "/api/auth/login",
        json={"email": "mallory.jobs@test.local", "password": "Strong#1234"},
    )

    res = other.post("/api/jobs", json={"contract_id": done_contract})
    assert res.status_code == 403
    assert res.get_json()["code"] == 2002


def test_create_job_full_analysis_succeeds_without_running_pipeline(
    authed_client, app, done_contract
):
    """
    Conftest stubs `_run_analysis_and_store` to a no-op, so this exercises the
    full_analysis branch without invoking the BERT pipeline.
    """
    res = authed_client.post(
        "/api/jobs",
        json={"contract_id": done_contract, "job_type": "full_analysis"},
    )
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    assert body["code"] == 0
    assert body["data"]["status"] == "running"
    assert body["data"]["job_id"] > 0


def test_create_job_non_full_analysis_skips_pipeline(authed_client, done_contract):
    res = authed_client.post(
        "/api/jobs",
        json={"contract_id": done_contract, "job_type": "preview"},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["status"] == "running"
