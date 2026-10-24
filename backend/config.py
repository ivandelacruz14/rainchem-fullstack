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
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
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

    FRONTEND_URLS = [
        url.strip().rstrip("/")
        for url in os.getenv("FRONTEND_URL", "http://localhost:5173").split(",")
        if url.strip()
    ]
    FRONTEND_URL = FRONTEND_URLS[0]

    SALES_UTC_OFFSET_HOURS = int(os.getenv("SALES_UTC_OFFSET_HOURS", "8"))

    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

    SMTP_FROM = os.getenv(
        "SMTP_FROM",
        "onboarding@resend.dev"
    )

    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

    PAYMONGO_SECRET_KEY = os.getenv("PAYMONGO_SECRET_KEY", "")
    PAYMONGO_WEBHOOK_SECRET = os.getenv("PAYMONGO_WEBHOOK_SECRET", "")
    PAYMENT_DEMO_MODE = os.getenv("PAYMENT_DEMO_MODE", "false").lower() == "true"


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    JWT_SECRET_KEY = "test-secret"
    SECRET_KEY = "test-secret"