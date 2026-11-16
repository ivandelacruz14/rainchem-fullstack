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


PH_MOBILE = re.compile(r"^09(0[5-9]|1\d|2\d|3\d|4\d|5\d|6\d|7\d|8\d|9\d)\d{7}$")
PH_INTERNATIONAL = re.compile(r"^\+639(0[5-9]|1\d|2\d|3\d|4\d|5\d|6\d|7\d|8\d|9\d)\d{7}$")


def _looks_fabricated(local):
    """Refuses placeholder-style numbers: three identical digits in a row (555, 000), or only a few different digits."""
    tail = local[2:]
    if re.search(r"(\d)\1\1", tail):
        return True
    return len(set(tail)) <= 3


def normalize_ph_mobile(raw):
    """09XXXXXXXXX stays as it is. +639XXXXXXXXX becomes 09XXXXXXXXX. Anything else, or a fabricated-looking
    number, returns None."""
    raw = raw or ""
    if PH_INTERNATIONAL.match(raw):
        raw = "0" + raw[3:]
    if not PH_MOBILE.match(raw) or _looks_fabricated(raw):
        return None
    return raw


NAME_PART = re.compile(r"^[^\W\d_](?:[^\W\d_]|[ .'\-])*$")


def clean_name_parts(data):
    """Returns (first, middle, last, problems). Middle name is optional. A single 'name' is split at the first space."""
    if "firstName" not in data and data.get("name"):
        words = " ".join(str(data.get("name")).split()).split(" ", 1)
        data = {"firstName": words[0], "lastName": words[1] if len(words) > 1 else ""}
    problems = []

    def part(key, label, required):
        value = " ".join(str(data.get(key) or "").split())
        if not value:
            if required:
                problems.append(f"Enter your {label}")
            return None
        if len(value) > 60:
            problems.append(f"Your {label} is too long (60 characters at most)")
        elif not NAME_PART.match(value):
            problems.append(f"Your {label} can only contain letters, spaces, hyphens, apostrophes, and periods")
        return value

    first = part("firstName", "first name", True)
    middle = part("middleName", "middle name", False)
    last = part("lastName", "last name", True)
    return first, middle, last, problems


def is_valid_phone(phone):
    return normalize_ph_mobile(phone) is not None


def generate_verification_code():
    return str(secrets.randbelow(900000) + 100000)


def generate_reset_token():
    return secrets.token_urlsafe(32)
