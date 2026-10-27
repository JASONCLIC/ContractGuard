from ..extensions import db


class RiskItem(db.Model):
    __tablename__ = "risk_items"

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id = db.Column(db.Integer, db.ForeignKey("clauses.id", ondelete="SET NULL"))
    job_id = db.Column(db.Integer, db.ForeignKey("analysis_jobs.id", ondelete="SET NULL"))
    risk_level = db.Column(db.String(16), nullable=False, default="low", index=True)
    risk_type = db.Column(db.String(64), nullable=False)
    evidence_sentence = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    llm_explanation = db.Column(db.Text, nullable=True)
    llm_status = db.Column(db.String(32), nullable=False, default="skipped")
    llm_error_code = db.Column(db.String(64), nullable=True)
    llm_latency_ms = db.Column(db.Integer, nullable=True)
    legal_reference = db.Column(db.Text)
