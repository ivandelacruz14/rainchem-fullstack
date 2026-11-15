"""One-time codes: a random 6-digit code, stored only as a salted hash."""
import hashlib
import hmac
import secrets


def hash_code(salt, code):
    return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()


def generate():
    """Returns (code, salt, code_hash). Only the salt and hash are ever stored."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_hex(8)
    return code, salt, hash_code(salt, code)


def matches(salt, stored_hash, code):
    return hmac.compare_digest(stored_hash, hash_code(salt, str(code or "").strip()))
