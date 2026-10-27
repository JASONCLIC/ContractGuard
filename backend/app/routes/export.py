from datetime import datetime
from io import BytesIO

from flask import Blueprint, send_file

from ..extensions import db
from ..middleware.auth_middleware import get_current_user_id, require_login
from ..models.analysis_job import AnalysisJob
from ..models.contract import Contract
from ..models.missing import MissingItem
from ..models.risk import RiskItem
from ..services.desensitizer import desensitize_text
from ..services.pdf_exporter import build_pdf_bytes
from ..utils.response import fail, success

bp = Blueprint("export", __name__)

_export_cache = {}


@bp.post("/<int:contract_id>/pdf")
@require_login
def create_pdf_job(contract_id):
    contract = Contract.query.get(contract_id)
    if not contract:
        return fail(2001, "contract not found", status=404)
    if contract.user_id != get_current_user_id():
        return fail(2002, "contract access denied", status=403)
    if contract.status != "done":
        return fail(2003, "contract not ready", status=409)

    job = AnalysisJob(
        contract_id=contract_id,
        job_type="pdf_export",
        status="success",
        progress_percent=100,
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db.session.add(job)
    db.session.commit()

    risks = RiskItem.query.filter_by(contract_id=contract_id).all()
    missing = MissingItem.query.filter_by(contract_id=contract_id).all()
    risks_data = [
        {
            "risk_level": r.risk_level,
            "risk_type": r.risk_type,
            "explanation": r.explanation,
            "llm_explanation": r.llm_explanation,
            "evidence_sentence": r.evidence_sentence,
        }
        for r in risks
    ]
    missing_data = [
        {
            "item_name": m.item_name,
            "description": m.description,
            "potential_risk": m.potential_risk,
        }
        for m in missing
    ]
    file_bytes, mimetype, filename = build_pdf_bytes(
        contract_id,
        contract.key_info or {},
        risks_data,
        missing_data,
    )
    _export_cache[job.id] = (file_bytes, mimetype, filename)
    return success({"job_id": job.id, "status": job.status})


@bp.get("/<int:contract_id>/pdf/<int:job_id>")
@require_login
def download_pdf(contract_id, job_id):
    contract = Contract.query.get(contract_id)
    if not contract:
        return fail(2001, "contract not found", status=404)
    if contract.user_id != get_current_user_id():
        return fail(2002, "contract access denied", status=403)
    if job_id not in _export_cache:
        return fail(3001, "export file not found", status=404)
    file_bytes, mimetype, filename = _export_cache[job_id]
    return send_file(
        BytesIO(file_bytes),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


@bp.get("/<int:contract_id>/desensitized")
@require_login
def get_desensitized(contract_id):
    contract = Contract.query.get(contract_id)
    if not contract:
        return fail(2001, "contract not found", status=404)
    if contract.user_id != get_current_user_id():
        return fail(2002, "contract access denied", status=403)
    if not contract.desensitized_text:
        result = desensitize_text(contract.raw_text, key_info=contract.key_info or {})
        contract.desensitized_text = result.redacted_text
        contract.redaction_summary = result.redaction_summary
        contract.total_redactions = result.total_redactions
        db.session.commit()
    return success(
        {
            "desensitized_text": contract.desensitized_text,
            "redaction_summary": contract.redaction_summary or [],
            "total_redactions": contract.total_redactions or 0,
        }
    )
