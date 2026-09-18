from functools import wraps
from flask import jsonify
from flask_jwt_extended import create_access_token, get_jwt, verify_jwt_in_request


def create_user_token(user):
    return create_access_token(identity=f"user:{user.id}", additional_claims={"role": "user"})


def create_admin_token(admin):
    return create_access_token(identity=f"admin:{admin.id}", additional_claims={"role": "admin"})


def current_user_id():
    """Extracts the numeric user id from a verified user token."""
    from flask_jwt_extended import get_jwt_identity
    identity = get_jwt_identity()
    if identity and identity.startswith("user:"):
        return int(identity.split(":")[1])
    return None


def current_admin_id():
    from flask_jwt_extended import get_jwt_identity
    identity = get_jwt_identity()
    if identity and identity.startswith("admin:"):
        return int(identity.split(":")[1])
    return None


def require_user(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "user":
            return jsonify({"error": "A customer account is required for this action"}), 403
        return fn(*args, **kwargs)
    return wrapper


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access is required for this action"}), 403
        return fn(*args, **kwargs)
    return wrapper


def optional_user_id():
    """For endpoints that work for both guests and logged-in users (like
    chat), returns the user id if a valid token is present, else None."""
    from flask_jwt_extended import get_jwt_identity
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity and identity.startswith("user:"):
            return int(identity.split(":")[1])
    except Exception:
        pass
    return None
