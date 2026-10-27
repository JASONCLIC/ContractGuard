import uuid

from flask import g

from ..utils.response import fail


def register_error_handlers(app):
    @app.before_request
    def attach_request_id():
        g.request_id = f"req_{uuid.uuid4().hex[:12]}"

    @app.errorhandler(404)
    def not_found(_):
        return fail(5001, "not found", status=404)

    @app.errorhandler(500)
    def internal_error(_):
        return fail(5001, "internal server error", status=500)
