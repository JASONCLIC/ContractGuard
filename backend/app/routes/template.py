from flask import Blueprint
from sqlalchemy.exc import SQLAlchemyError

from ..services.template_library_service import (
    list_template_categories,
    list_template_items_by_category,
    safe_seed_template_library,
)
from ..utils.response import success

bp = Blueprint("template", __name__)


@bp.get("/categories")
def categories():
    try:
        safe_seed_template_library()
    except SQLAlchemyError:
        return success([])
    return success(list_template_categories())


@bp.get("/<category>")
def by_category(category):
    try:
        safe_seed_template_library()
    except SQLAlchemyError:
        return success([])
    return success(list_template_items_by_category(category))
