"""
P0/P1 system tests for the authentication blueprint.

Covers:
- Register → login → /auth/me → logout → /auth/me happy path (P0-AUTH-01)
- Invalid registration payloads (P1-AUTH-02)
- Duplicate email rejected
- Wrong / unknown credentials → 401
- Disabled account cannot log in (P0-AUTH-03)
- /auth/me without session → 401
- Admin login flag is_admin=True
- Email is normalised to lowercase
- Account disabled mid-session → /auth/me 403
"""

from __future__ import annotations


def test_register_login_logout_flow(client):
    """P0-AUTH-01: register → login → /me → logout → /me 401."""
    res = client.post(
        "/api/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "Secret#123"},
    )
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    assert body["code"] == 0
    assert body["data"]["email"] == "alice@example.com"
    assert body["data"]["is_admin"] is False

    res = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "Secret#123"},
    )
    assert res.status_code == 200
    assert res.get_json()["code"] == 0

    res = client.get("/api/auth/me")
    assert res.status_code == 200
    assert res.get_json()["data"]["email"] == "alice@example.com"

    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert res.get_json()["data"]["logged_out"] is True

    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_register_invalid_payloads_rejected(client):
    """P1-AUTH-02: short name / bad email / short password → 1001."""
    cases = [
        {"name": "A", "email": "good@x.com", "password": "Strong#1"},
        {"name": "Alice", "email": "no-at-sign", "password": "Strong#1"},
        {"name": "Alice", "email": "good@x.com", "password": "12345"},
    ]
    for payload in cases:
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 400, payload
        assert res.get_json()["code"] == 1001


def test_register_duplicate_email_rejected(client):
    payload = {"name": "Alice", "email": "dup@example.com", "password": "Secret#123"}
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 200

    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert res.get_json()["code"] == 1001
    assert "already registered" in res.get_json()["message"]


def test_login_wrong_password_returns_401(client):
    client.post(
        "/api/auth/register",
        json={"name": "Bob", "email": "bob@example.com", "password": "Right#1234"},
    )
    res = client.post(
        "/api/auth/login",
        json={"email": "bob@example.com", "password": "Wrong#9999"},
    )
    assert res.status_code == 401
    assert res.get_json()["code"] == 1001


def test_login_unknown_email_returns_401(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "Secret#123"},
    )
    assert res.status_code == 401
    assert res.get_json()["code"] == 1001


def test_disabled_account_cannot_login(client, app):
    """P0-AUTH-03: account disabled → 403/1002 on login."""
    client.post(
        "/api/auth/register",
        json={"name": "Carol", "email": "carol@example.com", "password": "Secret#123"},
    )
    with app.app_context():
        from backend.app.extensions import db
        from backend.app.models.user import User

        user = User.query.filter_by(email="carol@example.com").first()
        user.is_active = False
        db.session.commit()

    res = client.post(
        "/api/auth/login",
        json={"email": "carol@example.com", "password": "Secret#123"},
    )
    assert res.status_code == 403
    assert res.get_json()["code"] == 1002


def test_me_without_session_returns_401(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_admin_login_returns_is_admin_true(app, client):
    res = client.post(
        "/api/auth/login",
        json={
            "email": app.config["ADMIN_EMAIL"],
            "password": app.config["ADMIN_PASSWORD"],
        },
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["code"] == 0
    assert body["data"]["is_admin"] is True


def test_email_normalised_to_lowercase(client):
    res = client.post(
        "/api/auth/register",
        json={"name": "Dave", "email": "Dave@Example.COM", "password": "Secret#123"},
    )
    assert res.status_code == 200, res.get_json()

    res = client.post(
        "/api/auth/login",
        json={"email": "dave@example.com", "password": "Secret#123"},
    )
    assert res.status_code == 200


def test_user_disabled_mid_session_blocked_on_me(authed_client, app):
    """If the account is disabled after login, /auth/me must reject the session."""
    with app.app_context():
        from backend.app.extensions import db
        from backend.app.models.user import User

        user = User.query.filter_by(email="alice@test.local").first()
        user.is_active = False
        db.session.commit()

    res = authed_client.get("/api/auth/me")
    assert res.status_code == 403
    assert res.get_json()["code"] == 1002


def test_logout_is_idempotent(client):
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert res.get_json()["data"]["logged_out"] is True
