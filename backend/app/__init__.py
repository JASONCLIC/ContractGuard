from flask import Flask
from flask import redirect

from .config import Config
from .extensions import cors, db, migrate
from .routes import register_blueprints
from .middleware.error_handler import register_error_handlers
from .services.admin_service import ensure_admin_user
from .services.schema_sync_service import ensure_runtime_schema
from .services.template_library_service import ensure_template_library_seeded


def create_app(config_object=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)

    cors.init_app(
        app,
        supports_credentials=True,
        origins=[
            "http://localhost:5173",
            "http://csi420-01-vm8.ucd.ie",
        ],
        # 允许前端 JS 读取 Content-Disposition 响应头（下载文件名所需）
        expose_headers=["Content-Disposition"],
    )
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        ensure_runtime_schema()
        # Bootstrap admin account for backend management console.
        ensure_admin_user()
        ensure_template_library_seeded()

    register_blueprints(app)
    register_error_handlers(app)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/")
    def root():
        # Root keeps a friendly entrypoint and points users to the frontend portal.
        return redirect("http://localhost:5173", code=302)

    return app
