from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import User, Order
from app.services import audit
from app.utils.auth_decorators import current_admin, require_permission

admin_users_bp = Blueprint("admin_users", __name__, url_prefix="/api/admin/users")


@admin_users_bp.get("/summary")
@require_permission("customers")
def users_summary():
    """Aggregate counts only, safe to show without revealing anyone's
    identity. The admin dashboard uses this until an admin explicitly asks
    to see the customer list."""
    total = User.query.count()
    verified = User.query.filter_by(verified=True).count()
    return jsonify({"total": total, "verified": verified})


@admin_users_bp.get("")
@require_permission("customers")
def list_users():
    search = (request.args.get("search") or "").lower()
    query = User.query
    if search:
        query = query.filter(
            db.or_(User.name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
        )
    users = query.order_by(User.created_at.desc()).all()

    result = []
    for user in users:
        data = user.to_dict()
        data["orderCount"] = Order.query.filter_by(user_id=user.id).count()
        result.append(data)
    return jsonify({"users": result})


@admin_users_bp.get("/<int:user_id>")
@require_permission("customers")
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    data = user.to_dict()
    data["orders"] = [o.to_dict() for o in orders]
    return jsonify({"user": data})


@admin_users_bp.put("/<int:user_id>/business")
@require_permission("customers")
def set_business_verified(user_id):
    """Marks a business account as verified, which raises its bulk limit. Personal accounts cannot be verified."""
    user = User.query.get_or_404(user_id)
    if user.account_type != "business":
        return jsonify({"error": "Only business accounts can be verified"}), 400
    data = request.get_json() or {}
    verified = bool(data.get("businessVerified"))
    before = bool(user.business_verified)
    user.business_verified = verified
    audit.record("business_verification", "user", user.id, {"verified": before}, {"verified": verified},
                 str(data.get("reason") or "")[:500] or None, current_admin())
    db.session.commit()
    return jsonify({"user": user.to_dict()})


@admin_users_bp.delete("/<int:user_id>")
@require_permission("customers")
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User account deactivated"})
