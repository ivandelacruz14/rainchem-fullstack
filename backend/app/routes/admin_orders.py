from datetime import datetime
from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Order, OrderStatusHistory
from app.models.order import ORDER_STATUSES
from app.services.receipt_service import create_receipt_for_order
from app.services.email_service import send_email
from app.utils.auth_decorators import require_admin

admin_orders_bp = Blueprint("admin_orders", __name__, url_prefix="/api/admin/orders")


@admin_orders_bp.get("")
@require_admin
def list_orders():
    status = request.args.get("status")
    query = Order.query
    if status and status != "All":
        query = query.filter_by(status=status)
    orders = query.order_by(Order.created_at.desc()).all()
    return jsonify({"orders": [o.to_dict() for o in orders]})


@admin_orders_bp.get("/<int:order_id>")
@require_admin
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify({"order": order.to_dict()})


@admin_orders_bp.post("/<int:order_id>/confirm")
@require_admin
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status != "pending_confirmation":
        return jsonify({"error": "Only pending orders can be confirmed"}), 400

    order.status = "confirmed"
    order.confirmed_at = datetime.utcnow()
    db.session.add(OrderStatusHistory(order_id=order.id, status="confirmed"))
    db.session.commit()

    receipt = create_receipt_for_order(order)

    send_email(
        order.customer_email, f"Order confirmed - {order.order_number}",
        f"Hi {order.customer_name},\n\nGood news, your order {order.order_number} "
        f"has been confirmed and is being prepared. Your receipt number is "
        f"{receipt.receipt_number}. You can view and print it anytime from My Orders.",
        user_id=order.user_id,
    )

    return jsonify({"order": order.to_dict(), "receipt": receipt.to_dict()})


@admin_orders_bp.post("/<int:order_id>/status")
@require_admin
def update_status(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json() or {}
    new_status = data.get("status")

    if new_status not in ORDER_STATUSES:
        return jsonify({"error": "Invalid status"}), 400
    if order.status == "cancelled":
        return jsonify({"error": "A cancelled order cannot be updated"}), 400

    order.status = new_status
    if new_status == "cancelled":
        order.cancelled_at = datetime.utcnow()

    tracking_number = data.get("trackingNumber")
    if tracking_number:
        order.tracking_number = tracking_number

    db.session.add(OrderStatusHistory(order_id=order.id, status=new_status))
    db.session.commit()
    return jsonify({"order": order.to_dict()})


@admin_orders_bp.get("/<int:order_id>/receipt")
@require_admin
def get_receipt(order_id):
    order = Order.query.get_or_404(order_id)
    if not order.receipt:
        return jsonify({"error": "No receipt has been generated for this order yet"}), 404
    return jsonify({"order": order.to_dict(), "receipt": order.receipt.to_dict()})
