from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import User, Order
from app.utils.auth_decorators import require_admin

admin_users_bp = Blueprint("admin_users", __name__, url_prefix="/api/admin/users")


@admin_users_bp.get("/summary")
@require_admin
def users_summary():
    """Aggregate counts only, safe to show without revealing anyone's
    identity. The admin dashboard uses this until an admin explicitly asks
    to see the customer list."""
    total = User.query.count()
    verified = User.query.filter_by(verified=True).count()
    return jsonify({"total": total, "verified": verified})


@admin_users_bp.get("")
@require_admin
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
@require_admin
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    data = user.to_dict()
    data["orders"] = [o.to_dict() for o in orders]
    return jsonify({"user": data})


@admin_users_bp.delete("/<int:user_id>")
@require_admin
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User account deactivated"})
