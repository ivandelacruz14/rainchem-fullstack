from datetime import datetime

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Order
from app.models.order import COD, GCASH, CARD
from app.services import paymongo
from app.services import payment_flow
from app.services.payment_flow import start_checkout, mark_paid
from app.services.email_service import send_email
from app.utils.auth_decorators import require_user, current_user_id

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")

MAX_PROOF_CHARS = 3_000_000  # ~2 MB of base64, the browser shrinks screenshots well below this


def _my_order(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user_id():
        return None
    return order


def _methods_payload():
    online = payment_flow.available_online_methods()
    return {
        COD: True,
        GCASH: GCASH in online,
        CARD: CARD in online,
    }


@payments_bp.get("/config")
def config():
    return jsonify({"methods": _methods_payload(), "demoMode": paymongo.demo_mode()})


@payments_bp.get("/orders/<int:order_id>")
@require_user
def order_payment_info(order_id):
    """Everything the payment page needs: the order, which methods can be used,
    and (for GCash) where to send the money."""
    order = _my_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({
        "order": order.to_dict(),
        "methods": _methods_payload(),
        "gcash": payment_flow.gcash_for_order(order) if order.payment_method == GCASH else None,
        "demoMode": paymongo.demo_mode(),
    })


@payments_bp.post("/orders/<int:order_id>/method")
@require_user
def change_method(order_id):
    """Lets the customer switch between Cash on Delivery, GCash and card until
    the order is confirmed or paid."""
    order = _my_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if not order.to_dict()["canChangePayment"]:
        return jsonify({"error": "The payment method can no longer be changed for this order"}), 400

    method = (request.get_json() or {}).get("method")
    if method not in payment_flow.available_methods():
        return jsonify({"error": f"{method or 'That method'} is not available right now"}), 400

    if method != order.payment_method:
        order.payment_method = method
        payment_flow.reset_payment(order)
        db.session.commit()
    return jsonify({
        "order": order.to_dict(),
        "gcash": payment_flow.gcash_for_order(order) if order.payment_method == GCASH else None,
    })


@payments_bp.post("/orders/<int:order_id>/gcash")
@require_user
def submit_gcash(order_id):
    """The customer paid through GCash and sends the reference number (and
    optionally a screenshot). An admin then checks it against the GCash
    account and marks the order as paid."""
    order = _my_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if order.status == "cancelled":
        return jsonify({"error": "This order was cancelled"}), 400
    if order.payment_method != GCASH:
        return jsonify({"error": "This order is not set to pay with GCash"}), 400
    if order.payment_status == "paid":
        return jsonify({"error": "This order is already paid"}), 400

    data = request.get_json() or {}
    reference = payment_flow.valid_gcash_reference(data.get("reference"))
    if not reference:
        return jsonify({"error": "Please enter the GCash reference number from your payment receipt"}), 400

    duplicate = Order.query.filter(Order.payment_reference == reference, Order.id != order.id).first()
    if duplicate:
        return jsonify({"error": "That reference number was already used on another order"}), 400

    proof = data.get("proof")
    if proof:
        if not isinstance(proof, str) or not proof.startswith("data:image/") or len(proof) > MAX_PROOF_CHARS:
            return jsonify({"error": "The screenshot must be an image under 2 MB"}), 400
        order.payment_proof = proof

    order.payment_reference = reference
    order.payment_submitted_at = datetime.utcnow()
    order.payment_status = "verifying"
    db.session.commit()

    send_email(
        order.customer_email, f"GCash payment submitted - {order.order_number}",
        f"Hi {order.customer_name},\n\nWe received your GCash reference number ({reference}) for order "
        f"{order.order_number} (PHP {float(order.total):.2f}). Our team will verify it shortly and "
        "you'll get another email once it's confirmed.",
        user_id=order.user_id,
    )
    return jsonify({"order": order.to_dict()})


@payments_bp.post("/orders/<int:order_id>/checkout")
@require_user
def checkout(order_id):
    """Starts the secure card page (PayMongo). Cards only."""
    order = _my_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if order.status == "cancelled":
        return jsonify({"error": "This order was cancelled"}), 400
    if order.payment_method != CARD:
        return jsonify({"error": "This order is not set to pay by card"}), 400
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

    if (
        order.payment_method == CARD and order.payment_status != "paid"
        and order.payment_reference and not order.payment_reference.startswith("demo-")
    ):
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
