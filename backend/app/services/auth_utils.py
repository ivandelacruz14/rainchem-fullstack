import re
import secrets


def validate_password(password):
    """Returns a list of unmet requirements; empty list means it's valid."""
    errors = []
    if not password or len(password) < 8:
        errors.append("At least 8 characters")
    if password and len(password) > 24:
        errors.append("No more than 24 characters")
    if not re.search(r"[A-Z]", password or ""):
        errors.append("At least one uppercase letter")
    if not re.search(r"[a-z]", password or ""):
        errors.append("At least one lowercase letter")
    if not re.search(r"[0-9]", password or ""):
        errors.append("At least one number")
    if not re.search(r"[^A-Za-z0-9]", password or ""):
        errors.append("At least one special symbol")
    return errors


def is_valid_email(email):
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email or ""))


def is_valid_phone(phone):
    return bool(re.match(r"^[0-9+\-\s()]{7,20}$", phone or ""))


def generate_verification_code():
    return str(secrets.randbelow(900000) + 100000)


def generate_reset_token():
    return secrets.token_urlsafe(32)
