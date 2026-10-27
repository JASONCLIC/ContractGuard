import uuid

from werkzeug.security import check_password_hash, generate_password_hash


def generate_session_token() -> str:
    return uuid.uuid4().hex


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)
