from functools import wraps
from flask import g, jsonify
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


def _load_admin():
    from app.extensions import db
    from app.models import Admin
    admin_id = current_admin_id()
    return db.session.get(Admin, admin_id) if admin_id else None


def require_admin(fn):
    """Any signed-in admin or distributor. Prefer require_head_admin or
    require_permission for anything that is not safe for every account."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if get_jwt().get("role") != "admin":
            return jsonify({"error": "Admin access is required for this action"}), 403
        admin = _load_admin()
        if admin is None or not admin.is_active:
            return jsonify({"error": "This admin account is not active"}), 403
        g.current_admin = admin
        return fn(*args, **kwargs)
    return wrapper


def require_head_admin(fn):
    @wraps(fn)
    @require_admin
    def wrapper(*args, **kwargs):
        if not g.current_admin.is_head:
            return jsonify({"error": "Only a Head Admin can do this"}), 403
        return fn(*args, **kwargs)
    return wrapper


def require_permission(*keys):
    """Head admins always pass. Distributors need at least one of the keys,
    as granted to them by a Head Admin."""
    def decorator(fn):
        @wraps(fn)
        @require_admin
        def wrapper(*args, **kwargs):
            admin = g.current_admin
            if not any(admin.has_permission(key) for key in keys):
                return jsonify({"error": "You do not have permission to do this"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def current_admin():
    return getattr(g, "current_admin", None)


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
