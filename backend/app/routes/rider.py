import hashlib
from datetime import datetime

from flask import Blueprint, Response, current_app, jsonify, request

from app.extensions import db
from app.services.pod import matches_order
from app.models import Order, OrderStatusHistory
from app.models.delivery import DeliveryProof
from app.services import audit, delivery as svc, live_chat as chat
from app.services.payment_flow import mark_paid
from app.utils.auth_decorators import current_admin, require_permission

rider_bp = Blueprint("rider", __name__, url_prefix="/api/rider")
ACTIVE = ("ready_for_delivery", "shipped")
DASHBOARD_STATES = ("ready_for_delivery", "shipped", "delivery_failed", "rescheduled", "delivered")


def _err(message, status=400):
    return jsonify({"error": message}), status


def _mine(order_id):
    """Riders see only the orders assigned to them. Anything else looks like it does not exist."""
    order = db.session.get(Order, order_id)
    if not order or order.rider_id != current_admin().id:
        return None
    return order


def _detail(order):
    data = order.to_dict()
    unpaid_cash = (not order.is_online_payment) and order.payment_status != "paid"
    data.update({
        "customer": {"name": order.customer_name, "phone": order.customer_phone},
        "address": data.get("formatted") or order.address_line1,
        "amountToCollect": float(order.total) if unpaid_cash else 0,
        "items": [{"productId": i.product_id, "name": i.product_name, "quantity": i.quantity} for i in order.items],
        "scanned": svc.accepted(order),
        "missing": svc.missing(order),
        "hasProof": DeliveryProof.query.filter_by(order_id=order.id).first() is not None,
    })
    return data


@rider_bp.get("")
@require_permission("deliveries")
def my_deliveries():
    rows = Order.query.filter(Order.rider_id == current_admin().id,
                              Order.status.in_(ACTIVE + ("delivery_failed", "rescheduled"))).order_by(Order.id).all()
    return jsonify({"orders": [_detail(o) for o in rows]})


@rider_bp.get("/summary")
@require_permission("deliveries")
def summary():
    rows = Order.query.filter(Order.rider_id == current_admin().id, Order.status.in_(DASHBOARD_STATES)).all()

    def count(*states):
        return sum(1 for o in rows if o.status in states)

    return jsonify({"summary": {
        "total": len(rows),
        "pending": count("ready_for_delivery"),
        "outForDelivery": count("shipped"),
        "delivered": count("delivered"),
        "failed": count("delivery_failed", "rescheduled"),
    }})


def _digits(value):
    return "".join(ch for ch in (value or "") if ch.isdigit())


@rider_bp.get("/search")
@require_permission("deliveries")
def search():
    """Finds the rider's own orders by customer name, order number, or phone number."""
    q = (request.args.get("q") or "").strip()[:80]
    if len(q) < 2:
        return jsonify({"orders": [], "message": "Type at least 2 characters"})
    q_lower, q_digits = q.lower(), _digits(q)
    rows = Order.query.filter(Order.rider_id == current_admin().id, Order.status.in_(DASHBOARD_STATES)).order_by(Order.id.desc()).all()
    found = []
    for o in rows:
        hit = (q_lower in (o.customer_name or "").lower()
               or q_lower in (o.order_number or "").lower()
               or (len(q_digits) >= 4 and q_digits in _digits(o.customer_phone)))
        if hit:
            found.append({"id": o.id, "orderNumber": o.order_number, "customerName": o.customer_name,
                          "customerPhone": o.customer_phone, "status": o.status,
                          "statusLabel": o.to_dict()["statusLabel"], "address": o.address_line1})
    return jsonify({"orders": found[:50]})


@rider_bp.post("/<int:order_id>/fail")
@require_permission("deliveries")
def report_failed(order_id):
    """The delivery did not happen today. The reason is required, and the admin confirms it and sets a new date."""
    order = _mine(order_id)
    if not order:
        return _err("Order not found", 404)
    if order.status != "shipped":
        return _err("Only an order that is out for delivery can be reported as failed")
    reason = str((request.get_json() or {}).get("reason") or "").strip()[:500]
    if len(reason) < 5:
        return _err("Write the reason the delivery failed (at least 5 characters)")
    order.status = "delivery_failed"
    order.failed_reason = reason
    order.failed_at = datetime.utcnow()
    db.session.add(OrderStatusHistory(order_id=order.id, status="delivery_failed"))
    audit.record("delivery_failed", "order", order.id, {"status": "shipped"}, {"status": "delivery_failed"}, reason, current_admin())
    db.session.commit()
    return jsonify({"order": _detail(order)})


@rider_bp.get("/<int:order_id>")
@require_permission("deliveries")
def delivery_detail(order_id):
    order = _mine(order_id)
    if not order:
        return _err("Order not found", 404)
    return jsonify({"order": _detail(order)})


@rider_bp.post("/<int:order_id>/start")
@require_permission("deliveries")
def start(order_id):
    order = _mine(order_id)
    if not order:
        return _err("Order not found", 404)
    if order.status not in ("ready_for_delivery", "rescheduled"):
        return _err("This order is not ready to leave the warehouse")
    order.status = "shipped"
    db.session.add(OrderStatusHistory(order_id=order.id, status="shipped"))
    db.session.commit()
    return jsonify({"order": _detail(order)})


@rider_bp.post("/<int:order_id>/scan")
@require_permission("deliveries")
def scan(order_id):
    order = _mine(order_id)
    if not order:
        return _err("Order not found", 404)
    code = (request.get_json() or {}).get("code")
    if matches_order(order, code):
        # The order sticker identifies the order. It is not a unit, so nothing is counted here.
        return jsonify({"accepted": True, "orderConfirmed": True,
                        "message": f"Order {order.order_number} confirmed", "order": _detail(order)})
    if order.status != "shipped":
        return _err("Scan the order sticker to confirm the order. Start the delivery before scanning the items.")
    ok, message, _ = svc.record_scan(order, current_admin(), code)
    return jsonify({"accepted": ok, "message": message, "order": _detail(order)}), (200 if ok else 422)


@rider_bp.post("/<int:order_id>/proof")
@require_permission("deliveries")
def upload_proof(order_id):
    order = _mine(order_id)
    if not order:
        return _err("Order not found", 404)
    if order.status != "shipped":
        return _err("Start the delivery before uploading proof")
    if DeliveryProof.query.filter_by(order_id=order.id).first():
        return _err("The proof for this order is already uploaded and cannot be replaced", 409)
    upload = request.files.get("image")
    if upload is None or upload.filename == "":
        return _err("Choose a photo")
    try:
        data, mime = chat.read_upload(upload)
    except chat.LiveChatError as error:
        return _err(str(error), error.status)
    db.session.add(DeliveryProof(order_id=order.id, rider_id=current_admin().id, data=data, mime=mime,
                                 size=len(data), sha256=hashlib.sha256(data).hexdigest()))
    db.session.commit()
    return jsonify({"order": _detail(order)}), 201


@rider_bp.get("/<int:order_id>/proof")
@require_permission("deliveries")
def get_proof(order_id):
    order = _mine(order_id)
    proof = DeliveryProof.query.filter_by(order_id=order_id).first() if order else None
    if not proof:
        return _err("No proof on file", 404)
    return Response(proof.data, mimetype=proof.mime, headers={
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox"})


@rider_bp.post("/<int:order_id>/deliver")
@require_permission("deliveries")
def deliver(order_id):
    order = _mine(order_id)
    if not order:
        return _err("Order not found", 404)
    note = str((request.get_json(silent=True) or {}).get("note") or "").strip()[:300]
    if order.status != "shipped":
        return _err("Only an order that is out for delivery can be marked delivered")
    gaps = svc.missing(order)
    if gaps:
        return jsonify({"error": "Scan every unit before delivering", "missing": gaps}), 400
    if not DeliveryProof.query.filter_by(order_id=order.id).first():
        return _err("Upload the delivery proof before delivering")
    if current_app.config.get("POD_REQUIRE_VERIFIED_RECEIPT"):
        from app.services.pod import latest_upload
        receipt = latest_upload(order)
        if receipt is None or receipt.status != "verified":
            return _err("The customer\u2019s delivery receipt must be verified by an admin before delivery is recorded")
    if order.is_online_payment and order.payment_status != "paid":
        return _err("This order has not been paid yet")
    if order.payment_status != "paid":
        mark_paid(order)  # cash on delivery: collected at the door, recorded the same way as the admin path
    order.status = "delivered"
    order.delivery_note = note or None
    db.session.add(OrderStatusHistory(order_id=order.id, status="delivered"))
    audit.record("delivered", "order", order.id, {"status": "shipped"}, {"status": "delivered"}, None, current_admin())
    db.session.commit()
    return jsonify({"order": _detail(order)})
