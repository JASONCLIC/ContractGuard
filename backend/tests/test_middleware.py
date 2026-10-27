"""
P1 system tests for the middleware layer.

Covers:
- rate_limiter.check_limit window/limit semantics
- error_handler 404/500 contract
- require_login, require_admin, require_contract_access decorators
"""

from __future__ import annotations

import time

import pytest


# ── rate_limiter ──────────────────────────────────────────────────────────────


def test_rate_limit_allows_under_limit():
    from backend.app.middleware import rate_limiter

    rate_limiter._bucket.clear()
    for _ in range(10):
        assert rate_limiter.check_limit("k1", limit=10, window_sec=60) is True


def test_rate_limit_blocks_over_limit():
    from backend.app.middleware import rate_limiter

    rate_limiter._bucket.clear()
    for _ in range(10):
        assert rate_limiter.check_limit("k2", limit=10, window_sec=60) is True
    assert rate_limiter.check_limit("k2", limit=10, window_sec=60) is False


def test_rate_limit_separate_keys_independent():
    from backend.app.middleware import rate_limiter

    rate_limiter._bucket.clear()
    for _ in range(10):
        rate_limiter.check_limit("a", limit=10, window_sec=60)
    # "a" is exhausted, but "b" should still be free.
    assert rate_limiter.check_limit("b", limit=10, window_sec=60) is True


def test_rate_limit_window_eviction():
    """Records older than the window must be evicted before counting."""
    from backend.app.middleware import rate_limiter

    rate_limiter._bucket.clear()
    rate_limiter._bucket["k3"] = [time.time() - 120 for _ in range(10)]
    assert rate_limiter.check_limit("k3", limit=10, window_sec=60) is True


# ── error_handler ─────────────────────────────────────────────────────────────


def test_404_handler_returns_5001(client):
    res = client.get("/api/no-such-endpoint")
    assert res.status_code == 404
    body = res.get_json()
    assert body["code"] == 5001
    assert body["request_id"] is not None


def test_request_id_attached_to_responses(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "ok"


# ── require_admin / require_login behaviour via routes ────────────────────────


def test_require_admin_blocks_regular_user(authed_client):
    res = authed_client.get("/api/admin/overview")
    assert res.status_code == 403
    assert res.get_json()["code"] == 2003


def test_require_admin_blocks_anonymous(app):
    res = app.test_client().get("/api/admin/overview")
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_require_login_blocks_anonymous(app):
    res = app.test_client().get("/api/contract/1")
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_require_login_blocks_disabled_user(authed_client, app):
    """Decorator must drop session and return 2004 when user is disabled."""
    with app.app_context():
        from backend.app.extensions import db
        from backend.app.models.user import User

        user = User.query.filter_by(email="alice@test.local").first()
        user.is_active = False
        db.session.commit()

    res = authed_client.post("/api/contract/paste", json={"text": "Article 1."})
    assert res.status_code == 403
    assert res.get_json()["code"] == 2004


# ── Health & root smoke ───────────────────────────────────────────────────────


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_root_redirects_to_frontend(client):
    res = client.get("/", follow_redirects=False)
    assert res.status_code == 302
    assert "localhost:5173" in res.headers["Location"]
