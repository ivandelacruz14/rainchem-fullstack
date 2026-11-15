import hashlib
from datetime import datetime

from flask import Blueprint, Response, jsonify, request

from app.extensions import db
from app.models import Order, OrderStatusHistory
from app.models.delivery import DeliveryProof
from app.services import audit, delivery as svc, live_chat as chat
from app.services.payment_flow import mark_paid
from app.utils.auth_decorators import current_admin, require_permission

rider_bp = Blueprint("rider", __name__, url_prefix="/api/rider")
ACTIVE = ("ready_for_delivery", "shipped")


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
    rows = Order.query.filter(Order.rider_id == current_admin().id, Order.status.in_(ACTIVE)).order_by(Order.id).all()
    return jsonify({"orders": [_detail(o) for o in rows]})


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
    if order.status != "ready_for_delivery":
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
    if order.status != "shipped":
        return _err("Start the delivery before scanning")
    ok, message, _ = svc.record_scan(order, current_admin(), (request.get_json() or {}).get("code"))
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
    if order.status != "shipped":
        return _err("Only an order that is out for delivery can be marked delivered")
    gaps = svc.missing(order)
    if gaps:
        return jsonify({"error": "Scan every unit before delivering", "missing": gaps}), 400
    if not DeliveryProof.query.filter_by(order_id=order.id).first():
        return _err("Upload the delivery proof before delivering")
    if order.is_online_payment and order.payment_status != "paid":
        return _err("This order has not been paid yet")
    if order.payment_status != "paid":
        mark_paid(order)  # cash on delivery: collected at the door, recorded the same way as the admin path
    order.status = "delivered"
    db.session.add(OrderStatusHistory(order_id=order.id, status="delivered"))
    audit.record("delivered", "order", order.id, {"status": "shipped"}, {"status": "delivered"}, None, current_admin())
    db.session.commit()
    return jsonify({"order": _detail(order)})
