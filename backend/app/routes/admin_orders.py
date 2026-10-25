from datetime import datetime
from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Order, OrderStatusHistory, Product
from app.models.order import ORDER_STATUSES
from app.services.receipt_service import create_receipt_for_order
from app.services.email_service import send_email
from app.services.payment_flow import mark_paid, reset_payment
from app.models import OrderItem
from app.services.admin_scope import scope_product_ids
from app.utils.auth_decorators import current_admin, require_head_admin, require_permission

admin_orders_bp = Blueprint("admin_orders", __name__, url_prefix="/api/admin/orders")


@admin_orders_bp.get("")
@require_permission("orders")
def list_orders():
    admin = current_admin()
    status = request.args.get("status")
    query = Order.query
    ids = scope_product_ids(admin)
    if ids is not None:
        query = query.filter(Order.id.in_(
            db.session.query(OrderItem.order_id).filter(OrderItem.product_id.in_(ids or [-1]))
        ))
    if status == "returns":
        query = query.filter(Order.return_status != "none")
    elif status == "verifying":
        query = query.filter(Order.payment_status == "verifying", Order.status != "cancelled")
    elif status and status != "All":
        query = query.filter_by(status=status)
    orders = query.order_by(Order.created_at.desc()).all()
    if ids is not None:
        return jsonify({"scope": "limited", "orders": [o.to_scoped_dict(set(ids)) for o in orders]})
    return jsonify({"scope": "full", "orders": [o.to_dict() for o in orders]})


@admin_orders_bp.get("/<int:order_id>")
@require_head_admin
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify({"order": order.to_dict()})


@admin_orders_bp.post("/<int:order_id>/confirm")
@require_head_admin
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status != "pending_confirmation":
        return jsonify({"error": "Only pending orders can be confirmed"}), 400
    if order.is_online_payment and order.payment_status != "paid":
        return jsonify({"error": f"This order is still waiting for the customer's {order.payment_method} payment"}), 400

    # Status change and receipt are saved together, so an order can never end up
    # "confirmed" without a receipt to print.
    order.status = "confirmed"
    order.confirmed_at = datetime.utcnow()
    db.session.add(OrderStatusHistory(order_id=order.id, status="confirmed"))
    receipt = create_receipt_for_order(order, commit=False)
    db.session.commit()

    send_email(
        order.customer_email, f"Order confirmed - {order.order_number}",
        f"Hi {order.customer_name},\n\nGood news, your order {order.order_number} "
        f"has been confirmed and is being prepared. Your receipt number is "
        f"{receipt.receipt_number}. You can view and print it anytime from My Orders.",
        user_id=order.user_id,
    )

    return jsonify({"order": order.to_dict(), "receipt": receipt.to_dict()})


@admin_orders_bp.post("/<int:order_id>/status")
@require_head_admin
def update_status(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json() or {}
    new_status = data.get("status")

    if new_status not in ORDER_STATUSES:
        return jsonify({"error": "Invalid status"}), 400
    if order.status == "cancelled":
        return jsonify({"error": "A cancelled order cannot be updated"}), 400

    if order.status == "pending_confirmation" and new_status not in ("pending_confirmation", "cancelled"):
        # Confirming is what creates the receipt, so it cannot be skipped.
        return jsonify({"error": "Confirm the order first"}), 400
    if new_status in ("shipped", "delivered") and order.is_online_payment and order.payment_status != "paid":
        return jsonify({"error": "This order has not been paid yet"}), 400

    order.status = new_status
    if new_status == "cancelled":
        order.cancelled_at = datetime.utcnow()
        if order.payment_status == "paid":
            order.payment_status = "refund_pending"
        for item in order.items:  # the goods are not leaving, put them back on the shelf
            if item.product_id:
                product = db.session.get(Product, item.product_id)
                if product:
                    product.stock += item.quantity
    if new_status == "delivered" and not order.is_online_payment and order.payment_status == "unpaid":
        order.payment_status = "paid"
        order.paid_at = datetime.utcnow()

    tracking_number = data.get("trackingNumber")
    if tracking_number:
        order.tracking_number = tracking_number

    db.session.add(OrderStatusHistory(order_id=order.id, status=new_status))
    db.session.commit()
    return jsonify({"order": order.to_dict()})


@admin_orders_bp.get("/<int:order_id>/receipt")
@require_head_admin
def get_receipt(order_id):
    order = Order.query.get_or_404(order_id)
    if not order.receipt and order.status in ("confirmed", "processing", "shipped", "delivered"):
        create_receipt_for_order(order)  # confirmed before receipts were saved
    if not order.receipt:
        return jsonify({"error": "A receipt is created when the order is confirmed"}), 404
    return jsonify({"order": order.to_dict(), "receipt": order.receipt.to_dict()})


@admin_orders_bp.get("/<int:order_id>/payment-proof")
@require_head_admin
def get_payment_proof(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify({"proof": order.payment_proof})


@admin_orders_bp.post("/<int:order_id>/payment/verify")
@require_head_admin
def verify_payment(order_id):
    """Admin checked the GCash account and the payment arrived."""
    order = Order.query.get_or_404(order_id)
    if order.status == "cancelled":
        return jsonify({"error": "This order was cancelled"}), 400
    if order.payment_status == "paid":
        return jsonify({"error": "This order is already marked as paid"}), 400
    if not order.is_online_payment:
        return jsonify({"error": "Cash on Delivery is marked paid when the order is delivered"}), 400
    mark_paid(order)
    return jsonify({"order": order.to_dict()})


@admin_orders_bp.post("/<int:order_id>/payment/reject")
@require_head_admin
def reject_payment(order_id):
    """The reference/screenshot did not match a real payment. Send the order back
    to unpaid so the customer can try again or pick another method."""
    order = Order.query.get_or_404(order_id)
    if order.payment_status != "verifying":
        return jsonify({"error": "There is no submitted payment to reject on this order"}), 400
    note = str((request.get_json() or {}).get("note") or "").strip()[:300]
    old_reference = order.payment_reference
    reset_payment(order)
    db.session.commit()
    send_email(
        order.customer_email, f"Payment could not be verified - {order.order_number}",
        f"Hi {order.customer_name},\n\nWe could not verify the {order.payment_method} payment "
        f"(reference {old_reference}) for order {order.order_number}."
        + (f"\n\nNote from our team: {note}" if note else "")
        + "\n\nPlease open My Orders > To Pay to send the correct reference number or choose "
        "another payment method.",
        user_id=order.user_id,
    )
    return jsonify({"order": order.to_dict()})


@admin_orders_bp.post("/<int:order_id>/return/<decision>")
@require_head_admin
def decide_return(order_id, decision):
    order = Order.query.get_or_404(order_id)
    if decision not in ("approve", "reject"):
        return jsonify({"error": "Unknown decision"}), 400
    if order.return_status != "requested":
        return jsonify({"error": "There is no pending return request on this order"}), 400

    note = str((request.get_json() or {}).get("note") or "").strip()[:500] or None
    order.return_note = note

    if decision == "approve":
        order.return_status = "approved"
        if order.payment_status == "paid":
            order.payment_status = "refund_pending"
        for item in order.items:
            if item.product_id:
                product = db.session.get(Product, item.product_id)
                if product:
                    product.stock += item.quantity
    else:
        order.return_status = "rejected"

    db.session.commit()

    send_email(
        order.customer_email, f"Return request {order.return_status} - {order.order_number}",
        f"Hi {order.customer_name},\n\nYour return request for order {order.order_number} "
        f"was {order.return_status}."
        + (f"\n\nNote from our team: {note}" if note else "")
        + ("\n\nYour refund will be processed by our team." if decision == "approve" else ""),
        user_id=order.user_id,
    )
    return jsonify({"order": order.to_dict()})


@admin_orders_bp.post("/<int:order_id>/refunded")
@require_head_admin
def mark_refunded(order_id):
    order = Order.query.get_or_404(order_id)
    if order.payment_status != "refund_pending":
        return jsonify({"error": "This order has no pending refund"}), 400
    order.payment_status = "refunded"
    db.session.commit()
    return jsonify({"order": order.to_dict()})
