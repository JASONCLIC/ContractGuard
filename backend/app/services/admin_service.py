from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional

from ..extensions import db
from ..models.user import User
from .auth_service import hash_password


def is_admin_email(email: Optional[str]) -> bool:
    admin_email = (current_app.config.get("ADMIN_EMAIL") or "").strip().lower()
    return bool(email) and bool(admin_email) and email.strip().lower() == admin_email


def is_admin_user(user: Optional[User]) -> bool:
    if not user:
        return False
    return is_admin_email(user.email)


def ensure_admin_user() -> None:
    """
    Ensure one admin account exists.
    Uses ADMIN_NAME / ADMIN_EMAIL / ADMIN_PASSWORD from config.
    """
    admin_name = (current_app.config.get("ADMIN_NAME") or "Administrator").strip()
    admin_email = (current_app.config.get("ADMIN_EMAIL") or "").strip().lower()
    admin_password = current_app.config.get("ADMIN_PASSWORD") or ""

    if not admin_email or len(admin_password) < 6:
        return

    try:
        User.__table__.create(bind=db.engine, checkfirst=True)

        user = User.query.filter_by(email=admin_email).first()
        if user:
            # Keep name in sync for clarity in UI.
            changed = False
            if user.name != admin_name:
                user.name = admin_name
                changed = True
            if not user.is_active:
                user.is_active = True
                user.deactivated_at = None
                changed = True
            if changed:
                db.session.commit()
            return

        db.session.add(
            User(
                name=admin_name,
                email=admin_email,
                password_hash=hash_password(admin_password),
            )
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
