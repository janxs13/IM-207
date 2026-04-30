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

    # ── SMS (Semaphore — Philippine SMS gateway) ─────────────────
    # Register at https://semaphore.co — ₱0.50/SMS
    SEMAPHORE_API_KEY = os.environ.get("SEMAPHORE_API_KEY", "")

    # ── PayPal ───────────────────────────────────────────────────
    PAYPAL_CLIENT_ID     = os.environ.get("PAYPAL_CLIENT_ID", "")
    PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
    PAYPAL_MODE          = os.environ.get("PAYPAL_MODE", "sandbox")  # sandbox or live

    # ── OTP / 2FA ────────────────────────────────────────────────
    OTP_EXPIRY_MINUTES = int(os.environ.get("OTP_EXPIRY_MINUTES", "5"))

    # ── PayMongo ─────────────────────────────────────────────────
    # Get your keys at: https://dashboard.paymongo.com/developers
    # Set PAYMONGO_SECRET_KEY in your .env or environment variables.
    # Use sk_test_XXXX for development, sk_live_XXXX for production.
    PAYMONGO_SECRET_KEY    = os.environ.get("PAYMONGO_SECRET_KEY", "")
    PAYMONGO_PUBLIC_KEY    = os.environ.get("PAYMONGO_PUBLIC_KEY", "")
    PAYMONGO_WEBHOOK_SECRET = os.environ.get("PAYMONGO_WEBHOOK_SECRET", "")
    # Base URL for payment redirect callbacks (e.g. https://yourdomain.com)
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")
