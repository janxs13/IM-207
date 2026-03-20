import os

class Config:
    SECRET_KEY                     = os.environ.get("SECRET_KEY", "super_secret_bus_key")
    SQLALCHEMY_DATABASE_URI        = os.environ.get("DATABASE_URL", "sqlite:///bus_ticketing.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY                 = os.environ.get("JWT_SECRET_KEY", "jwt_secret_key_2026")