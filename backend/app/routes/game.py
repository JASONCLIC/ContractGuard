from flask import Blueprint, request
from sqlalchemy.exc import SQLAlchemyError

from ..services.game_question_service import (
    check_game_answer,
    list_game_questions,
    safe_seed_game_questions,
)
from ..utils.response import fail, success

bp = Blueprint("game", __name__)


@bp.get("/questions")
def questions():
    try:
        safe_seed_game_questions()
    except SQLAlchemyError:
        return fail(code=50001, message="failed to initialize game question bank", status=500)

    difficulty = request.args.get("difficulty")
    count_raw = request.args.get("count", 10)
    try:
        count = max(1, min(int(count_raw), 50))
    except (TypeError, ValueError):
        count = 10

    rows = list_game_questions(difficulty=difficulty, count=count)
    return success(
        [
            {
                "id": row.id,
                "clause_text": row.clause_text,
                "difficulty": row.difficulty,
            }
            for row in rows
        ]
    )


@bp.post("/answer")
def answer():
    try:
        safe_seed_game_questions()
    except SQLAlchemyError:
        return fail(code=50001, message="failed to initialize game question bank", status=500)

    payload = request.get_json(silent=True) or {}
    try:
        question_id = int(payload.get("question_id", 0))
    except (TypeError, ValueError):
        return success({"correct": False, "message": "invalid question id"})

    selected = payload.get("answer")

    result = check_game_answer(question_id=question_id, answer=selected)
    if not result["found"]:
        return success({"correct": False, "message": "question not found"})

    return success(
        {
            "correct": result["correct"],
            "correct_answer": result["correct_answer"],
            "explanation": result["explanation"],
        }
    )
