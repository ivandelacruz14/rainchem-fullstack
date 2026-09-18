from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import Admin
from app.services.auth_utils import validate_password
from app.utils.auth_decorators import create_admin_token, require_admin, current_admin_id

admin_auth_bp = Blueprint("admin_auth", __name__, url_prefix="/api/admin/auth")


@admin_auth_bp.post("/login")
def admin_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    admin = Admin.query.filter_by(email=email).first()
    if not admin or not check_password_hash(admin.password_hash, password):
        return jsonify({"error": "Incorrect email or password"}), 401

    token = create_admin_token(admin)
    return jsonify({"token": token, "admin": admin.to_dict()})


@admin_auth_bp.get("/me")
@require_admin
def admin_me():
    admin = Admin.query.get(current_admin_id())
    return jsonify({"admin": admin.to_dict()})


@admin_auth_bp.get("/accounts")
@require_admin
def list_admins():
    admins = Admin.query.order_by(Admin.created_at).all()
    return jsonify({"admins": [a.to_dict() for a in admins]})


@admin_auth_bp.post("/accounts")
@require_admin
def create_admin():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    role = data.get("role") or "Admin"
    password = data.get("password") or ""

    if Admin.query.filter_by(email=email).first():
        return jsonify({"error": "An admin with this email already exists"}), 400

    password_errors = validate_password(password)
    if password_errors:
        return jsonify({"error": "Password requirements not met: " + ", ".join(password_errors)}), 400

    admin = Admin(name=name, email=email, role=role, password_hash=generate_password_hash(password))
    db.session.add(admin)
    db.session.commit()
    return jsonify({"admin": admin.to_dict()}), 201


@admin_auth_bp.delete("/accounts/<int:admin_id>")
@require_admin
def delete_admin(admin_id):
    if Admin.query.count() <= 1:
        return jsonify({"error": "At least one admin account must remain"}), 400
    admin = Admin.query.get_or_404(admin_id)
    db.session.delete(admin)
    db.session.commit()
    return jsonify({"message": "Admin account removed"})
