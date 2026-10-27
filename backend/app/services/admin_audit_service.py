from typing import Any, Dict, Optional, Union

from ..extensions import db
from ..models.admin_audit_log import AdminAuditLog


def log_admin_action(
    *,
    admin_user_id: Optional[int],
    action: str,
    target_type: str,
    target_id: Optional[Union[str, int]],
    summary: str,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    row = AdminAuditLog(
        admin_user_id=admin_user_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        summary=summary,
        detail_json=detail or {},
    )
    db.session.add(row)
    db.session.commit()
