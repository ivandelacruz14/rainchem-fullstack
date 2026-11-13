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

    # One or more frontend origins, comma separated. The first one is used to
    # build links in emails (for example the password reset link).
    FRONTEND_URL = os.getenv(
        "FRONTEND_URL",
        "http://localhost:5173"
    )

    # Largest image that can be sent in the live chat, in megabytes.
    CHAT_UPLOAD_MAX_MB = float(os.getenv("CHAT_UPLOAD_MAX_MB", "3"))

    # Admin security: a six-digit code by email at sign-in, an idle timeout, and an absolute session limit.
    ADMIN_OTP_REQUIRED = os.getenv("ADMIN_OTP_REQUIRED", "true").lower() == "true"
    ADMIN_IDLE_MINUTES = int(os.getenv("ADMIN_IDLE_MINUTES", "10"))
    ADMIN_SESSION_HOURS = int(os.getenv("ADMIN_SESSION_HOURS", "8"))

    # Cloudflare Turnstile secret key. Leave empty in local development to skip the check.
    TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")

    # Email provider: "mailjet" (default) or "resend". Mailjet falls back to Resend when its connection keeps failing.
    EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "mailjet")

    # Bulk and repeat-order rules. Boxes, not pesos. Defaults are placeholders: change them here or in the environment.
    BULK_BASIC_MAX_BOXES = int(os.getenv("BULK_BASIC_MAX_BOXES", "20"))
    BULK_VERIFIED_MAX_BOXES = int(os.getenv("BULK_VERIFIED_MAX_BOXES", "200"))
    BULK_REVIEW_BOXES = int(os.getenv("BULK_REVIEW_BOXES", "100"))
    DUPLICATE_ORDER_MINUTES = int(os.getenv("DUPLICATE_ORDER_MINUTES", "5"))

    # Hours between UTC and the shop's local time, used to group sales by day.
    STORE_UTC_OFFSET_HOURS = int(os.getenv("STORE_UTC_OFFSET_HOURS", "8"))

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
    TURNSTILE_SECRET_KEY = ""
    ADMIN_OTP_REQUIRED = False  # tests sign in with the password only; the OTP tests switch it on
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    FRONTEND_URL = "http://localhost:5173"
    JWT_SECRET_KEY = "test-secret"
    SECRET_KEY = "test-secret"