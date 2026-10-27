from ..extensions import db


class GameQuestion(db.Model):
    __tablename__ = "game_questions"

    id = db.Column(db.Integer, primary_key=True)
    clause_text = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(16), nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(16), nullable=False, default="medium")
