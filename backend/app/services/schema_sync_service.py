from sqlalchemy import inspect, text

from ..extensions import db
from ..models.admin_audit_log import AdminAuditLog
from ..models.analysis_job import AnalysisJob
from ..models.clause import Clause
from ..models.contract import Contract
from ..models.game_question import GameQuestion
from ..models.missing import MissingItem
from ..models.risk import RiskItem
from ..models.share_link import ShareLink
from ..models.template_clause import TemplateClause
from ..models.user import User


def ensure_runtime_schema() -> None:
    """
    Minimal runtime schema sync for environments without migrations.
    """
    # Create all tables that don't exist yet
    db.create_all()

    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    if "users" in table_names:
        columns = {c["name"] for c in inspector.get_columns("users")}
        if "is_active" not in columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
        if "deactivated_at" not in columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN deactivated_at DATETIME NULL"))
        db.session.commit()

    if "risk_items" in table_names:
        columns = {c["name"] for c in inspector.get_columns("risk_items")}
        if "llm_explanation" not in columns:
            db.session.execute(text("ALTER TABLE risk_items ADD COLUMN llm_explanation TEXT NULL"))
        if "llm_status" not in columns:
            db.session.execute(
                text("ALTER TABLE risk_items ADD COLUMN llm_status VARCHAR(32) NOT NULL DEFAULT 'skipped'")
            )
        if "llm_error_code" not in columns:
            db.session.execute(text("ALTER TABLE risk_items ADD COLUMN llm_error_code VARCHAR(64) NULL"))
        if "llm_latency_ms" not in columns:
            db.session.execute(text("ALTER TABLE risk_items ADD COLUMN llm_latency_ms INT NULL"))
        db.session.commit()

    if "contracts" in table_names:
        columns = {c["name"] for c in inspector.get_columns("contracts")}
        if "redaction_summary" not in columns:
            db.session.execute(text("ALTER TABLE contracts ADD COLUMN redaction_summary JSON NULL"))
        if "total_redactions" not in columns:
            db.session.execute(text("ALTER TABLE contracts ADD COLUMN total_redactions INT NOT NULL DEFAULT 0"))
        db.session.commit()

    if "analysis_jobs" in table_names:
        columns = {c["name"] for c in inspector.get_columns("analysis_jobs")}
        if "progress_message" not in columns:
            db.session.execute(text("ALTER TABLE analysis_jobs ADD COLUMN progress_message VARCHAR(255) NULL"))
        db.session.commit()

    AdminAuditLog.__table__.create(bind=db.engine, checkfirst=True)
    TemplateClause.__table__.create(bind=db.engine, checkfirst=True)
