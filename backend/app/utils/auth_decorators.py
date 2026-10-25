from functools import wraps
from flask import jsonify, g
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, verify_jwt_in_request

from app.extensions import db


def create_user_token(user):
    return create_access_token(identity=f"user:{user.id}", additional_claims={"role": "user"})


def create_admin_token(admin):
    return create_access_token(identity=f"admin:{admin.id}", additional_claims={"role": "admin"})


def current_user_id():
    """Extracts the numeric user id from a verified user token."""
    identity = get_jwt_identity()
    if identity and identity.startswith("user:"):
        return int(identity.split(":")[1])
    return None


def current_admin_id():
    identity = get_jwt_identity()
    if identity and identity.startswith("admin:"):
        return int(identity.split(":")[1])
    return None


def current_admin():
    """The signed-in admin, loaded fresh from the database so a changed role,
    changed permissions or a disabled account takes effect on the next request."""
    return getattr(g, "admin", None)


def require_user(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "user":
            return jsonify({"error": "A customer account is required for this action"}), 403
        return fn(*args, **kwargs)
    return wrapper


def _load_admin_or_error():
    from app.models import Admin
    verify_jwt_in_request()
    if get_jwt().get("role") != "admin":
        return None, (jsonify({"error": "Admin access is required for this action"}), 403)
    admin_id = current_admin_id()
    admin = db.session.get(Admin, admin_id) if admin_id else None
    if admin is None or not admin.is_active:
        return None, (jsonify({"error": "This admin account is disabled or no longer exists"}), 401)
    g.admin = admin
    return admin, None


def require_admin(fn):
    """Any active admin account, whatever its role."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        admin, error = _load_admin_or_error()
        if error:
            return error
        return fn(*args, **kwargs)
    return wrapper


def require_head_admin(fn):
    """Only Head Admins. Distributors are refused here no matter what the UI shows."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        admin, error = _load_admin_or_error()
        if error:
            return error
        if not admin.is_head:
            return jsonify({"error": "Only a Head Admin can do this"}), 403
        return fn(*args, **kwargs)
    return wrapper


def require_permission(*keys):
    """Head Admins always pass. Other admins need at least one of the listed permissions."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            admin, error = _load_admin_or_error()
            if error:
                return error
            if not admin.is_head and not any(admin.has_permission(k) for k in keys):
                return jsonify({"error": "You do not have permission to do this"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def optional_user_id():
    """For endpoints that work for both guests and logged-in users (like
    chat), returns the user id if a valid token is present, else None."""
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity and identity.startswith("user:"):
            return int(identity.split(":")[1])
    except Exception:
        pass
    return None
