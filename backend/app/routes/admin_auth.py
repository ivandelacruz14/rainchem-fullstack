from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import Admin, Product, Service
from app.services.auth_utils import is_valid_email, validate_password
from app.services.permissions import (
    ASSIGNABLE_ROLES, DISTRIBUTOR, PERMISSIONS, clean_permissions, default_permissions, is_head_role, role_info,
)
from app.utils.auth_decorators import create_admin_token, current_admin, require_admin, require_head_admin

admin_auth_bp = Blueprint("admin_auth", __name__, url_prefix="/api/admin/auth")


def _error(message, status=400):
    return jsonify({"error": message}), status


def _actor_confirmed(data):
    """Sensitive account actions need the acting Head Admin's own password again."""
    return check_password_hash(current_admin().password_hash, str(data.get("confirmPassword") or ""))


def _permissions_for(role, requested):
    """Stored permissions for a role: none for a Head Admin (they have everything), the
    role's starting set when nothing was chosen, otherwise only what that role may hold."""
    if is_head_role(role):
        return None
    if requested is None:
        return default_permissions(role)
    return clean_permissions(requested, role)


def _active_heads():
    return [a for a in Admin.query.filter_by(is_active=True).all() if a.is_head]


@admin_auth_bp.post("/login")
def admin_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    admin = Admin.query.filter_by(email=email).first()
    if not admin or not check_password_hash(admin.password_hash, password):
        return _error("Incorrect email or password", 401)
    if not admin.is_active:
        return _error("This account has been disabled. Contact the Head Admin.", 403)

    return jsonify({"token": create_admin_token(admin), "admin": admin.to_dict()})


@admin_auth_bp.get("/me")
@require_admin
def admin_me():
    return jsonify({"admin": current_admin().to_dict()})


@admin_auth_bp.put("/me/password")
@require_admin
def change_own_password():
    admin = current_admin()
    data = request.get_json() or {}
    if not check_password_hash(admin.password_hash, str(data.get("currentPassword") or "")):
        return _error("Current password is incorrect")
    problems = validate_password(data.get("newPassword") or "")
    if problems:
        return _error("Password requirements not met: " + ", ".join(problems))
    admin.password_hash = generate_password_hash(data["newPassword"])
    db.session.commit()
    return jsonify({"message": "Password updated"})


@admin_auth_bp.get("/accounts")
@require_head_admin
def list_admins():
    admins = Admin.query.order_by(Admin.created_at).all()
    return jsonify({
        "admins": [a.to_dict() for a in admins],
        "roles": ASSIGNABLE_ROLES,
        "roleInfo": role_info(),
        "permissions": [{"key": k, "label": v} for k, v in PERMISSIONS.items()],
    })


@admin_auth_bp.post("/accounts")
@require_head_admin
def create_admin():
    data = request.get_json() or {}
    if not _actor_confirmed(data):
        return _error("Enter your own password to confirm this change", 403)

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    role = data.get("role") or DISTRIBUTOR
    password = data.get("password") or ""

    if not name:
        return _error("Please enter a name")
    if not is_valid_email(email):
        return _error("Please enter a valid email address")
    if role not in ASSIGNABLE_ROLES:
        return _error("Choose a valid role")
    if Admin.query.filter_by(email=email).first():
        return _error("An admin with this email already exists")
    problems = validate_password(password)
    if problems:
        return _error("Password requirements not met: " + ", ".join(problems))

    admin = Admin(
        name=name, email=email, role=role, is_active=True,
        password_hash=generate_password_hash(password),
        permissions=_permissions_for(role, data.get("permissions")),
    )
    db.session.add(admin)
    db.session.commit()
    return jsonify({"admin": admin.to_dict()}), 201


@admin_auth_bp.put("/accounts/<int:admin_id>")
@require_head_admin
def update_admin(admin_id):
    actor = current_admin()
    data = request.get_json() or {}
    if not _actor_confirmed(data):
        return _error("Enter your own password to confirm this change", 403)

    admin = Admin.query.get_or_404(admin_id)
    if admin.id == actor.id:
        return _error("You cannot change your own role, permissions or status")

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return _error("Please enter a name")
        admin.name = name
    role_changed = False
    if "role" in data and data["role"] != admin.role:
        if data["role"] not in ASSIGNABLE_ROLES:
            return _error("Choose a valid role")
        admin.role = data["role"]
        role_changed = True
    if "isActive" in data:
        admin.is_active = bool(data["isActive"])
    if "permissions" in data:
        admin.permissions = _permissions_for(admin.role, data["permissions"])
    elif role_changed:
        admin.permissions = _permissions_for(admin.role, None)

    if not _active_heads():
        db.session.rollback()
        return _error("At least one active Head Admin must remain")
    db.session.commit()
    return jsonify({"admin": admin.to_dict()})


@admin_auth_bp.post("/accounts/<int:admin_id>/password")
@require_head_admin
def reset_admin_password(admin_id):
    data = request.get_json() or {}
    if not _actor_confirmed(data):
        return _error("Enter your own password to confirm this change", 403)
    admin = Admin.query.get_or_404(admin_id)
    problems = validate_password(data.get("newPassword") or "")
    if problems:
        return _error("Password requirements not met: " + ", ".join(problems))
    admin.password_hash = generate_password_hash(data["newPassword"])
    db.session.commit()
    return jsonify({"message": "Password reset. Share the new password with them securely."})


@admin_auth_bp.delete("/accounts/<int:admin_id>")
@require_head_admin
def delete_admin(admin_id):
    actor = current_admin()
    data = request.get_json(silent=True) or {}
    if not _actor_confirmed(data):
        return _error("Enter your own password to confirm this change", 403)

    admin = Admin.query.get_or_404(admin_id)
    if admin.id == actor.id:
        return _error("You cannot remove your own account")
    if admin.is_head and len(_active_heads()) <= 1 and admin.is_active:
        return _error("At least one active Head Admin must remain")

    # What they owned goes back to the Head Admins.
    Product.query.filter_by(owner_admin_id=admin.id).update({"owner_admin_id": None})
    Service.query.filter_by(owner_admin_id=admin.id).update({"owner_admin_id": None})
    db.session.delete(admin)
    db.session.commit()
    return jsonify({"message": "Admin account removed"})
