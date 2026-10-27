from flask import Blueprint, request, session

from ..extensions import db
from ..models.user import User
from ..services.auth_service import hash_password, verify_password
from ..services.admin_service import is_admin_user
from ..utils.response import fail, success

bp = Blueprint("auth", __name__)


@bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if len(name) < 2 or "@" not in email or len(password) < 6:
        return fail(1001, "invalid registration payload")
    if User.query.filter_by(email=email).first():
        return fail(1001, "email already registered")

    user = User(name=name, email=email, password_hash=hash_password(password))
    db.session.add(user)
    db.session.commit()
    return success(
        {"user_id": user.id, "name": user.name, "email": user.email, "is_admin": is_admin_user(user)}
    )


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not verify_password(user.password_hash, password):
        return fail(1001, "email or password is incorrect", status=401)
    if not user.is_active:
        return fail(1002, "account disabled", status=403)
    session["user_id"] = user.id
    return success(
        {"user_id": user.id, "name": user.name, "email": user.email, "is_admin": is_admin_user(user)}
    )


@bp.post("/logout")
def logout():
    session.pop("user_id", None)
    return success({"logged_out": True})


@bp.get("/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return fail(2002, "login required", status=401)
    user = User.query.get(user_id)
    if not user:
        return fail(2002, "login required", status=401)
    if not user.is_active:
        session.pop("user_id", None)
        return fail(1002, "account disabled", status=403)
    return success(
        {"user_id": user.id, "name": user.name, "email": user.email, "is_admin": is_admin_user(user)}
    )
