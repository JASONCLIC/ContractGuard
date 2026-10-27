import json
from pathlib import Path
from typing import List

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models.template_clause import TemplateClause

_TEMPLATE_FILE = Path(__file__).resolve().parents[2] / "data" / "template_library.json"


def _load_seed_templates():
    with _TEMPLATE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_template_library_seeded() -> None:
    TemplateClause.__table__.create(bind=db.engine, checkfirst=True)
    if TemplateClause.query.count() > 0:
        return

    rows = _load_seed_templates()
    for row in rows:
        db.session.add(
            TemplateClause(
                category_key=row["category_key"],
                category_label=row["category_label"],
                title=row["title"],
                content=row["content"],
                tip=row.get("tip", ""),
                sort_order=int(row.get("sort_order", 1)),
                is_active=True,
            )
        )
    db.session.commit()


def safe_seed_template_library() -> None:
    try:
        ensure_template_library_seeded()
    except SQLAlchemyError:
        db.session.rollback()
        raise


def list_template_categories():
    rows = (
        TemplateClause.query.with_entities(
            TemplateClause.category_key,
            func.min(TemplateClause.category_label).label("label"),
        )
        .filter(TemplateClause.is_active.is_(True))
        .group_by(TemplateClause.category_key)
        .order_by(TemplateClause.category_key.asc())
        .all()
    )
    return [{"key": r.category_key, "label": r.label} for r in rows]


def list_template_items_by_category(category_key):
    rows = (
        TemplateClause.query.filter_by(category_key=category_key, is_active=True)
        .order_by(TemplateClause.sort_order.asc(), TemplateClause.id.asc())
        .all()
    )
    return [
        {"id": r.id, "title": r.title, "content": r.content, "tip": r.tip or ""}
        for r in rows
    ]


def list_all_template_clauses(limit=500):
    rows = (
        TemplateClause.query.order_by(
            TemplateClause.category_key.asc(),
            TemplateClause.sort_order.asc(),
            TemplateClause.id.asc(),
        )
        .limit(limit)
        .all()
    )
    return rows


def get_template_clause(template_id):
    return db.session.get(TemplateClause, template_id)


def create_template_clause(payload):
    row = TemplateClause(
        category_key=(payload.get("category_key") or "").strip(),
        category_label=(payload.get("category_label") or "").strip(),
        title=(payload.get("title") or "").strip(),
        content=(payload.get("content") or "").strip(),
        tip=(payload.get("tip") or "").strip(),
        sort_order=int(payload.get("sort_order", 1)),
        is_active=bool(payload.get("is_active", True)),
    )
    db.session.add(row)
    db.session.commit()
    return row


def update_template_clause(row, payload):
    if "category_key" in payload:
        row.category_key = (payload.get("category_key") or "").strip()
    if "category_label" in payload:
        row.category_label = (payload.get("category_label") or "").strip()
    if "title" in payload:
        row.title = (payload.get("title") or "").strip()
    if "content" in payload:
        row.content = (payload.get("content") or "").strip()
    if "tip" in payload:
        row.tip = (payload.get("tip") or "").strip()
    if "sort_order" in payload:
        row.sort_order = int(payload.get("sort_order", 1))
    if "is_active" in payload:
        row.is_active = bool(payload.get("is_active"))
    db.session.commit()
    return row


def delete_template_clause(row):
    db.session.delete(row)
    db.session.commit()

