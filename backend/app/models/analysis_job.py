from datetime import datetime

from ..extensions import db


class AnalysisJob(db.Model):
    __tablename__ = "analysis_jobs"

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = db.Column(db.String(32), nullable=False, default="full_analysis")
    status = db.Column(db.String(32), nullable=False, default="pending", index=True)
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0, nullable=False)
    progress_percent = db.Column(db.Integer, default=0, nullable=False)
    progress_message = db.Column(db.String(255))
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
