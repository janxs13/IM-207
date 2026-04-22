import os
from datetime import timedelta


def _jwt_access_hours():
    raw = os.environ.get("JWT_ACCESS_HOURS", "8")
    try:
        h = int(raw)
    except ValueError:
        return 8
    return max(1, min(h, 168))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "super_secret_bus_key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///bus_ticketing.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt_secret_key_2026")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=_jwt_access_hours())

    # Explicit storage avoids Flask-Limiter in-memory UserWarning on startup.
    # For production with multiple workers, set e.g. RATELIMIT_STORAGE_URI=redis://localhost:6379/0
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # Mail config (Flask-Mail). If credentials are missing, run in console mode.
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = str(os.environ.get("MAIL_USE_TLS", "true")).strip().lower() in ("1", "true", "yes", "on")
    MAIL_USE_SSL = str(os.environ.get("MAIL_USE_SSL", "false")).strip().lower() in ("1", "true", "yes", "on")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or MAIL_USERNAME
    MAIL_SUPPRESS_SEND = not bool(MAIL_USERNAME and MAIL_PASSWORD)
