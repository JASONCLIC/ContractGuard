import secrets
from datetime import datetime, timedelta
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models.share_link import ShareLink


def create_share_link(
    contract_id: int,
    password: Optional[str],
    expires_hours: int,
    max_access_count: int,
):
    token = secrets.token_urlsafe(24)
    share = ShareLink(
        contract_id=contract_id,
        token=token,
        password_hash=generate_password_hash(password) if password else None,
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
        max_access_count=max_access_count,
        is_desensitized=True,
    )
    db.session.add(share)
    db.session.commit()
    return share


def verify_share_password(share: ShareLink, password: Optional[str]):
    if not share.password_hash:
        return True
    if not password:
        return False
    return check_password_hash(share.password_hash, password)
