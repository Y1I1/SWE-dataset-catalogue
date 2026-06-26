import os

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

load_dotenv()

_INSECURE_KEYS = {"dev-only-change-me", "change-me", "secret", ""}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "")
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    TALISMAN_ENABLED = True
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_LOGIN = "10 per minute"


class DevConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    TALISMAN_FORCE_HTTPS = False
    TALISMAN_CONTENT_SECURITY_POLICY = None


class TestConfig(Config):
    TESTING = True
    DEBUG = True
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    WTF_CSRF_ENABLED = True
    TALISMAN_ENABLED = False
    RATELIMIT_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ProdConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    TALISMAN_FORCE_HTTPS = True
    TALISMAN_CONTENT_SECURITY_POLICY = {
        "default-src": "'self'",
        "style-src": ["'self'"],
        "script-src": ["'self'"],
        "frame-ancestors": "'none'",
    }


config_by_name = {
    "dev": DevConfig,
    "development": DevConfig,
    "test": TestConfig,
    "testing": TestConfig,
    "prod": ProdConfig,
    "production": ProdConfig,
}


def get_config_name() -> str:
    return os.getenv("FLASK_CONFIG", "dev").lower()


def validate_prod_config(app) -> None:
    """Raise RuntimeError immediately if production config is insecure."""
    secret = app.config.get("SECRET_KEY", "")
    db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if secret in _INSECURE_KEYS:
        raise RuntimeError(
            "Production start-up aborted: SECRET_KEY is missing or uses a known-insecure placeholder. "
            "Set a strong random value in the Render environment."
        )
    if not db_url:
        raise RuntimeError(
            "Production start-up aborted: DATABASE_URL is not set. "
            "Configure it in the Render environment."
        )
