from datetime import datetime

from flask import Blueprint, request
from sqlalchemy import func

from ..extensions import db
from ..middleware.auth_middleware import get_current_user, require_admin
from ..models.admin_audit_log import AdminAuditLog
from ..models.analysis_job import AnalysisJob
from ..models.clause import Clause
from ..models.contract import Contract
from ..models.game_question import GameQuestion
from ..models.missing import MissingItem
from ..models.risk import RiskItem
from ..models.user import User
from ..services.admin_audit_service import log_admin_action
from ..services.admin_service import is_admin_user
from ..services.template_library_service import (
    create_template_clause,
    delete_template_clause,
    get_template_clause,
    list_all_template_clauses,
    safe_seed_template_library,
    update_template_clause,
)
from ..utils.response import fail, success

bp = Blueprint("admin", __name__)


def _clamp_limit(raw, default=20, max_value=200):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, min(value, max_value))


def _clamp_offset(raw):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return max(0, value)


def _parse_date_start(date_s):
    if not date_s:
        return None
    try:
        return datetime.fromisoformat(date_s)
    except ValueError:
        return None


def _parse_date_end(date_s):
    if not date_s:
        return None


def _validate_template_payload(payload):
    required = ["category_key", "category_label", "title", "content"]
    for key in required:
        if not (payload.get(key) or "").strip():
            return False
    sort_order = payload.get("sort_order", 1)
    try:
        int(sort_order)
    except (TypeError, ValueError):
        return False
    return True
    try:
        dt = datetime.fromisoformat(date_s)
        return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    except ValueError:
        return None


@bp.get("/overview")
@require_admin
def overview():
    total_users = User.query.count()
    total_contracts = Contract.query.count()
    total_risks = RiskItem.query.count()
    total_jobs = AnalysisJob.query.count()

    status_rows = (
        Contract.query.with_entities(Contract.status, func.count(Contract.id))
        .group_by(Contract.status)
        .all()
    )
    contract_status = {status or "unknown": count for status, count in status_rows}

    risk_rows = (
        RiskItem.query.with_entities(RiskItem.risk_level, func.count(RiskItem.id))
        .group_by(RiskItem.risk_level)
        .all()
    )
    risk_level_dist = {level or "unknown": count for level, count in risk_rows}

    latest_contracts = (
        Contract.query.order_by(Contract.created_at.desc()).limit(8).all()
    )
    latest_users = User.query.order_by(User.created_at.desc()).limit(8).all()

    return success(
        {
            "stats": {
                "users": total_users,
                "contracts": total_contracts,
                "risks": total_risks,
                "jobs": total_jobs,
            },
            "contract_status": contract_status,
            "risk_level_dist": risk_level_dist,
            "latest_contracts": [
                {
                    "id": c.id,
                    "title": c.title,
                    "status": c.status,
                    "contract_type": c.contract_type,
                    "created_at": c.created_at.isoformat(),
                    "user_id": c.user_id,
                }
                for c in latest_contracts
            ],
            "latest_users": [
                {
                    "id": u.id,
                    "name": u.name,
                    "email": u.email,
                    "created_at": u.created_at.isoformat(),
                }
                for u in latest_users
            ],
        }
    )


@bp.get("/users")
@require_admin
def users():
    limit = _clamp_limit(request.args.get("limit"), default=50)
    offset = _clamp_offset(request.args.get("offset"))
    keyword = (request.args.get("keyword") or "").strip().lower()
    is_active_raw = request.args.get("is_active")

    query = User.query
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((User.name.ilike(like)) | (User.email.ilike(like)))
    if is_active_raw in {"true", "false"}:
        query = query.filter(User.is_active.is_(is_active_raw == "true"))

    rows = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    total = query.count()
    return success(
        {
            "total": total,
            "items": [
                {
                    "id": u.id,
                    "name": u.name,
                    "email": u.email,
                    "is_active": bool(u.is_active),
                    "is_admin": is_admin_user(u),
                    "deactivated_at": u.deactivated_at.isoformat() if u.deactivated_at else None,
                    "created_at": u.created_at.isoformat(),
                }
                for u in rows
            ],
        }
    )


@bp.get("/contracts")
@require_admin
def contracts_search():
    limit = _clamp_limit(request.args.get("limit"), default=50)
    offset = _clamp_offset(request.args.get("offset"))
    keyword = (request.args.get("keyword") or "").strip().lower()
    status = (request.args.get("status") or "").strip().lower()
    contract_type = (request.args.get("contract_type") or "").strip().lower()
    user_email = (request.args.get("user_email") or "").strip().lower()
    date_from = _parse_date_start(request.args.get("date_from"))
    date_to = _parse_date_end(request.args.get("date_to"))

    query = Contract.query.join(User, User.id == Contract.user_id)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((Contract.title.ilike(like)) | (User.email.ilike(like)))
    if status:
        query = query.filter(Contract.status == status)
    if contract_type:
        query = query.filter(Contract.contract_type == contract_type)
    if user_email:
        query = query.filter(User.email.ilike(f"%{user_email}%"))
    if date_from:
        query = query.filter(Contract.created_at >= date_from)
    if date_to:
        query = query.filter(Contract.created_at <= date_to)

    total = query.count()
    rows = query.order_by(Contract.created_at.desc()).offset(offset).limit(limit).all()
    owner_ids = {c.user_id for c in rows}
    owners = {u.id: u for u in User.query.filter(User.id.in_(owner_ids)).all()} if owner_ids else {}
    return success(
        {
            "total": total,
            "items": [
                {
                    "id": c.id,
                    "title": c.title,
                    "status": c.status,
                    "contract_type": c.contract_type,
                    "created_at": c.created_at.isoformat(),
                    "user_id": c.user_id,
                    "user_email": owners.get(c.user_id).email if owners.get(c.user_id) else None,
                    "file_size": c.file_size,
                }
                for c in rows
            ],
        }
    )


@bp.get("/contracts/<int:contract_id>/detail")
@require_admin
def contract_detail(contract_id):
    contract = Contract.query.get(contract_id)
    if not contract:
        return fail(2001, "contract not found", status=404)

    clauses = Clause.query.filter_by(contract_id=contract_id).order_by(Clause.index_num.asc()).all()
    risks = RiskItem.query.filter_by(contract_id=contract_id).all()
    missing_items = MissingItem.query.filter_by(contract_id=contract_id).all()
    jobs = AnalysisJob.query.filter_by(contract_id=contract_id).order_by(AnalysisJob.created_at.desc()).all()
    user = User.query.get(contract.user_id)

    return success(
        {
            "contract": {
                "id": contract.id,
                "title": contract.title,
                "status": contract.status,
                "contract_type": contract.contract_type,
                "created_at": contract.created_at.isoformat(),
                "file_size": contract.file_size,
                "key_info": contract.key_info or {},
            },
            "owner": {
                "id": user.id if user else None,
                "name": user.name if user else None,
                "email": user.email if user else None,
            },
            "clauses": [
                {
                    "id": c.id,
                    "index_num": c.index_num,
                    "heading": c.heading,
                    "category": c.category,
                    "content": c.content,
                }
                for c in clauses
            ],
            "risks": [
                {
                    "id": r.id,
                    "risk_level": r.risk_level,
                    "risk_type": r.risk_type,
                    "evidence_sentence": r.evidence_sentence,
                    "explanation": r.explanation,
                    "llm_explanation": r.llm_explanation,
                    "llm_status": r.llm_status,
                    "llm_error_code": r.llm_error_code,
                    "llm_latency_ms": r.llm_latency_ms,
                    "legal_reference": r.legal_reference,
                }
                for r in risks
            ],
            "missing_items": [
                {
                    "id": m.id,
                    "item_name": m.item_name,
                    "description": m.description,
                    "potential_risk": m.potential_risk,
                }
                for m in missing_items
            ],
            "jobs": [
                {
                    "id": j.id,
                    "job_type": j.job_type,
                    "status": j.status,
                    "progress_percent": j.progress_percent,
                    "error_message": j.error_message,
                    "created_at": j.created_at.isoformat(),
                }
                for j in jobs
            ],
        }
    )


@bp.patch("/users/<int:user_id>/status")
@require_admin
def update_user_status(user_id):
    admin = get_current_user()
    payload = request.get_json(silent=True) or {}
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        return fail(1001, "enabled must be boolean")

    user = User.query.get(user_id)
    if not user:
        return fail(2001, "user not found", status=404)
    if admin and user.id == admin.id and not enabled:
        return fail(1001, "cannot disable current admin user")
    if is_admin_user(user) and not enabled:
        return fail(1001, "cannot disable admin account")

    user.is_active = enabled
    user.deactivated_at = None if enabled else datetime.utcnow()
    db.session.commit()

    log_admin_action(
        admin_user_id=admin.id if admin else None,
        action="user.status.update",
        target_type="user",
        target_id=user.id,
        summary=f"set user {user.email} active={enabled}",
        detail={"email": user.email, "enabled": enabled},
    )
    return success({"id": user.id, "is_active": user.is_active})


@bp.delete("/users/<int:user_id>")
@require_admin
def delete_user(user_id):
    admin = get_current_user()
    user = User.query.get(user_id)
    if not user:
        return fail(2001, "user not found", status=404)
    if admin and user.id == admin.id:
        return fail(1001, "cannot delete current admin user")
    if is_admin_user(user):
        return fail(1001, "cannot delete admin account")

    detail = {"email": user.email, "name": user.name}
    db.session.delete(user)
    db.session.commit()

    log_admin_action(
        admin_user_id=admin.id if admin else None,
        action="user.delete",
        target_type="user",
        target_id=user_id,
        summary=f"deleted user {detail['email']}",
        detail=detail,
    )
    return success({"deleted": True})


@bp.get("/game-questions")
@require_admin
def game_questions():
    rows = GameQuestion.query.order_by(GameQuestion.id.asc()).all()
    return success(
        [
            {
                "id": q.id,
                "clause_text": q.clause_text,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "difficulty": q.difficulty,
            }
            for q in rows
        ]
    )


@bp.post("/game-questions")
@require_admin
def create_game_question():
    admin = get_current_user()
    payload = request.get_json(silent=True) or {}
    clause_text = (payload.get("clause_text") or "").strip()
    correct_answer = (payload.get("correct_answer") or "").strip().lower()
    explanation = (payload.get("explanation") or "").strip()
    difficulty = (payload.get("difficulty") or "medium").strip().lower()

    if not clause_text or correct_answer not in {"safe", "risk"} or not explanation:
        return fail(1001, "invalid payload")
    if difficulty not in {"easy", "medium", "hard"}:
        return fail(1001, "invalid difficulty")

    row = GameQuestion(
        clause_text=clause_text,
        correct_answer=correct_answer,
        explanation=explanation,
        difficulty=difficulty,
    )
    db.session.add(row)
    db.session.commit()

    log_admin_action(
        admin_user_id=admin.id if admin else None,
        action="game_question.create",
        target_type="game_question",
        target_id=row.id,
        summary=f"created game question #{row.id}",
        detail={"difficulty": row.difficulty, "correct_answer": row.correct_answer},
    )
    return success({"id": row.id})


@bp.put("/game-questions/<int:question_id>")
@require_admin
def update_game_question(question_id):
    admin = get_current_user()
    row = GameQuestion.query.get(question_id)
    if not row:
        return fail(2001, "question not found", status=404)

    payload = request.get_json(silent=True) or {}
    clause_text = (payload.get("clause_text") or row.clause_text).strip()
    correct_answer = (payload.get("correct_answer") or row.correct_answer).strip().lower()
    explanation = (payload.get("explanation") or row.explanation).strip()
    difficulty = (payload.get("difficulty") or row.difficulty).strip().lower()

    if not clause_text or correct_answer not in {"safe", "risk"} or not explanation:
        return fail(1001, "invalid payload")
    if difficulty not in {"easy", "medium", "hard"}:
        return fail(1001, "invalid difficulty")

    row.clause_text = clause_text
    row.correct_answer = correct_answer
    row.explanation = explanation
    row.difficulty = difficulty
    db.session.commit()

    log_admin_action(
        admin_user_id=admin.id if admin else None,
        action="game_question.update",
        target_type="game_question",
        target_id=row.id,
        summary=f"updated game question #{row.id}",
        detail={"difficulty": row.difficulty, "correct_answer": row.correct_answer},
    )
    return success({"updated": True})


@bp.delete("/game-questions/<int:question_id>")
@require_admin
def delete_game_question(question_id):
    admin = get_current_user()
    row = GameQuestion.query.get(question_id)
    if not row:
        return fail(2001, "question not found", status=404)

    db.session.delete(row)
    db.session.commit()
    log_admin_action(
        admin_user_id=admin.id if admin else None,
        action="game_question.delete",
        target_type="game_question",
        target_id=question_id,
        summary=f"deleted game question #{question_id}",
        detail={},
    )
    return success({"deleted": True})


@bp.get("/template-clauses")
@require_admin
def template_clauses():
    safe_seed_template_library()
    rows = list_all_template_clauses(limit=1000)
    return success(
        [
            {
                "id": r.id,
                "category_key": r.category_key,
                "category_label": r.category_label,
                "title": r.title,
                "content": r.content,
                "tip": r.tip or "",
                "sort_order": r.sort_order,
                "is_active": bool(r.is_active),
            }
            for r in rows
        ]
    )


@bp.post("/template-clauses")
@require_admin
def create_template():
    admin = get_current_user()
    payload = request.get_json(silent=True) or {}
    if not _validate_template_payload(payload):
        return fail(1001, "invalid payload")

    row = create_template_clause(payload)
    log_admin_action(
        admin_user_id=admin.id if admin else None,
        action="template_clause.create",
        target_type="template_clause",
        target_id=row.id,
        summary="created template clause",
        detail={"category_key": row.category_key, "title": row.title},
    )
    return success({"id": row.id})


@bp.put("/template-clauses/<int:template_id>")
@require_admin
def update_template(template_id):
    admin = get_current_user()
    payload = request.get_json(silent=True) or {}
    row = get_template_clause(template_id)
    if not row:
        return fail(2001, "template clause not found", status=404)

    merged = {
        "category_key": payload.get("category_key", row.category_key),
        "category_label": payload.get("category_label", row.category_label),
        "title": payload.get("title", row.title),
        "content": payload.get("content", row.content),
        "tip": payload.get("tip", row.tip or ""),
        "sort_order": payload.get("sort_order", row.sort_order),
        "is_active": payload.get("is_active", row.is_active),
    }
    if not _validate_template_payload(merged):
        return fail(1001, "invalid payload")

    updated = update_template_clause(row, payload)
    log_admin_action(
        admin_user_id=admin.id if admin else None,
        action="template_clause.update",
        target_type="template_clause",
        target_id=updated.id,
        summary="updated template clause",
        detail={"category_key": updated.category_key, "title": updated.title},
    )
    return success({"updated": True})


@bp.delete("/template-clauses/<int:template_id>")
@require_admin
def delete_template(template_id):
    admin = get_current_user()
    row = get_template_clause(template_id)
    if not row:
        return fail(2001, "template clause not found", status=404)
    detail = {"category_key": row.category_key, "title": row.title}
    delete_template_clause(row)
    log_admin_action(
        admin_user_id=admin.id if admin else None,
        action="template_clause.delete",
        target_type="template_clause",
        target_id=template_id,
        summary="deleted template clause",
        detail=detail,
    )
    return success({"deleted": True})


@bp.get("/audit-logs")
@require_admin
def audit_logs():
    limit = _clamp_limit(request.args.get("limit"), default=50)
    offset = _clamp_offset(request.args.get("offset"))
    action = (request.args.get("action") or "").strip()
    keyword = (request.args.get("keyword") or "").strip().lower()

    query = AdminAuditLog.query
    if action:
        query = query.filter(AdminAuditLog.action == action)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (AdminAuditLog.summary.ilike(like))
            | (AdminAuditLog.target_type.ilike(like))
            | (AdminAuditLog.target_id.ilike(like))
        )
    total = query.count()
    rows = query.order_by(AdminAuditLog.created_at.desc()).offset(offset).limit(limit).all()
    admin_ids = {r.admin_user_id for r in rows if r.admin_user_id}
    admins = {u.id: u for u in User.query.filter(User.id.in_(admin_ids)).all()} if admin_ids else {}

    return success(
        {
            "total": total,
            "items": [
                {
                    "id": r.id,
                    "admin_user_id": r.admin_user_id,
                    "admin_email": admins.get(r.admin_user_id).email if admins.get(r.admin_user_id) else None,
                    "action": r.action,
                    "target_type": r.target_type,
                    "target_id": r.target_id,
                    "summary": r.summary,
                    "detail_json": r.detail_json or {},
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ],
        }
    )

