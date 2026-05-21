"""
LIFE OS AI — Flask application factory.

We follow the standard application-factory pattern so the app can be
constructed against different configurations (development, production,
testing) and so tests can spin up isolated instances.
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, render_template, session
from werkzeug.middleware.proxy_fix import ProxyFix

from config import get_config


def create_app(config_class=None) -> Flask:
    """Build and return a configured Flask application."""
    app = Flask(
        __name__,
        instance_relative_config=False,
        template_folder="templates",
        static_folder="static",
    )

    # ------------------------------------------------------------------ config
    app.config.from_object(config_class or get_config())

    # Honour X-Forwarded-* headers when running behind a reverse proxy
    # (Render, Railway, Heroku, nginx, etc) — required for HTTPS cookies
    # and url_for(..., _external=True) to produce https:// URLs.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Ensure runtime directories exist.
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    # Initialise the SQLite schema. Idempotent — uses CREATE TABLE IF NOT EXISTS
    # under the hood, so it's safe to call on every app start.
    from app.core.database import DatabaseManager
    DatabaseManager(app.config["DATABASE_PATH"]).init_schema()

    # ----------------------------------------------------------- blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.chat import chat_bp
    from app.routes.tasks import tasks_bp
    from app.routes.study import study_bp
    from app.routes.mood import mood_bp
    from app.routes.productivity import productivity_bp
    from app.routes.files import files_bp
    from app.routes.voice import voice_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/app")
    app.register_blueprint(chat_bp, url_prefix="/app/chat")
    app.register_blueprint(tasks_bp, url_prefix="/app/tasks")
    app.register_blueprint(study_bp, url_prefix="/app/study")
    app.register_blueprint(mood_bp, url_prefix="/app/mood")
    app.register_blueprint(productivity_bp, url_prefix="/app/productivity")
    app.register_blueprint(files_bp, url_prefix="/app/files")
    app.register_blueprint(voice_bp, url_prefix="/app/voice")
    app.register_blueprint(settings_bp, url_prefix="/app/settings")

    # ------------------------------------------------------------- context
    @app.context_processor
    def inject_globals():
        """Variables available in every template."""
        return {
            "APP_NAME": "LIFE OS AI",
            "APP_TAGLINE": "Your AI Operating System for a Better Life",
            "current_user_id": session.get("user_id"),
            "current_user_name": session.get("user_name"),
        }

    # ----------------------------------------------------------- errors
    @app.errorhandler(404)
    def not_found(_):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_):
        return render_template("errors/500.html"), 500

    return app
