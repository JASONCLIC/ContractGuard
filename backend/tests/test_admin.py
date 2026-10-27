"""
P0/P1 system tests for /api/admin (admin only).

Covers:
- require_admin gating (login + admin email check)
- Overview / users / contracts (search, detail) read endpoints
- User status update + delete (with self-protection rules)
- Game-question CRUD with audit log
- Template-clause CRUD with audit log
- Audit log listing
"""

from __future__ import annotations

import pytest


# ── require_admin gating ──────────────────────────────────────────────────────


def test_admin_endpoints_require_login(app):
    fresh = app.test_client()
    res = fresh.get("/api/admin/overview")
    assert res.status_code == 401
    assert res.get_json()["code"] == 2002


def test_admin_endpoints_reject_non_admin(authed_client):
    """Authed regular user is rejected with 2003."""
    res = authed_client.get("/api/admin/overview")
    assert res.status_code == 403
    assert res.get_json()["code"] == 2003


# ── Overview ──────────────────────────────────────────────────────────────────


def test_admin_overview_returns_aggregates(admin_authed_client):
    res = admin_authed_client.get("/api/admin/overview")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert {"stats", "contract_status", "risk_level_dist", "latest_contracts", "latest_users"} <= set(data)
    assert {"users", "contracts", "risks", "jobs"} <= set(data["stats"])
    assert isinstance(data["stats"]["users"], int)


# ── Users ─────────────────────────────────────────────────────────────────────


def test_admin_users_list(admin_authed_client, client):
    """Register a regular user via the public client, then list as admin."""
    client.post(
        "/api/auth/register",
        json={"name": "RegU", "email": "regu@test.local", "password": "Strong#1234"},
    )

    res = admin_authed_client.get("/api/admin/users?limit=50")
    assert res.status_code == 200
    body = res.get_json()["data"]
    emails = [u["email"] for u in body["items"]]
    assert "regu@test.local" in emails
    assert "admin@test.local" in emails
    # is_admin flag must be set
    admin_row = next(u for u in body["items"] if u["email"] == "admin@test.local")
    assert admin_row["is_admin"] is True


def test_admin_users_keyword_filter(admin_authed_client, client):
    client.post(
        "/api/auth/register",
        json={"name": "Searchable", "email": "needle@test.local", "password": "Strong#1234"},
    )
    res = admin_authed_client.get("/api/admin/users?keyword=needle")
    items = res.get_json()["data"]["items"]
    assert all("needle" in u["email"] or "needle" in u["name"].lower() for u in items)


def test_admin_disable_then_enable_user(admin_authed_client, client, app):
    client.post(
        "/api/auth/register",
        json={"name": "Toggle", "email": "toggle@test.local", "password": "Strong#1234"},
    )
    with app.app_context():
        from backend.app.models.user import User

        uid = User.query.filter_by(email="toggle@test.local").first().id

    res = admin_authed_client.patch(
        f"/api/admin/users/{uid}/status", json={"enabled": False}
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["is_active"] is False

    res = admin_authed_client.patch(
        f"/api/admin/users/{uid}/status", json={"enabled": True}
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["is_active"] is True


def test_admin_cannot_disable_self(admin_authed_client, app):
    with app.app_context():
        from backend.app.models.user import User

        admin_id = User.query.filter_by(email="admin@test.local").first().id

    res = admin_authed_client.patch(
        f"/api/admin/users/{admin_id}/status", json={"enabled": False}
    )
    assert res.status_code == 400
    assert res.get_json()["code"] == 1001


def test_admin_cannot_disable_admin_account(admin_authed_client, app):
    """Even for an arbitrary admin row, the API must refuse to disable admins."""
    with app.app_context():
        from backend.app.models.user import User

        admin_id = User.query.filter_by(email="admin@test.local").first().id

    res = admin_authed_client.patch(
        f"/api/admin/users/{admin_id}/status", json={"enabled": False}
    )
    assert res.status_code == 400
    assert res.get_json()["code"] == 1001


def test_admin_status_payload_must_be_bool(admin_authed_client, client, app):
    client.post(
        "/api/auth/register",
        json={"name": "Bobby", "email": "bobby@test.local", "password": "Strong#1234"},
    )
    with app.app_context():
        from backend.app.models.user import User

        uid = User.query.filter_by(email="bobby@test.local").first().id

    res = admin_authed_client.patch(
        f"/api/admin/users/{uid}/status", json={"enabled": "yes"}
    )
    assert res.status_code == 400
    assert res.get_json()["code"] == 1001


def test_admin_status_unknown_user_returns_404(admin_authed_client):
    res = admin_authed_client.patch(
        "/api/admin/users/999999/status", json={"enabled": True}
    )
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001


def test_admin_delete_regular_user_writes_audit_log(admin_authed_client, client, app):
    client.post(
        "/api/auth/register",
        json={"name": "Delme", "email": "delme@test.local", "password": "Strong#1234"},
    )
    with app.app_context():
        from backend.app.models.user import User

        uid = User.query.filter_by(email="delme@test.local").first().id

    res = admin_authed_client.delete(f"/api/admin/users/{uid}")
    assert res.status_code == 200
    assert res.get_json()["data"]["deleted"] is True

    with app.app_context():
        from backend.app.models.admin_audit_log import AdminAuditLog
        from backend.app.models.user import User

        assert User.query.get(uid) is None
        log = AdminAuditLog.query.filter_by(action="user.delete").order_by(
            AdminAuditLog.id.desc()
        ).first()
        assert log is not None
        assert "delme@test.local" in log.summary


def test_admin_cannot_delete_self(admin_authed_client, app):
    with app.app_context():
        from backend.app.models.user import User

        admin_id = User.query.filter_by(email="admin@test.local").first().id

    res = admin_authed_client.delete(f"/api/admin/users/{admin_id}")
    assert res.status_code == 400
    assert res.get_json()["code"] == 1001


def test_admin_delete_unknown_user_returns_404(admin_authed_client):
    res = admin_authed_client.delete("/api/admin/users/999999")
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001


# ── Contracts search & detail ─────────────────────────────────────────────────


def test_admin_contracts_search_returns_done(admin_authed_client, done_contract):
    res = admin_authed_client.get("/api/admin/contracts?limit=50")
    assert res.status_code == 200
    body = res.get_json()["data"]
    assert body["total"] >= 1
    assert any(item["id"] == done_contract for item in body["items"])


def test_admin_contracts_search_keyword(admin_authed_client, done_contract):
    res = admin_authed_client.get("/api/admin/contracts?keyword=labor")
    assert res.status_code == 200
    items = res.get_json()["data"]["items"]
    assert any(item["id"] == done_contract for item in items)


def test_admin_contract_detail(admin_authed_client, done_contract):
    res = admin_authed_client.get(f"/api/admin/contracts/{done_contract}/detail")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["contract"]["id"] == done_contract
    assert len(data["clauses"]) == 3
    assert len(data["risks"]) == 2
    assert len(data["missing_items"]) == 1
    assert "owner" in data and data["owner"]["email"] == "alice@test.local"


def test_admin_contract_detail_unknown_returns_404(admin_authed_client):
    res = admin_authed_client.get("/api/admin/contracts/999999/detail")
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001


# ── Game questions CRUD ───────────────────────────────────────────────────────


def test_admin_game_question_crud(admin_authed_client, app):
    payload = {
        "clause_text": "A clause that allows unilateral salary cuts.",
        "correct_answer": "risk",
        "explanation": "Unilateral cuts are unlawful.",
        "difficulty": "easy",
    }
    res = admin_authed_client.post("/api/admin/game-questions", json=payload)
    assert res.status_code == 200
    qid = res.get_json()["data"]["id"]

    res = admin_authed_client.put(
        f"/api/admin/game-questions/{qid}",
        json={"difficulty": "hard"},
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["updated"] is True

    res = admin_authed_client.get("/api/admin/game-questions")
    items = res.get_json()["data"]
    row = next(it for it in items if it["id"] == qid)
    assert row["difficulty"] == "hard"

    res = admin_authed_client.delete(f"/api/admin/game-questions/{qid}")
    assert res.status_code == 200
    assert res.get_json()["data"]["deleted"] is True

    # audit log must record the create+update+delete actions
    with app.app_context():
        from backend.app.models.admin_audit_log import AdminAuditLog

        actions = {row.action for row in AdminAuditLog.query.all()}
        assert {"game_question.create", "game_question.update", "game_question.delete"} <= actions


@pytest.mark.parametrize(
    "payload",
    [
        {"clause_text": "", "correct_answer": "risk", "explanation": "x"},
        {"clause_text": "x", "correct_answer": "maybe", "explanation": "x"},
        {"clause_text": "x", "correct_answer": "risk", "explanation": "x", "difficulty": "expert"},
    ],
)
def test_admin_game_question_validation_rejects(admin_authed_client, payload):
    res = admin_authed_client.post("/api/admin/game-questions", json=payload)
    assert res.status_code == 400
    assert res.get_json()["code"] == 1001


def test_admin_game_question_update_unknown_returns_404(admin_authed_client):
    res = admin_authed_client.put(
        "/api/admin/game-questions/999999",
        json={"clause_text": "x", "correct_answer": "safe", "explanation": "x"},
    )
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001


def test_admin_game_question_delete_unknown_returns_404(admin_authed_client):
    res = admin_authed_client.delete("/api/admin/game-questions/999999")
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001


# ── Template clauses CRUD ─────────────────────────────────────────────────────


def test_admin_template_crud(admin_authed_client, app):
    payload = {
        "category_key": "salary",
        "category_label": "Salary Clauses",
        "title": "New Salary Template",
        "content": "Salary shall be paid monthly on the 5th.",
        "tip": "Always specify the exact day.",
        "sort_order": 99,
    }
    res = admin_authed_client.post("/api/admin/template-clauses", json=payload)
    assert res.status_code == 200, res.get_json()
    tid = res.get_json()["data"]["id"]

    res = admin_authed_client.put(
        f"/api/admin/template-clauses/{tid}",
        json={"title": "Updated Salary Template"},
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["updated"] is True

    res = admin_authed_client.get("/api/admin/template-clauses")
    items = res.get_json()["data"]
    row = next(it for it in items if it["id"] == tid)
    assert row["title"] == "Updated Salary Template"

    res = admin_authed_client.delete(f"/api/admin/template-clauses/{tid}")
    assert res.status_code == 200
    assert res.get_json()["data"]["deleted"] is True

    with app.app_context():
        from backend.app.models.admin_audit_log import AdminAuditLog

        actions = {row.action for row in AdminAuditLog.query.all()}
        assert {"template_clause.create", "template_clause.update", "template_clause.delete"} <= actions


def test_admin_template_create_invalid_payload(admin_authed_client):
    res = admin_authed_client.post(
        "/api/admin/template-clauses",
        json={"category_key": "salary", "title": "x"},  # missing required fields
    )
    assert res.status_code == 400
    assert res.get_json()["code"] == 1001


def test_admin_template_update_unknown_returns_404(admin_authed_client):
    res = admin_authed_client.put(
        "/api/admin/template-clauses/999999",
        json={"title": "x"},
    )
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001


def test_admin_template_delete_unknown_returns_404(admin_authed_client):
    res = admin_authed_client.delete("/api/admin/template-clauses/999999")
    assert res.status_code == 404
    assert res.get_json()["code"] == 2001


# ── Audit log listing ─────────────────────────────────────────────────────────


def test_admin_audit_logs_list(admin_authed_client, client, app):
    # Trigger one auditable action: disable a user.
    client.post(
        "/api/auth/register",
        json={"name": "AL", "email": "audit-target@test.local", "password": "Strong#1234"},
    )
    with app.app_context():
        from backend.app.models.user import User

        uid = User.query.filter_by(email="audit-target@test.local").first().id
    admin_authed_client.patch(
        f"/api/admin/users/{uid}/status", json={"enabled": False}
    )

    res = admin_authed_client.get("/api/admin/audit-logs?limit=20")
    assert res.status_code == 200
    body = res.get_json()["data"]
    assert body["total"] >= 1
    actions = [item["action"] for item in body["items"]]
    assert "user.status.update" in actions


def test_admin_audit_logs_keyword_filter(admin_authed_client, client, app):
    client.post(
        "/api/auth/register",
        json={"name": "Zoe", "email": "z-target@test.local", "password": "Strong#1234"},
    )
    with app.app_context():
        from backend.app.models.user import User

        uid = User.query.filter_by(email="z-target@test.local").first().id
    admin_authed_client.delete(f"/api/admin/users/{uid}")

    res = admin_authed_client.get("/api/admin/audit-logs?keyword=z-target")
    items = res.get_json()["data"]["items"]
    assert any("z-target@test.local" in it["summary"] for it in items)
