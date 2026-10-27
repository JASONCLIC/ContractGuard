import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models.game_question import GameQuestion

_QUESTION_FILE = Path(__file__).resolve().parents[2] / "data" / "game_questions.json"


def _load_seed_questions() -> List[Dict[str, Any]]:
    with _QUESTION_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_game_questions_seeded() -> None:
    """Create table (if needed) and seed the default question bank once."""
    GameQuestion.__table__.create(bind=db.engine, checkfirst=True)
    if GameQuestion.query.count() > 0:
        return

    rows = _load_seed_questions()
    for row in rows:
        db.session.add(
            GameQuestion(
                clause_text=row["clause_text"],
                correct_answer=row["correct_answer"],
                explanation=row["explanation"],
                difficulty=row.get("difficulty", "medium"),
            )
        )
    db.session.commit()


def list_game_questions(difficulty: Optional[str] = None, count: int = 10) -> List[GameQuestion]:
    query = GameQuestion.query
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    return query.order_by(GameQuestion.id.asc()).limit(count).all()


def check_game_answer(question_id: int, answer: Optional[str]) -> Dict[str, Any]:
    question = db.session.get(GameQuestion, question_id)
    if not question:
        return {"found": False}
    return {
        "found": True,
        "correct": answer == question.correct_answer,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
    }


def safe_seed_game_questions() -> None:
    """Seed game questions and rollback on DB errors."""
    try:
        ensure_game_questions_seeded()
    except SQLAlchemyError:
        db.session.rollback()
        raise
