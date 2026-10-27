from ..extensions import db


class Clause(db.Model):
    __tablename__ = "clauses"
    __table_args__ = (db.UniqueConstraint("contract_id", "index_num", name="uq_contract_clause_idx"),)

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("analysis_jobs.id", ondelete="SET NULL"))
    index_num = db.Column(db.Integer, nullable=False)
    heading = db.Column(db.String(255))
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(64), nullable=False, default="general")
