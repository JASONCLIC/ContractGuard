from .analysis import bp as analysis_bp
from .admin import bp as admin_bp
from .auth import bp as auth_bp
from .contract import bp as contract_bp
from .export import bp as export_bp
from .game import bp as game_bp
from .jobs import bp as jobs_bp
from .share import bp as share_bp
from .template import bp as template_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(contract_bp, url_prefix="/api/contract")
    app.register_blueprint(jobs_bp, url_prefix="/api/jobs")
    app.register_blueprint(analysis_bp, url_prefix="/api/analysis")
    app.register_blueprint(export_bp, url_prefix="/api/export")
    app.register_blueprint(share_bp, url_prefix="/api/share")
    app.register_blueprint(template_bp, url_prefix="/api/template")
    app.register_blueprint(game_bp, url_prefix="/api/game")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
