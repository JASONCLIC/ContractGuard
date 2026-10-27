from flask import Blueprint, request

from ..middleware.auth_middleware import get_current_user_id, require_login
from ..models.clause import Clause
from ..models.contract import Contract
from ..models.missing import MissingItem
from ..models.risk import RiskItem
from ..utils.response import fail, success

bp = Blueprint("analysis", __name__)


def _check_access(contract_id):
    current_user_id = get_current_user_id()
    if not current_user_id:
        return None, fail(2002, "login required", status=401)
    contract = Contract.query.get(contract_id)
    if not contract:
        return None, fail(2001, "contract not found", status=404)
    if contract.user_id != current_user_id:
        return None, fail(2002, "contract access denied", status=403)
    if contract.status != "done":
        return None, fail(2003, "contract not ready", status=409)
    return contract, None


@bp.get("/<int:contract_id>/structure")
@require_login
def structure(contract_id):
    _, error = _check_access(contract_id)
    if error:
        return error
    clauses = Clause.query.filter_by(contract_id=contract_id).order_by(Clause.index_num.asc()).all()
    return success(
        [
            {
                "id": c.id,
                "index_num": c.index_num,
                "heading": c.heading,
                "content": c.content,
                "category": c.category,
            }
            for c in clauses
        ]
    )


@bp.get("/<int:contract_id>/summary")
@require_login
def summary(contract_id):
    contract, error = _check_access(contract_id)
    if error:
        return error
    return success(contract.key_info or {})


@bp.get("/<int:contract_id>/risks")
@require_login
def risks(contract_id):
    _, error = _check_access(contract_id)
    if error:
        return error
    level = request.args.get("level")
    q = RiskItem.query.filter_by(contract_id=contract_id)
    if level:
        q = q.filter_by(risk_level=level)
    rows = q.all()
    clause_rows = Clause.query.filter_by(contract_id=contract_id).all()
    clause_index_map = {c.id: c.index_num for c in clause_rows}
    return success(
        [
            {
                "id": r.id,
                "index_num": clause_index_map.get(r.clause_id),
                "risk_level": r.risk_level,
                "risk_type": r.risk_type,
                "evidence_sentence": r.evidence_sentence,
                "explanation": r.explanation,
                "llm_explanation": r.llm_explanation,
                "llm_status": r.llm_status,
                "llm_error_code": r.llm_error_code,
                "llm_latency_ms": r.llm_latency_ms,
                "legal_reference": r.legal_reference,
                "clause_id": r.clause_id,
            }
            for r in rows
        ]
    )


@bp.get("/<int:contract_id>/missing")
@require_login
def missing(contract_id):
    _, error = _check_access(contract_id)
    if error:
        return error
    rows = MissingItem.query.filter_by(contract_id=contract_id).all()
    return success(
        [
            {
                "id": m.id,
                "item_name": m.item_name,
                "description": m.description,
                "potential_risk": m.potential_risk,
            }
            for m in rows
        ]
    )
