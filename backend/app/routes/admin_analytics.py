from flask import Blueprint, jsonify
from sqlalchemy import func

from app.extensions import db
from app.models import Order, OrderItem
from app.utils.auth_decorators import require_admin

admin_analytics_bp = Blueprint("admin_analytics", __name__, url_prefix="/api/admin/analytics")


@admin_analytics_bp.get("/sales")
@require_admin
def sales_summary():
    rows = (
        db.session.query(
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("units"),
            func.sum(OrderItem.quantity * OrderItem.unit_price * (1 - OrderItem.discount_rate)).label("revenue"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.status != "cancelled")
        .group_by(OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity * OrderItem.unit_price * (1 - OrderItem.discount_rate)).desc())
        .all()
    )

    data = [
        {"name": r.product_name, "units": int(r.units), "revenue": round(float(r.revenue), 2)}
        for r in rows
    ]
    top = data[0] if data else None
    bottom = data[-1] if data else None

    return jsonify({"products": data, "topSeller": top, "lowestSeller": bottom})