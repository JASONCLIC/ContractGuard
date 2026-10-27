"""
Tests for backend/app/routes/contract._run_analysis_and_store.

Mocks parse_contract_text so the heavy NLP pipeline is not invoked, but the
job + contract row state machine is exercised end-to-end (running → success
on the happy path; running → failed on exception).
"""

from __future__ import annotations

from datetime import datetime

import pytest


@pytest.fixture
def uploaded_contract(authed_client, app, pdf_factory):
    """Use the upload endpoint to create a contract+job pair, then return ids."""
    from io import BytesIO

    res = authed_client.post(
        "/api/contract/upload",
        data={
            "file": (BytesIO(pdf_factory()), "labor.pdf", "application/pdf"),
            "contract_type": "labor",
        },
        content_type="multipart/form-data",
    )
    body = res.get_json()["data"]
    return {"contract_id": body["contract_id"], "job_id": body["job_id"]}


def test_run_analysis_happy_path(monkeypatch, app, uploaded_contract):
    """Successful pipeline → contract.status='done', job.status='success'."""

    def fake_pipeline(text, contract_type, progress_callback=None):
        if progress_callback:
            progress_callback(50, "halfway")
        return {
            "clauses": [
                {"index_num": 1, "heading": "H1", "content": "c1", "category": "general"},
                {"index_num": 2, "heading": "H2", "content": "c2", "category": "salary"},
            ],
            "key_info": {"party_a": "A", "party_b": "B"},
            "risks": [
                {
                    "index_num": 2,
                    "risk_level": "high",
                    "risk_type": "wage_payment_unclear",
                    "evidence_sentence": "evi",
                    "explanation": "exp",
                    "legal_reference": "ref",
                    "llm_status": "skipped",
                }
            ],
            "missing_items": [
                {
                    "item_name": "Dispute Resolution",
                    "description": "d",
                    "potential_risk": "r",
                }
            ],
            "desensitized_text": "[EMPLOYER] hires [EMPLOYEE].",
            "redaction_summary": [{"type": "EMAIL", "count": 1}],
            "total_redactions": 1,
        }

    from backend.app.routes import contract as contract_route

    monkeypatch.setattr(contract_route, "parse_contract_text", fake_pipeline)

    with app.app_context():
        from backend.app.extensions import db
        from backend.app.models.analysis_job import AnalysisJob
        from backend.app.models.clause import Clause
        from backend.app.models.contract import Contract
        from backend.app.models.missing import MissingItem
        from backend.app.models.risk import RiskItem

        contract = Contract.query.get(uploaded_contract["contract_id"])
        job = AnalysisJob.query.get(uploaded_contract["job_id"])

        contract_route._run_analysis_and_store(contract, job)

        db.session.refresh(contract)
        db.session.refresh(job)

        assert contract.status == "done"
        assert job.status == "success"
        assert job.progress_percent == 100
        assert job.finished_at is not None
        assert contract.key_info == {"party_a": "A", "party_b": "B"}
        assert contract.total_redactions == 1
        assert contract.desensitized_text.startswith("[EMPLOYER]")

        assert Clause.query.filter_by(contract_id=contract.id).count() == 2
        assert RiskItem.query.filter_by(contract_id=contract.id).count() == 1
        assert MissingItem.query.filter_by(contract_id=contract.id).count() == 1


def test_run_analysis_failure_marks_job_failed(monkeypatch, app, uploaded_contract):
    """Exception inside the pipeline → contract.status='error', job.status='failed'."""

    def boom(text, contract_type, progress_callback=None):
        raise RuntimeError("simulated NLP failure")

    from backend.app.routes import contract as contract_route

    monkeypatch.setattr(contract_route, "parse_contract_text", boom)

    with app.app_context():
        from backend.app.extensions import db
        from backend.app.models.analysis_job import AnalysisJob
        from backend.app.models.contract import Contract

        contract = Contract.query.get(uploaded_contract["contract_id"])
        job = AnalysisJob.query.get(uploaded_contract["job_id"])

        with pytest.raises(RuntimeError):
            contract_route._run_analysis_and_store(contract, job)

        db.session.refresh(contract)
        db.session.refresh(job)

        assert contract.status == "error"
        assert job.status == "failed"
        assert job.error_message and "simulated NLP failure" in job.error_message
        assert isinstance(job.finished_at, datetime)


def test_run_analysis_in_background_swallows_errors(monkeypatch, app, uploaded_contract):
    """The background wrapper must swallow exceptions (caller is a daemon thread)."""

    def boom(text, contract_type, progress_callback=None):
        raise RuntimeError("background failure")

    from backend.app.routes import contract as contract_route

    monkeypatch.setattr(contract_route, "parse_contract_text", boom)

    # Should not raise; status mutation still happens via _run_analysis_and_store.
    contract_route._run_analysis_in_background(
        app, uploaded_contract["contract_id"], uploaded_contract["job_id"]
    )

    with app.app_context():
        from backend.app.models.analysis_job import AnalysisJob
        from backend.app.models.contract import Contract

        contract = Contract.query.get(uploaded_contract["contract_id"])
        job = AnalysisJob.query.get(uploaded_contract["job_id"])
        assert contract.status == "error"
        assert job.status == "failed"
