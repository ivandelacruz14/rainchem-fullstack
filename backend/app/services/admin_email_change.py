from datetime import datetime, timedelta

from flask import current_app
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import Admin, AdminEmailChange
from app.services import otp as otp_codes
from app.services.auth_utils import is_valid_email
from app.services.email_service import send_email

CODE_MINUTES = 10
MAX_ATTEMPTS = 5
COOLDOWN_SECONDS = 30


class EmailChangeError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def start(admin, password, new_email):
    """Checks the password, then emails a code to the NEW address to prove it is reachable."""
    if not check_password_hash(admin.password_hash, password or ""):
        raise EmailChangeError("Incorrect password", 403)
    new_email = (new_email or "").strip().lower()
    if not is_valid_email(new_email):
        raise EmailChangeError("Please enter a valid email address")
    if new_email == admin.email:
        raise EmailChangeError("That is already your email")
    if Admin.query.filter(Admin.email == new_email, Admin.id != admin.id).first():
        raise EmailChangeError("Another admin already uses this email")

    recent = (
        AdminEmailChange.query.filter_by(admin_id=admin.id, used=False)
        .order_by(AdminEmailChange.created_at.desc()).first()
    )
    if recent and recent.created_at > datetime.utcnow() - timedelta(seconds=COOLDOWN_SECONDS):
        raise EmailChangeError(f"Please wait {COOLDOWN_SECONDS} seconds before asking for another code", 429)

    AdminEmailChange.query.filter_by(admin_id=admin.id, used=False).update({"used": True})
    code, salt, code_hash = otp_codes.generate()
    row = AdminEmailChange(
        admin_id=admin.id, new_email=new_email, salt=salt, code_hash=code_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=CODE_MINUTES),
    )
    db.session.add(row)
    db.session.commit()

    sent = send_email(
        new_email, "Confirm your new Rainchem admin email",
        f"Your confirmation code is {code}. It expires in {CODE_MINUTES} minutes.\n\n"
        "Enter it to make this address your admin login and the place approval codes are sent. "
        "If you did not ask for this, ignore this email.",
        sensitive=True,
    )
    if not sent and not current_app.debug:
        row.used = True
        db.session.commit()
        raise EmailChangeError(
            "We could not send the code to that address. Check the email settings on the server (Mailjet), then try again.", 503
        )


def confirm(admin, code):
    row = (
        AdminEmailChange.query.filter_by(admin_id=admin.id, used=False)
        .order_by(AdminEmailChange.created_at.desc()).first()
    )
    if row is None:
        raise EmailChangeError("Ask for a new code first")
    if row.expires_at < datetime.utcnow():
        raise EmailChangeError("That code has expired. Ask for a new one.")
    if row.attempts >= MAX_ATTEMPTS:
        raise EmailChangeError("Too many wrong codes. Ask for a new one.", 429)
    if not otp_codes.matches(row.salt, row.code_hash, code):
        row.attempts += 1
        db.session.commit()
        left = MAX_ATTEMPTS - row.attempts
        raise EmailChangeError("Incorrect code. " + (f"{left} tries left." if left else "Ask for a new code."))
    if Admin.query.filter(Admin.email == row.new_email, Admin.id != admin.id).first():
        raise EmailChangeError("Another admin already uses this email", 409)

    old_email = admin.email
    admin.email = row.new_email
    row.used = True
    db.session.commit()

    # A heads-up to the old address, in case this was not the owner.
    try:
        send_email(
            old_email, "Your Rainchem admin email was changed",
            f"The login email of {admin.name} was changed to {admin.email}. "
            "If this was not you, contact the Head Admin right away.",
        )
    except Exception:
        db.session.rollback()
    return admin
