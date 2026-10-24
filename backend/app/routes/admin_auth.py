from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import Admin
from app.models.admin import PERMISSIONS, ROLE_DISTRIBUTOR, ROLE_HEAD_ADMIN
from app.services.auth_utils import validate_password, is_valid_email
from app.utils.auth_decorators import (
    create_admin_token, require_admin, require_head_admin, current_admin,
)

admin_auth_bp = Blueprint("admin_auth", __name__, url_prefix="/api/admin/auth")

CREATABLE_ROLES = (ROLE_HEAD_ADMIN, ROLE_DISTRIBUTOR)


def _clean_permissions(raw):
    if not isinstance(raw, list):
        return []
    return [key for key in PERMISSIONS if key in raw]


def _confirm_acting_password(data):
    """Account-management changes need the acting Head Admin's own password."""
    return check_password_hash(current_admin().password_hash, data.get("currentPassword") or "")


def _remaining_active_heads(excluding_id=None):
    query = Admin.query.filter(Admin.role != ROLE_DISTRIBUTOR, Admin.is_active.is_(True))
    if excluding_id is not None:
        query = query.filter(Admin.id != excluding_id)
    return query.count()


@admin_auth_bp.post("/login")
def admin_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    admin = Admin.query.filter_by(email=email).first()
    if not admin or not check_password_hash(admin.password_hash, password):
        return jsonify({"error": "Incorrect email or password"}), 401
    if not admin.is_active:
        return jsonify({"error": "This account has been disabled. Contact a Head Admin."}), 403

    return jsonify({"token": create_admin_token(admin), "admin": admin.to_dict()})


@admin_auth_bp.get("/me")
@require_admin
def admin_me():
    return jsonify({"admin": current_admin().to_dict(), "permissionCatalog": PERMISSIONS})


@admin_auth_bp.get("/accounts")
@require_head_admin
def list_admins():
    admins = Admin.query.order_by(Admin.created_at).all()
    return jsonify({"admins": [a.to_dict() for a in admins], "permissionCatalog": PERMISSIONS})


@admin_auth_bp.post("/accounts")
@require_head_admin
def create_admin():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    role = data.get("role") or ROLE_DISTRIBUTOR
    password = data.get("password") or ""

    if not _confirm_acting_password(data):
        return jsonify({"error": "Your own password is incorrect"}), 403
    if not name:
        return jsonify({"error": "Please enter a name"}), 400
    if not is_valid_email(email):
        return jsonify({"error": "Please enter a valid email address"}), 400
    if role not in CREATABLE_ROLES:
        return jsonify({"error": "Role must be Head Admin or Distributor"}), 400
    if Admin.query.filter_by(email=email).first():
        return jsonify({"error": "An admin with this email already exists"}), 400

    password_errors = validate_password(password)
    if password_errors:
        return jsonify({"error": "Password requirements not met: " + ", ".join(password_errors)}), 400

    admin = Admin(
        name=name, email=email, role=role,
        password_hash=generate_password_hash(password),
        permissions=_clean_permissions(data.get("permissions")) if role == ROLE_DISTRIBUTOR else None,
        is_active=True,
    )
    db.session.add(admin)
    db.session.commit()
    return jsonify({"admin": admin.to_dict()}), 201


@admin_auth_bp.put("/accounts/<int:admin_id>")
@require_head_admin
def update_admin(admin_id):
    data = request.get_json() or {}
    actor = current_admin()
    target = Admin.query.get_or_404(admin_id)

    if not _confirm_acting_password(data):
        return jsonify({"error": "Your own password is incorrect"}), 403

    is_self = target.id == actor.id
    wants_role = data.get("role", target.role)
    wants_active = data.get("isActive", target.is_active)

    if is_self and (wants_role != target.role or wants_active is False or "permissions" in data):
        return jsonify({"error": "You cannot change your own role, status or permissions"}), 400
    if wants_role != target.role and wants_role not in CREATABLE_ROLES:
        return jsonify({"error": "Role must be Head Admin or Distributor"}), 400

    losing_head = target.is_head and (wants_role == ROLE_DISTRIBUTOR or wants_active is False)
    if losing_head and _remaining_active_heads(excluding_id=target.id) < 1:
        return jsonify({"error": "At least one active Head Admin must remain"}), 400

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Please enter a name"}), 400
        target.name = name

    target.role = wants_role
    target.is_active = bool(wants_active)
    if target.is_distributor:
        if "permissions" in data:
            target.permissions = _clean_permissions(data.get("permissions"))
    else:
        target.permissions = None

    new_password = data.get("newPassword")
    if new_password:
        password_errors = validate_password(new_password)
        if password_errors:
            return jsonify({"error": "Password requirements not met: " + ", ".join(password_errors)}), 400
        target.password_hash = generate_password_hash(new_password)

    db.session.commit()
    return jsonify({"admin": target.to_dict()})


@admin_auth_bp.delete("/accounts/<int:admin_id>")
@require_head_admin
def delete_admin(admin_id):
    data = request.get_json(silent=True) or {}
    actor = current_admin()
    target = Admin.query.get_or_404(admin_id)

    if not _confirm_acting_password(data):
        return jsonify({"error": "Your own password is incorrect"}), 403
    if target.id == actor.id:
        return jsonify({"error": "You cannot remove your own account"}), 400
    if target.is_head and _remaining_active_heads(excluding_id=target.id) < 1:
        return jsonify({"error": "At least one active Head Admin must remain"}), 400

    # Their products and services stay in the catalogue; ownership is released.
    from app.models import Product, Service
    Product.query.filter_by(owner_admin_id=target.id).update({"owner_admin_id": None})
    Service.query.filter_by(owner_admin_id=target.id).update({"owner_admin_id": None})
    db.session.delete(target)
    db.session.commit()
    return jsonify({"message": "Account removed"})
