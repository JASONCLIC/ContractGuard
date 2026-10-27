"""
P0/P1 system tests for /api/share.

Covers:
- POST   /api/share/create        owner creates share link (auth, ownership)
- GET    /api/share/<token>       public access with optional password,
                                  expiry, max-access-count, IP rate limit
- POST   /api/share/<token>/verify  password check
- DELETE /api/share/<token>       revoke (owner only)
"""

from __future__ import annotations

from datetime import datetime, timedelta


# ── POST /create ──────────────────────────────────────────────────────────────


def test_create_share_requires_login(app):
    res = app.test_client().post("/api/share/create", json={"contract_id": 1})
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_create_share_unknown_contract_returns_404(authed_client):
    res = authed_client.post("/api/share/create", json={"contract_id": 999999})
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001


def test_create_share_other_user_returns_403(authed_client, app, done_contract):
    other = app.test_client()
    other.post(
        "/api/auth/register",
        json={"name": "Eve", "email": "eve.share@test.local", "password": "Strong#1234"},
    )
    other.post(
        "/api/auth/login",
        json={"email": "eve.share@test.local", "password": "Strong#1234"},
    )
    res = other.post("/api/share/create", json={"contract_id": done_contract})
    assert res.status_code == 403
    assert res.get_json()["code"] == 2002


def test_create_share_no_password(authed_client, done_contract):
    res = authed_client.post(
        "/api/share/create",
        json={"contract_id": done_contract, "expires_hours": 1},
    )
    assert res.status_code == 200, res.get_json()
    data = res.get_json()["data"]
    assert "token" in data and len(data["token"]) > 16
    assert data["share_url"].endswith(data["token"])
    assert "expires_at" in data


def test_create_share_with_password(authed_client, done_contract):
    res = authed_client.post(
        "/api/share/create",
        json={"contract_id": done_contract, "password": "secret", "expires_hours": 24},
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["token"]


# ── GET /<token> ──────────────────────────────────────────────────────────────


def _create_share(authed_client, contract_id, **kwargs):
    payload = {"contract_id": contract_id, **kwargs}
    res = authed_client.post("/api/share/create", json=payload)
    assert res.status_code == 200, res.get_json()
    return res.get_json()["data"]["token"]


def test_share_invalid_token_returns_4001(app):
    res = app.test_client().get("/api/share/no-such-token")
    assert res.status_code == 404
    assert res.get_json()["code"] == 4001


def test_share_no_password_public_access(authed_client, app, done_contract):
    token = _create_share(authed_client, done_contract)
    res = app.test_client().get(f"/api/share/{token}")
    assert res.status_code == 200, res.get_json()
    data = res.get_json()["data"]
    assert data["contract_id"] == done_contract
    assert "[EMPLOYER]" in data["text"]
    assert data["key_info"]["party_a"] == "Acme Corporation"


def test_share_with_password_required(authed_client, app, done_contract):
    token = _create_share(authed_client, done_contract, password="secret")

    res = app.test_client().get(f"/api/share/{token}")
    assert res.status_code == 401
    assert res.get_json()["code"] == 4002

    res = app.test_client().get(f"/api/share/{token}?password=wrong")
    assert res.status_code == 401
    assert res.get_json()["code"] == 4002

    res = app.test_client().get(f"/api/share/{token}?password=secret")
    assert res.status_code == 200


def test_share_expired_returns_410(authed_client, app, done_contract):
    token = _create_share(authed_client, done_contract)
    with app.app_context():
        from backend.app.extensions import db
        from backend.app.models.share_link import ShareLink

        link = ShareLink.query.filter_by(token=token).first()
        link.expires_at = datetime.utcnow() - timedelta(hours=1)
        db.session.commit()

    res = app.test_client().get(f"/api/share/{token}")
    assert res.status_code == 410
    assert res.get_json()["code"] == 4001


def test_share_max_access_count_enforced(authed_client, app, done_contract):
    token = _create_share(authed_client, done_contract, max_access_count=1)

    res = app.test_client().get(f"/api/share/{token}")
    assert res.status_code == 200

    res = app.test_client().get(f"/api/share/{token}")
    assert res.status_code == 429
    assert res.get_json()["code"] == 4003


def test_share_rate_limit_per_token_ip(authed_client, app, done_contract):
    """P0-SHA-02: same IP+token > 10 requests within 60s → 429/4003."""
    token = _create_share(authed_client, done_contract, max_access_count=999)
    fresh = app.test_client()
    last = None
    for _ in range(11):
        last = fresh.get(f"/api/share/{token}")
    assert last.status_code == 429
    assert last.get_json()["code"] == 4003


# ── POST /<token>/verify ──────────────────────────────────────────────────────


def test_share_verify_unknown_token_4001(app):
    res = app.test_client().post("/api/share/missing/verify", json={"password": "x"})
    assert res.status_code == 404
    assert res.get_json()["code"] == 4001


def test_share_verify_correct_password(authed_client, app, done_contract):
    token = _create_share(authed_client, done_contract, password="correct")
    res = app.test_client().post(
        f"/api/share/{token}/verify", json={"password": "correct"}
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["verified"] is True


def test_share_verify_wrong_password(authed_client, app, done_contract):
    token = _create_share(authed_client, done_contract, password="correct")
    res = app.test_client().post(
        f"/api/share/{token}/verify", json={"password": "incorrect"}
    )
    assert res.status_code == 401
    assert res.get_json()["code"] == 4002


# ── DELETE /<token> ───────────────────────────────────────────────────────────


def test_share_revoke_unknown_token_4001(authed_client):
    res = authed_client.delete("/api/share/missing-token")
    assert res.status_code == 404
    assert res.get_json()["code"] == 4001


def test_share_revoke_succeeds(authed_client, app, done_contract):
    token = _create_share(authed_client, done_contract)
    res = authed_client.delete(f"/api/share/{token}")
    assert res.status_code == 200
    assert res.get_json()["data"]["revoked"] is True

    res = app.test_client().get(f"/api/share/{token}")
    assert res.status_code == 404
    assert res.get_json()["code"] == 4001


def test_share_revoke_other_user_returns_403(authed_client, app, done_contract):
    token = _create_share(authed_client, done_contract)

    other = app.test_client()
    other.post(
        "/api/auth/register",
        json={"name": "Eve", "email": "eve.revoke@test.local", "password": "Strong#1234"},
    )
    other.post(
        "/api/auth/login",
        json={"email": "eve.revoke@test.local", "password": "Strong#1234"},
    )
    res = other.delete(f"/api/share/{token}")
    assert res.status_code == 403
    assert res.get_json()["code"] == 2002
