"""
Shared pytest fixtures for ContractGuard backend system tests.

Design notes:
- Backend uses session cookies for auth, so we drive everything through
  Flask's test_client and let it persist the session between requests.
- Database is SQLite in-memory pinned to a single connection (StaticPool)
  so threads/contexts share state. Schema is rebuilt per test for isolation.
- The heavy NLP pipeline (BERT + Qwen LLM) is never executed in unit tests:
  the background analysis launcher is monkeypatched into a no-op, so the
  upload route only validates input and persists the Contract / AnalysisJob
  rows that the test then asserts against.
"""

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy.pool import StaticPool

# Repo root has a trailing space in its name on this machine; resolve robustly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app  # noqa: E402
from backend.app.config import Config  # noqa: E402
from backend.app.extensions import db  # noqa: E402


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    SECRET_KEY = "test-secret-key"
    LLM_ENABLED = False
    LLM_API_KEY = ""
    ADMIN_NAME = "Test Admin"
    ADMIN_EMAIL = "admin@test.local"
    ADMIN_PASSWORD = "Admin@123456"
    SESSION_COOKIE_SECURE = False
    PROPAGATE_EXCEPTIONS = True


# ── Application & database fixtures ───────────────────────────────────────────


@pytest.fixture(scope="session")
def app():
    application = create_app(TestConfig)
    yield application


@pytest.fixture(autouse=True)
def _reset_database(app):
    """Drop and recreate all tables before each test, then re-seed admin + templates."""
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

        from backend.app.services.admin_service import ensure_admin_user
        from backend.app.services.template_library_service import (
            ensure_template_library_seeded,
        )

        ensure_admin_user()
        try:
            ensure_template_library_seeded()
        except Exception:
            # Template seeding is non-critical for auth/upload tests.
            db.session.rollback()
    yield
    with app.app_context():
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


# ── Pipeline isolation ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _no_background_analysis(monkeypatch):
    """
    Replace the background-analysis launcher with a no-op so upload tests do
    not start the BERT+LLM pipeline. Tests assert on Contract/AnalysisJob row
    creation, not on analysis completion.
    """
    from backend.app.routes import contract as contract_route
    from backend.app.routes import jobs as jobs_route

    monkeypatch.setattr(
        contract_route,
        "_start_background_analysis",
        lambda contract_id, job_id: None,
    )
    # /api/jobs (POST) calls _run_analysis_and_store synchronously when
    # job_type=full_analysis. Stub it too so jobs tests do not trigger NLP.
    monkeypatch.setattr(
        jobs_route,
        "_run_analysis_and_store",
        lambda contract, job: None,
    )


@pytest.fixture(autouse=True)
def _reset_inmemory_state():
    """Reset module-level in-memory caches between tests."""
    from backend.app.middleware import rate_limiter
    from backend.app.routes import export as export_route

    rate_limiter._bucket.clear()
    export_route._export_cache.clear()
    yield
    rate_limiter._bucket.clear()
    export_route._export_cache.clear()


# ── PDF helpers ───────────────────────────────────────────────────────────────


def _build_minimal_pdf(text: str) -> bytes:
    """Generate a small but real PDF whose extracted text contains `text`."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    text_obj = c.beginText(72, 720)
    for line in text.split("\n"):
        text_obj.textLine(line if line else " ")
    c.drawText(text_obj)
    c.showPage()
    c.save()
    return buffer.getvalue()


@pytest.fixture
def pdf_factory():
    """Return a callable that generates a small valid PDF with optional custom text."""

    def _make(text: str = (
        "Article 1 Term: This Agreement begins on 2024-01-01 and lasts 24 months. "
        "Article 2 Salary: 5000 USD per month. "
        "Article 3 Termination: Either party may terminate with 30 days notice."
    )) -> bytes:
        return _build_minimal_pdf(text)

    return _make


@pytest.fixture
def oversized_pdf_bytes(pdf_factory):
    """A real PDF padded above the 10 MB upload cap; size is the failing check."""
    base = pdf_factory()
    padding = b"\n%" + (b"x" * (11 * 1024 * 1024))
    return base + padding


@pytest.fixture
def fake_pdf_bytes():
    """Bytes whose magic header is NOT `%PDF-`."""
    return b"This is plain text, not a PDF.\nContractGuard test fixture.\n"


# ── Auth helpers ──────────────────────────────────────────────────────────────


def _register(client, *, name="Alice Tester", email="alice@test.local", password="Strong#1234"):
    return client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )


def _login(client, email, password):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


@pytest.fixture
def registered_user(client):
    """Idempotent: registers alice if she isn't already in the DB.

    `done_contract` registers alice via its own helper client, so when both
    fixtures are requested by the same test the second registration would
    return 400 (`email already registered`). We tolerate that case here.
    """
    email = "alice@test.local"
    password = "Strong#1234"
    res = _register(client, email=email, password=password)
    assert res.status_code in (200, 400), res.get_json()
    return {"email": email, "password": password}


@pytest.fixture
def authed_client(client, registered_user):
    res = _login(client, registered_user["email"], registered_user["password"])
    assert res.status_code == 200, res.get_json()
    return client


@pytest.fixture
def admin_authed_client(app):
    """A dedicated test_client logged in as the seeded admin.

    Uses its own test_client so the main `client` / `authed_client` session
    is not overwritten when both fixtures are requested by the same test.
    """
    c = app.test_client()
    res = _login(c, app.config["ADMIN_EMAIL"], app.config["ADMIN_PASSWORD"])
    assert res.status_code == 200, res.get_json()
    return c


# ── Seeded analysis data ──────────────────────────────────────────────────────


@pytest.fixture
def done_contract(app, pdf_factory):
    """
    Upload a real PDF as alice (using a dedicated helper test_client so the
    main `client` session is not polluted), then directly promote the contract
    to status='done' and seed its Clauses / Risks / Missing items. Returns the
    contract id for use by analysis/export/share tests.

    Tests that need to query as the contract owner can request `authed_client`
    in addition; both end up acting on the same alice@test.local user.
    """
    from io import BytesIO

    helper = app.test_client()
    helper.post(
        "/api/auth/register",
        json={"name": "Alice Tester", "email": "alice@test.local", "password": "Strong#1234"},
    )
    helper.post(
        "/api/auth/login",
        json={"email": "alice@test.local", "password": "Strong#1234"},
    )

    pdf_bytes = pdf_factory()
    res = helper.post(
        "/api/contract/upload",
        data={
            "file": (BytesIO(pdf_bytes), "labor.pdf", "application/pdf"),
            "contract_type": "labor",
        },
        content_type="multipart/form-data",
    )
    cid = res.get_json()["data"]["contract_id"]

    with app.app_context():
        from backend.app.extensions import db
        from backend.app.models.clause import Clause
        from backend.app.models.contract import Contract
        from backend.app.models.missing import MissingItem
        from backend.app.models.risk import RiskItem

        contract = Contract.query.get(cid)
        contract.status = "done"
        contract.key_info = {
            "party_a": "Acme Corporation",
            "party_b": "John Doe",
            "salary_amount": "5000 USD",
            "work_location": "London Office",
            "contract_term": "24 months",
        }
        contract.desensitized_text = (
            "[EMPLOYER] hereby employs [EMPLOYEE] for a term of 24 months. "
            "Either party may terminate at will."
        )
        contract.redaction_summary = [{"type": "EMAIL", "count": 2}, {"type": "PHONE", "count": 1}]
        contract.total_redactions = 3

        c1 = Clause(
            contract_id=cid,
            index_num=1,
            heading="Article 1 Term",
            content="Contract term is 24 months from 2024-01-01.",
            category="general",
        )
        c2 = Clause(
            contract_id=cid,
            index_num=2,
            heading="Article 2 Salary",
            content="Salary subject to company discretion.",
            category="salary",
        )
        c3 = Clause(
            contract_id=cid,
            index_num=3,
            heading="Article 3 Termination",
            content="Either party may terminate at will, no notice required.",
            category="termination",
        )
        db.session.add_all([c1, c2, c3])
        db.session.flush()

        db.session.add_all(
            [
                RiskItem(
                    contract_id=cid,
                    clause_id=c2.id,
                    risk_level="medium",
                    risk_type="wage_payment_unclear",
                    evidence_sentence="Salary subject to company discretion.",
                    explanation="Wage payment is unclear and may allow arbitrary deductions.",
                    llm_status="skipped",
                    legal_reference="For reference only.",
                ),
                RiskItem(
                    contract_id=cid,
                    clause_id=c3.id,
                    risk_level="high",
                    risk_type="vague_termination",
                    evidence_sentence="Either party may terminate at will.",
                    explanation="Vague termination strips employee protections.",
                    llm_status="skipped",
                    legal_reference="For reference only.",
                ),
            ]
        )
        db.session.add(
            MissingItem(
                contract_id=cid,
                item_name="Dispute Resolution",
                description="No dispute resolution clause was detected.",
                potential_risk="Conflicts may be costly to resolve.",
            )
        )
        db.session.commit()

    return cid
