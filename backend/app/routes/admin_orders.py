from datetime import date, datetime
from flask import Blueprint, Response, request, jsonify

from app.extensions import db
from app.models import Admin, Order, OrderStatusHistory, Product
from app.models.delivery import DeliveryProof
from app.services import audit
from app.services.permissions import RIDER
from app.models.order import ORDER_STATUSES
from app.services.receipt_service import create_receipt_for_order
from app.services.pagination import page_args, page_slice, wants_page
from app.services.email_service import send_email
from app.services.payment_flow import mark_paid, reset_payment
from app.models import OrderItem
from app.services.inventory import stock_context
from app.utils.auth_decorators import current_admin, require_head_admin, require_permission

admin_orders_bp = Blueprint("admin_orders", __name__, url_prefix="/api/admin/orders")


@admin_orders_bp.get("")
@require_permission("orders")
def list_orders():
    admin = current_admin()
    status = request.args.get("status")
    query = Order.query
    # Without the manage_orders permission the list is the read-only view: no contact or payment details.
    limited = not admin.has_permission("manage_orders")
    if status == "returns":
        query = query.filter(Order.return_status != "none")
    elif status == "verifying":
        query = query.filter(Order.payment_status == "verifying", Order.status != "cancelled")
    elif status and status != "All":
        query = query.filter_by(status=status)
    query = query.order_by(Order.created_at.desc())
    meta = None
    if wants_page():
        page, per_page = page_args()
        orders, meta = page_slice(query, page, per_page)
    else:
        orders = query.all()
    body = {"scope": "limited", "orders": [o.to_scoped_dict(None) for o in orders]} if limited else {"scope": "full", "orders": [o.to_dict() for o in orders]}
    if meta:
        body["page"] = meta
    return jsonify(body)


@admin_orders_bp.get("/<int:order_id>")
@require_permission("manage_orders")
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify({"order": order.to_dict()})


@admin_orders_bp.post("/<int:order_id>/confirm")
@require_permission("manage_orders")
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
@require_permission("manage_orders")
def update_status(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json() or {}
    new_status = data.get("status")

    if order.status == "delivered":
        return jsonify({"error": "Delivered orders are final. Use the authorized correction if this is a mistake."}), 409
    if new_status in ("shipped", "delivered"):
        return jsonify({"error": "Out for delivery and delivered are set by the assigned rider after scanning and proof"}), 400
    allowed_next = {"pending_confirmation": ("confirmed", "cancelled"), "confirmed": ("processing", "cancelled"),
                    "processing": ("ready_for_delivery", "cancelled"), "ready_for_delivery": ("cancelled",)}
    if order.status in allowed_next and new_status != order.status and new_status not in allowed_next[order.status]:
        return jsonify({"error": f"An order cannot move from {order.status} to {new_status}"}), 400

    if new_status in ("delivery_failed", "rescheduled"):
        return jsonify({"error": "Failed deliveries are reported by the rider and confirmed in Delivery Confirmation"}), 400
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
                    with stock_context("cancel_restore", order=order, reference=f"order:{order.order_number}", reason="Cancelled by an administrator"):
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
@require_permission("manage_orders")
def get_receipt(order_id):
    order = Order.query.get_or_404(order_id)
    if not order.receipt and order.status in ("confirmed", "processing", "shipped", "delivered"):
        create_receipt_for_order(order)  # confirmed before receipts were saved
    if not order.receipt:
        return jsonify({"error": "A receipt is created when the order is confirmed"}), 404
    return jsonify({"order": order.to_dict(), "receipt": order.receipt.to_dict()})


@admin_orders_bp.get("/<int:order_id>/payment-proof")
@require_permission("manage_orders")
def get_payment_proof(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify({"proof": order.payment_proof})


@admin_orders_bp.post("/<int:order_id>/payment/verify")
@require_permission("manage_orders")
def verify_payment(order_id):
    """Admin checked the GCash account and the payment arrived."""
    order = Order.query.get_or_404(order_id)
    if order.status == "cancelled":
        return jsonify({"error": "This order was cancelled"}), 400
    if order.payment_status == "paid":
        return jsonify({"error": "This order is already marked as paid"}), 400
    if not order.is_online_payment:
        return jsonify({"error": "Cash on Delivery is marked paid when the order is delivered"}), 400
    if order.payment_reference:
        used = Order.query.filter(Order.payment_reference == order.payment_reference, Order.id != order.id,
                                  Order.payment_status == "paid").first()
        if used:
            return jsonify({"error": f"This payment reference was already used for order {used.order_number}"}), 409
    mark_paid(order)
    return jsonify({"order": order.to_dict()})


@admin_orders_bp.post("/<int:order_id>/payment/reject")
@require_permission("manage_orders")
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
@require_permission("manage_orders")
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
                    with stock_context("return", order=order, reference=f"order:{order.order_number}", reason="Return approved"):
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
@require_permission("manage_orders")
def mark_refunded(order_id):
    order = Order.query.get_or_404(order_id)
    if order.payment_status != "refund_pending":
        return jsonify({"error": "This order has no pending refund"}), 400
    order.payment_status = "refunded"
    db.session.commit()
    return jsonify({"order": order.to_dict()})


def _parse_date(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


@admin_orders_bp.post("/<int:order_id>/assign-rider")
@require_permission("manage_orders")
def assign_rider(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status not in ("confirmed", "processing", "ready_for_delivery", "rescheduled"):
        return jsonify({"error": "Confirm the order first, then send it to a rider"}), 400
    data = request.get_json() or {}
    rider = db.session.get(Admin, data.get("riderId")) if data.get("riderId") else None
    if rider is None or rider.role != RIDER or not rider.is_active:
        return jsonify({"error": "Choose an active rider"}), 400
    estimated = _parse_date(data.get("estimatedDate"))
    if estimated is None:
        return jsonify({"error": "Choose the estimated delivery date"}), 400
    if estimated < date.today():
        return jsonify({"error": "The estimated delivery date cannot be in the past"}), 400
    if not (rider.phone or "").strip():
        return jsonify({"error": f"{rider.name} has no phone number yet. Add it in Admin Accounts so customers can reach the rider."}), 400
    order.rider_id = rider.id
    order.rider_assigned_at = datetime.utcnow()
    order.estimated_delivery_date = estimated
    if order.status in ("confirmed", "processing"):
        # Sending to a rider means the order is ready to leave; no separate "ready" click is needed.
        order.status = "ready_for_delivery"
        db.session.add(OrderStatusHistory(order_id=order.id, status="ready_for_delivery"))
    audit.record("rider_assigned", "order", order.id, None, {"rider": rider.name}, None, current_admin())
    db.session.commit()
    return jsonify({"order": order.to_dict()})


@admin_orders_bp.post("/<int:order_id>/delivery-correction")
@require_head_admin
def delivery_correction(order_id):
    """The only way back from delivered. Keeps the scans and proof, and records the old status, the new one, and why."""
    order = Order.query.get_or_404(order_id)
    data = request.get_json() or {}
    reason = str(data.get("reason") or "").strip()
    if order.status != "delivered":
        return jsonify({"error": "Only a delivered order can be corrected"}), 400
    if data.get("status") != "shipped":
        return jsonify({"error": "A delivered order can only be corrected back to out for delivery"}), 400
    if not reason:
        return jsonify({"error": "Give a reason for the correction"}), 400
    order.status = "shipped"
    order.received_confirmed_at = None
    db.session.add(OrderStatusHistory(order_id=order.id, status="shipped"))
    audit.record("delivery_correction", "order", order.id, {"status": "delivered"}, {"status": "shipped"}, reason, current_admin())
    db.session.commit()
    return jsonify({"order": order.to_dict()})


@admin_orders_bp.get("/riders")
@require_permission("manage_orders")
def list_riders():
    """Active riders, for the assignment list. No other account details."""
    rows = Admin.query.filter_by(role=RIDER, is_active=True).order_by(Admin.name).all()
    return jsonify({"riders": [{"id": r.id, "name": r.name, "phone": r.phone} for r in rows]})


@admin_orders_bp.get("/<int:order_id>/delivery-proof")
@require_permission("orders")
def delivery_proof(order_id):
    proof = DeliveryProof.query.filter_by(order_id=order_id).first()
    if not proof:
        return jsonify({"error": "No proof on file"}), 404
    return Response(proof.data, mimetype=proof.mime, headers={
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox"})


@admin_orders_bp.get("/attention-count")
@require_permission("orders")
def attention_count():
    """Orders waiting for confirmation, and online payments waiting for verification. Used for the admin alert."""
    waiting = Order.query.filter(Order.status == "pending_confirmation").count()
    verifying = Order.query.filter(Order.payment_status == "verifying").count()
    return jsonify({"count": waiting, "verifying": verifying})

