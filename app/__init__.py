import os
import uuid

import click
from flask import Flask, redirect, url_for
from flask_login import current_user

from app.admin import admin_bp
from app.auth import auth_bp
from app.catalogue import catalogue_bp
from app.config import config_by_name, get_config_name
from app.errors import register_error_handlers
from app.extensions import csrf, db, limiter, login_manager, talisman
from app.models import User


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    config_name = (config_name or get_config_name()).lower()
    app.config.from_object(config_by_name.get(config_name, config_by_name["dev"]))

    if config_name not in ("test", "testing"):
        if os.getenv("DATABASE_URL"):
            app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
        if os.getenv("SECRET_KEY"):
            app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    if config_name in ("prod", "production"):
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    if app.config.get("TALISMAN_ENABLED", True):
        talisman.init_app(
            app,
            content_security_policy=app.config.get("TALISMAN_CONTENT_SECURITY_POLICY"),
            force_https=app.config.get("TALISMAN_FORCE_HTTPS", False),
            session_cookie_secure=app.config.get("SESSION_COOKIE_SECURE", True),
        )

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "error"

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, uuid.UUID(user_id))

    register_error_handlers(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(catalogue_bp)
    app.register_blueprint(admin_bp)
    _register_cli(app)
    _register_routes(app)

    return app


def _register_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("catalogue.list_datasets"))
        return redirect(url_for("auth.login"))

    @app.route("/health/db")
    def health_db():
        from sqlalchemy import text

        if not app.config.get("SQLALCHEMY_DATABASE_URI"):
            return {"database": "error", "message": "DATABASE_URL not set"}, 500
        try:
            db.session.execute(text("SELECT 1"))
            return {"database": "connected"}
        except Exception as exc:
            return {"database": "error", "message": str(exc)}, 500


def _register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db():
        import app.models  # noqa: F401

        db.create_all()
        click.echo("Tables created.")

    @app.cli.command("seed")
    def seed_cmd():
        from scripts.seed import run_seed

        run_seed()
