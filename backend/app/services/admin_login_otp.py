"""The second step of an admin sign-in: a six-digit code emailed to the admin's own address.

The first step (email and password) returns an opaque challenge token. The token and the code are
both stored only as hashes. The code expires after 10 minutes, allows 5 wrong tries, and works once."""
import hashlib
import secrets
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models import AdminLoginChallenge
from app.services import otp as otp_codes
from app.services.email_service import send_email

CODE_MINUTES = 10
MAX_ATTEMPTS = 5
COOLDOWN_SECONDS = 30


class AdminLoginError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def _hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _mask(email):
    name, _, domain = email.partition("@")
    return f"{name[:2]}{'*' * max(1, len(name) - 2)}@{domain}"


def start(admin):
    """Emails a new code to the admin. Returns (challenge_token, masked_email)."""
    recent = AdminLoginChallenge.query.filter_by(admin_id=admin.id).order_by(AdminLoginChallenge.created_at.desc()).first()
    if recent and recent.created_at > datetime.utcnow() - timedelta(seconds=COOLDOWN_SECONDS):
        raise AdminLoginError(f"Please wait {COOLDOWN_SECONDS} seconds before requesting a new code.", 429)

    AdminLoginChallenge.query.filter_by(admin_id=admin.id, used=False).update({"used": True})
    token = secrets.token_urlsafe(32)
    code, salt, code_hash = otp_codes.generate()
    row = AdminLoginChallenge(
        admin_id=admin.id, challenge_hash=_hash(token), salt=salt, code_hash=code_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=CODE_MINUTES),
    )
    db.session.add(row)
    db.session.commit()

    sent = send_email(
        admin.email, "Rainchem admin login code",
        f"Your login code is {code}. It expires in {CODE_MINUTES} minutes.\n\n"
        "If you did not try to sign in, change your password right away and tell the Head Admin.",
        sensitive=True,
    )
    if not sent and not current_app.debug:
        # A failed send must not start the 30-second wait: the attempt is removed, not kept as a sent code.
        db.session.delete(row)
        db.session.commit()
        raise AdminLoginError("The code could not be sent to your email. Please try again later.", 503)
    return token, _mask(admin.email)


def verify(token, code):
    """Checks the code. Returns the admin id when it is right."""
    if not token or len(str(token)) > 200:
        raise AdminLoginError("This sign-in has expired. Please sign in again.", 400)
    row = AdminLoginChallenge.query.filter_by(challenge_hash=_hash(str(token)), used=False).first()
    if row is None:
        raise AdminLoginError("This sign-in is invalid or has already been used. Please sign in again.", 400)
    if row.expires_at < datetime.utcnow():
        row.used = True
        db.session.commit()
        raise AdminLoginError("The code has expired. Sign in again to get a new one.", 400)
    if row.attempts >= MAX_ATTEMPTS:
        row.used = True
        db.session.commit()
        raise AdminLoginError("Too many wrong codes. Please sign in again.", 429)
    if not otp_codes.matches(row.salt, row.code_hash, code):
        row.attempts += 1
        db.session.commit()
        left = MAX_ATTEMPTS - row.attempts
        raise AdminLoginError("Wrong code. " + (f"{left} tries left." if left else "Sign in again to get a new one."), 400)
    row.used = True
    db.session.commit()
    return row.admin_id
