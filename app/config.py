import os

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

load_dotenv()


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
