"""
P1 system tests for /api/game (public).

Question bank auto-seeds from backend/data/game_questions.json on first request.
"""

from __future__ import annotations


def test_questions_default_count(client):
    res = client.get("/api/game/questions")
    assert res.status_code == 200
    items = res.get_json()["data"]
    assert isinstance(items, list)
    assert 1 <= len(items) <= 10


def test_questions_with_count_clamped(client):
    res = client.get("/api/game/questions?count=200")
    assert res.status_code == 200
    items = res.get_json()["data"]
    # The route clamps count to <= 50.
    assert len(items) <= 50


def test_questions_invalid_count_falls_back_to_default(client):
    res = client.get("/api/game/questions?count=abc")
    assert res.status_code == 200
    assert isinstance(res.get_json()["data"], list)


def test_answer_correct(client, app):
    """Pick the first seeded question and submit its known correct answer."""
    res = client.get("/api/game/questions?count=1")
    qid = res.get_json()["data"][0]["id"]

    with app.app_context():
        from backend.app.models.game_question import GameQuestion

        correct_answer = GameQuestion.query.get(qid).correct_answer

    res = client.post(
        "/api/game/answer", json={"question_id": qid, "answer": correct_answer}
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["correct"] is True
    assert body["data"]["correct_answer"] == correct_answer
    assert body["data"]["explanation"]


def test_answer_wrong(client, app):
    res = client.get("/api/game/questions?count=1")
    qid = res.get_json()["data"][0]["id"]

    with app.app_context():
        from backend.app.models.game_question import GameQuestion

        correct = GameQuestion.query.get(qid).correct_answer
    wrong = "safe" if correct == "risk" else "risk"

    res = client.post("/api/game/answer", json={"question_id": qid, "answer": wrong})
    assert res.status_code == 200
    assert res.get_json()["data"]["correct"] is False


def test_answer_unknown_question(client):
    res = client.post(
        "/api/game/answer", json={"question_id": 999999, "answer": "safe"}
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["correct"] is False
    assert "not found" in res.get_json()["data"]["message"].lower()


def test_answer_invalid_question_id(client):
    res = client.post("/api/game/answer", json={"question_id": "abc", "answer": "safe"})
    assert res.status_code == 200
    assert res.get_json()["data"]["correct"] is False
