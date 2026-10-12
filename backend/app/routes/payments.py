from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Order
from app.models.order import COD
from app.services import paymongo
from app.services.payment_flow import start_checkout, mark_paid
from app.utils.auth_decorators import require_user, current_user_id

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")


def _my_order(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user_id():
        return None
    return order


@payments_bp.get("/config")
def config():
    online = paymongo.available_methods()
    return jsonify({
        "methods": {
            COD: True,
            "GCash": "GCash" in online,
            "Credit / Debit Card": "Credit / Debit Card" in online,
        },
        "demoMode": paymongo.demo_mode(),
    })


@payments_bp.post("/orders/<int:order_id>/checkout")
@require_user
def checkout(order_id):
    order = _my_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if order.status == "cancelled":
        return jsonify({"error": "This order was cancelled"}), 400
    if not order.is_online_payment:
        return jsonify({"error": "This order is Cash on Delivery, there is nothing to pay online"}), 400
    if order.payment_status == "paid":
        return jsonify({"error": "This order is already paid"}), 400

    try:
        url = start_checkout(order)
    except paymongo.PaymentError as error:
        return jsonify({"error": str(error)}), 502
    return jsonify({"checkoutUrl": url})


@payments_bp.post("/orders/<int:order_id>/verify")
@require_user
def verify(order_id):
    order = _my_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    if order.payment_status != "paid" and order.payment_reference and not order.payment_reference.startswith("demo-"):
        try:
            if paymongo.is_configured() and paymongo.is_session_paid(order.payment_reference):
                mark_paid(order)
        except paymongo.PaymentError as error:
            return jsonify({"error": str(error), "paid": False, "order": order.to_dict()}), 502

    return jsonify({"paid": order.payment_status == "paid", "order": order.to_dict()})


@payments_bp.post("/orders/<int:order_id>/demo-complete")
@require_user
def demo_complete(order_id):
    if not paymongo.demo_mode():
        return jsonify({"error": "Not available"}), 403
    order = _my_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if (request.get_json() or {}).get("success"):
        mark_paid(order, reference=f"demo-{order.id}")
    return jsonify({"paid": order.payment_status == "paid", "order": order.to_dict()})


@payments_bp.post("/webhook")
def webhook():
    raw = request.get_data()
    if not paymongo.verify_webhook(raw, request.headers.get("Paymongo-Signature", "")):
        return jsonify({"error": "Invalid signature"}), 400

    event = paymongo.parse_paid_event(raw)
    if event:
        session_id, reference = event
        order = Order.query.filter_by(payment_reference=session_id).first()
        if not order and reference:
            order = Order.query.filter_by(order_number=reference).first()
        if order and order.status != "cancelled":
            mark_paid(order)
    return jsonify({"received": True})
