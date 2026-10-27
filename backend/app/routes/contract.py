import hashlib
from datetime import datetime
import threading

from flask import Blueprint, current_app, request

from ..extensions import db
from ..middleware.auth_middleware import get_current_user_id, require_login
from ..models.analysis_job import AnalysisJob
from ..models.clause import Clause
from ..models.contract import Contract
from ..models.missing import MissingItem
from ..models.risk import RiskItem
from ..services.parser import parse_contract_text
from ..utils.file_handler import extract_text_from_upload
from ..utils.file_security import validate_upload
from ..utils.response import fail, success
from ..utils.text_cleaner import normalize_text
from ..utils.validators import validate_text_input

bp = Blueprint("contract", __name__)


def _run_analysis_in_background(app, contract_id: int, job_id: int):
    with app.app_context():
        contract = Contract.query.get(contract_id)
        job = AnalysisJob.query.get(job_id)
        if not contract or not job:
            return
        try:
            _run_analysis_and_store(contract, job)
        except Exception:
            # Job status/error is already handled in _run_analysis_and_store.
            pass


def _start_background_analysis(contract_id: int, job_id: int):
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_run_analysis_in_background,
        args=(app, contract_id, job_id),
        daemon=True,
    )
    thread.start()


def _run_analysis_and_store(contract: Contract, job: AnalysisJob):
    def _update_job_progress(percent: int, message: str):
        job.progress_percent = max(0, min(99, int(percent)))
        job.progress_message = message
        db.session.commit()

    try:
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.error_message = None
        _update_job_progress(5, "Preparing contract analysis")

        result = parse_contract_text(
            contract.raw_text,
            contract.contract_type,
            progress_callback=_update_job_progress,
        )
        _update_job_progress(96, "Saving analysis result")
        Clause.query.filter_by(contract_id=contract.id).delete()
        RiskItem.query.filter_by(contract_id=contract.id).delete()
        MissingItem.query.filter_by(contract_id=contract.id).delete()

        clause_map = {}
        for c in result["clauses"]:
            row = Clause(
                contract_id=contract.id,
                job_id=job.id,
                index_num=c["index_num"],
                heading=c["heading"],
                content=c["content"],
                category=c["category"],
            )
            db.session.add(row)
            db.session.flush()
            clause_map[c["index_num"]] = row.id

        for r in result["risks"]:
            db.session.add(
                RiskItem(
                    contract_id=contract.id,
                    clause_id=clause_map.get(r["index_num"]),
                    job_id=job.id,
                    risk_level=r["risk_level"],
                    risk_type=r["risk_type"],
                    evidence_sentence=r["evidence_sentence"],
                    explanation=r["explanation"],
                    llm_explanation=r.get("llm_explanation"),
                    llm_status=r.get("llm_status", "skipped"),
                    llm_error_code=r.get("llm_error_code"),
                    llm_latency_ms=r.get("llm_latency_ms"),
                    legal_reference=r["legal_reference"],
                )
            )

        for m in result["missing_items"]:
            db.session.add(
                MissingItem(
                    contract_id=contract.id,
                    job_id=job.id,
                    item_name=m["item_name"],
                    description=m["description"],
                    potential_risk=m["potential_risk"],
                )
            )

        contract.key_info = result["key_info"]
        contract.desensitized_text = result.get("desensitized_text")
        contract.redaction_summary = result.get("redaction_summary") or []
        contract.total_redactions = int(result.get("total_redactions") or 0)
        contract.status = "done"
        job.status = "success"
        job.progress_percent = 100
        job.progress_message = "Analysis completed"
        job.finished_at = datetime.utcnow()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        contract.status = "error"
        job.status = "failed"
        job.error_message = str(e)
        job.progress_message = "Analysis failed"
        job.finished_at = datetime.utcnow()
        db.session.commit()
        raise e


@bp.post("/upload")
@require_login
def upload_contract():
    file = request.files.get("file")
    ok, message = validate_upload(file)
    if not ok:
        return fail(1002, message, status=400)

    try:
        raw_text = normalize_text(extract_text_from_upload(file))
    except ValueError as exc:
        return fail(1004, str(exc), status=400)
    except Exception:
        return fail(1004, "Failed to parse PDF. The file may be encrypted, scanned-only, or corrupted.", status=400)
    valid, text_msg = validate_text_input(raw_text)
    if not valid:
        return fail(1004, text_msg)

    user_id = get_current_user_id()
    if not user_id:
        return fail(2002, "login required", status=401)

    file_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    existing = Contract.query.filter_by(user_id=user_id, file_hash=file_hash).first()
    if existing:
        if existing.status == "done":
            return success({"contract_id": existing.id, "job_id": None, "duplicated": True})
        # Previous analysis failed or is stuck — delete and re-run
        db.session.delete(existing)
        db.session.commit()

    contract = Contract(
        user_id=user_id,
        session_token=None,
        title=file.filename or "uploaded_contract",
        contract_type=request.form.get("contract_type", "labor"),
        raw_text=raw_text,
        status="uploaded",
        file_hash=file_hash,
        file_size=len(raw_text.encode("utf-8")),
    )
    db.session.add(contract)
    db.session.flush()

    job = AnalysisJob(contract_id=contract.id, job_type="full_analysis", status="running")
    job.progress_percent = 3
    job.progress_message = "Queued for analysis"
    db.session.add(job)
    db.session.commit()

    _start_background_analysis(contract.id, job.id)
    return success({"contract_id": contract.id, "job_id": job.id})


@bp.post("/paste")
@require_login
def paste_contract():
    payload = request.get_json(silent=True) or {}
    raw_text = normalize_text(payload.get("text", ""))
    valid, text_msg = validate_text_input(raw_text)
    if not valid:
        return fail(1001, text_msg)

    user_id = get_current_user_id()
    if not user_id:
        return fail(2002, "login required", status=401)

    contract = Contract(
        user_id=user_id,
        session_token=None,
        title=payload.get("title", "pasted_contract"),
        contract_type=payload.get("contract_type", "labor"),
        raw_text=raw_text,
        status="uploaded",
        file_hash=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        file_size=len(raw_text.encode("utf-8")),
    )
    existing = Contract.query.filter_by(
        user_id=user_id,
        file_hash=contract.file_hash,
    ).first()
    if existing:
        if existing.status == "done":
            return success({"contract_id": existing.id, "job_id": None, "duplicated": True})
        # Previous analysis failed or is stuck — delete and re-run
        db.session.delete(existing)
        db.session.commit()

    db.session.add(contract)
    db.session.flush()
    job = AnalysisJob(contract_id=contract.id, job_type="full_analysis", status="running")
    job.progress_percent = 3
    job.progress_message = "Queued for analysis"
    db.session.add(job)
    db.session.commit()

    _start_background_analysis(contract.id, job.id)
    return success({"contract_id": contract.id, "job_id": job.id})


@bp.get("/<int:contract_id>")
@require_login
def get_contract(contract_id):
    user_id = get_current_user_id()
    contract = Contract.query.get(contract_id)
    if not contract:
        return fail(2001, "contract not found", status=404)
    if contract.user_id != user_id:
        return fail(2002, "contract access denied", status=403)
    return success(
        {
            "id": contract.id,
            "title": contract.title,
            "status": contract.status,
            "contract_type": contract.contract_type,
            "created_at": contract.created_at.isoformat(),
        }
    )


@bp.delete("/<int:contract_id>")
@require_login
def delete_contract(contract_id):
    user_id = get_current_user_id()
    contract = Contract.query.get(contract_id)
    if not contract:
        return fail(2001, "contract not found", status=404)
    if contract.user_id != user_id:
        return fail(2002, "contract access denied", status=403)
    db.session.delete(contract)
    db.session.commit()
    return success({"deleted": True})
