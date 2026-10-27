from ..extensions import db


class MissingItem(db.Model):
    __tablename__ = "missing_items"

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("analysis_jobs.id", ondelete="SET NULL"))
    item_name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=False)
    potential_risk = db.Column(db.Text, nullable=False)
