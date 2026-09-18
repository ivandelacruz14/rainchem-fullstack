import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "rainchem")
    DB_USER = os.getenv("DB_USER", "rainchem_app")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "rainchem_pass")
    DB_SSL_CA = os.getenv("DB_SSL_CA", "")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        "?charset=utf8mb4"
    )

    if DB_SSL_CA:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {
                "ssl": {
                    "ca": DB_SSL_CA
                }
            }
        }

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 24 * 7

    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    SMTP_FROM = os.getenv(
        "SMTP_FROM",
        "onboarding@resend.dev"
    )

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret"
    SECRET_KEY = "test-secret"