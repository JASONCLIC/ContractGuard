from datetime import datetime

from ..extensions import db


class TemplateClause(db.Model):
    __tablename__ = "template_clauses"

    id = db.Column(db.Integer, primary_key=True)
    category_key = db.Column(db.String(64), nullable=False, index=True)
    category_label = db.Column(db.String(128), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tip = db.Column(db.Text)
    sort_order = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
