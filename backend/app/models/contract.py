from datetime import datetime, timedelta

from ..extensions import db


class Contract(db.Model):
    __tablename__ = "contracts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_token = db.Column(db.String(64), index=True, nullable=True)
    title = db.Column(db.String(255), nullable=False)
    contract_type = db.Column(db.String(32), nullable=False, default="labor")
    raw_text = db.Column(db.Text, nullable=False)
    desensitized_text = db.Column(db.Text)
    redaction_summary = db.Column(db.JSON)
    total_redactions = db.Column(db.Integer, nullable=False, default=0)
    key_info = db.Column(db.JSON)
    status = db.Column(db.String(32), nullable=False, default="uploaded")
    file_hash = db.Column(db.String(64), unique=True)
    file_size = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(
        db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=7), nullable=False
    )
