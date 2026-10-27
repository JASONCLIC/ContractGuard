from datetime import datetime

from flask import Blueprint, request

from ..middleware.auth_middleware import get_current_user_id, require_login
from ..middleware.rate_limiter import check_limit
from ..models.contract import Contract
from ..models.share_link import ShareLink
from ..services.desensitizer import desensitize_text
from ..services.share_service import create_share_link, verify_share_password
from ..utils.response import fail, success

bp = Blueprint("share", __name__)


@bp.post("/create")
@require_login
def create():
    payload = request.get_json(silent=True) or {}
    contract_id = payload.get("contract_id")
    contract = Contract.query.get(contract_id)
    if not contract:
        return fail(2001, "contract not found", status=404)
    if contract.user_id != get_current_user_id():
        return fail(2002, "contract access denied", status=403)

    share = create_share_link(
        contract_id=contract_id,
        password=payload.get("password"),
        expires_hours=min(int(payload.get("expires_hours", 72)), 24 * 7),
        max_access_count=int(payload.get("max_access_count", 50)),
    )
    return success(
        {
            "token": share.token,
            "share_url": f"/api/share/{share.token}",
            "expires_at": share.expires_at.isoformat(),
        }
    )


@bp.get("/<token>")
def get_share(token):
    share = ShareLink.query.filter_by(token=token).first()
    if not share:
        return fail(4001, "invalid share token", status=404)
    if share.expires_at < datetime.utcnow():
        return fail(4001, "share link expired", status=410)
    if share.access_count >= share.max_access_count:
        return fail(4003, "share access limit reached", status=429)
    ip = request.remote_addr or "unknown"
    if not check_limit(f"{token}:{ip}", limit=10, window_sec=60):
        return fail(4003, "too many requests", status=429)

    password = request.args.get("password")
    if not verify_share_password(share, password):
        return fail(4002, "wrong password", status=401)

    contract = Contract.query.get(share.contract_id)
    share.access_count += 1
    from ..extensions import db
    if not contract.desensitized_text:
        result = desensitize_text(contract.raw_text, key_info=contract.key_info or {})
        contract.desensitized_text = result.redacted_text
        contract.redaction_summary = result.redaction_summary
        contract.total_redactions = result.total_redactions
    db.session.commit()
    return success(
        {
            "contract_id": contract.id,
            "text": contract.desensitized_text,
            "key_info": contract.key_info or {},
            "redaction_summary": contract.redaction_summary or [],
            "total_redactions": contract.total_redactions or 0,
        }
    )


@bp.post("/<token>/verify")
def verify(token):
    share = ShareLink.query.filter_by(token=token).first()
    if not share:
        return fail(4001, "invalid share token", status=404)
    payload = request.get_json(silent=True) or {}
    ok = verify_share_password(share, payload.get("password"))
    if not ok:
        return fail(4002, "wrong password", status=401)
    return success({"verified": True})


@bp.delete("/<token>")
@require_login
def revoke(token):
    share = ShareLink.query.filter_by(token=token).first()
    if not share:
        return fail(4001, "invalid share token", status=404)
    contract = Contract.query.get(share.contract_id)
    if not contract or contract.user_id != get_current_user_id():
        return fail(2002, "contract access denied", status=403)
    from ..extensions import db
    db.session.delete(share)
    db.session.commit()
    return success({"revoked": True})
