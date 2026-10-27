from datetime import datetime, timedelta

from ..extensions import db


class ShareLink(db.Model):
    __tablename__ = "share_links"

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    token = db.Column(db.String(128), nullable=False, unique=True)
    password_hash = db.Column(db.String(255))
    is_desensitized = db.Column(db.Boolean, nullable=False, default=True)
    access_count = db.Column(db.Integer, nullable=False, default=0)
    max_access_count = db.Column(db.Integer, nullable=False, default=50)
    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(hours=72), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
