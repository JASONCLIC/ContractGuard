from functools import wraps

from flask import request, session

from ..models.contract import Contract
from ..models.user import User
from ..services.admin_service import is_admin_user
from ..utils.response import fail


def get_session_token():
    return request.cookies.get("session_token")


def get_current_user_id():
    return session.get("user_id")


def get_current_user():
    user_id = get_current_user_id()
    if not user_id:
        return None
    return User.query.get(user_id)


def require_login(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return fail(2002, "login required", status=401)
        if not user.is_active:
            session.pop("user_id", None)
            return fail(2004, "account disabled", status=403)
        return view_func(*args, **kwargs)

    return wrapper


def require_admin(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return fail(2002, "login required", status=401)
        if not is_admin_user(user):
            return fail(2003, "admin access required", status=403)
        return view_func(*args, **kwargs)

    return wrapper


def require_contract_access(view_func):
    @wraps(view_func)
    def wrapper(contract_id, *args, **kwargs):
        user = get_current_user()
        contract = Contract.query.get(contract_id)
        if not contract:
            return fail(2001, "contract not found", status=404)
        if not user:
            return fail(2002, "login required", status=401)
        if not user.is_active:
            session.pop("user_id", None)
            return fail(2004, "account disabled", status=403)
        if contract.user_id != user.id and not is_admin_user(user):
            return fail(2002, "contract access denied", status=403)
        return view_func(contract_id, *args, **kwargs)

    return wrapper
