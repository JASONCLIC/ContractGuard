from flask import Blueprint, request

from ..extensions import db
from ..middleware.auth_middleware import get_current_user_id, require_login
from ..models.analysis_job import AnalysisJob
from ..models.contract import Contract
from ..routes.contract import _run_analysis_and_store
from ..utils.response import fail, success

bp = Blueprint("jobs", __name__)


@bp.post("")
@require_login
def create_job():
    payload = request.get_json(silent=True) or {}
    contract_id = payload.get("contract_id")
    job_type = payload.get("job_type", "full_analysis")
    contract = Contract.query.get(contract_id)
    if not contract:
        return fail(2001, "contract not found", status=404)
    if contract.user_id != get_current_user_id():
        return fail(2002, "contract access denied", status=403)

    job = AnalysisJob(contract_id=contract.id, job_type=job_type, status="running")
    db.session.add(job)
    db.session.commit()
    if job_type == "full_analysis":
        _run_analysis_and_store(contract, job)
    return success({"job_id": job.id, "status": job.status})


@bp.get("/<int:job_id>")
@require_login
def get_job(job_id):
    job = AnalysisJob.query.get(job_id)
    if not job:
        return fail(3001, "job not found", status=404)
    contract = Contract.query.get(job.contract_id)
    if contract and contract.user_id != get_current_user_id():
        return fail(2002, "contract access denied", status=403)
    return success(
        {
            "job_id": job.id,
            "contract_id": job.contract_id,
            "status": job.status,
            "progress_percent": job.progress_percent,
            "progress_message": job.progress_message,
            "error_message": job.error_message,
        }
    )
