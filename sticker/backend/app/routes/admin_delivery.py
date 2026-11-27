from datetime import date, datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Admin, Order, OrderStatusHistory
from app.models.order import STATUS_LABELS
from app.models.delivery import DeliveryProof
from app.services import audit
from app.services.pod import receipt_payload
from app.utils.auth_decorators import current_admin, require_permission

admin_delivery_bp = Blueprint("admin_delivery", __name__, url_prefix="/api/admin")


@admin_delivery_bp.get("/failed-deliveries")
@require_permission("orders")
def failed_deliveries():
    """tab=awaiting: the rider reported the delivery failed and the admin still has to confirm it.
    tab=rescheduled: confirmed, with the new delivery date."""
    tab = request.args.get("tab", "awaiting")
    status = {"awaiting": "delivery_failed", "rescheduled": "rescheduled"}.get(tab)
    if status is None:
        return jsonify({"error": "Unknown tab"}), 400
    rows = Order.query.filter_by(status=status).order_by(Order.failed_at.desc(), Order.id.desc()).limit(200).all()
    items = []
    for o in rows:
        payment = receipt_payload(o)["payment"]
        rider = db.session.get(Admin, o.rider_id) if o.rider_id else None
        items.append({
            "orderId": o.id, "orderNumber": o.order_number, "customerName": o.customer_name,
            "customerPhone": o.customer_phone, "address": o.address_line1, "rider": rider.name if rider else None,
            "failedReason": o.failed_reason, "failedAt": o.failed_at.isoformat() if o.failed_at else None,
            "rescheduledFor": o.rescheduled_for.isoformat() if o.rescheduled_for else None,
            "paymentMethod": o.payment_method, "codAmount": payment["codAmountToCollect"],
        })
    return jsonify({"tab": tab, "items": items})


@admin_delivery_bp.post("/orders/<int:order_id>/confirm-failed")
@require_permission("manage_orders")
def confirm_failed(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if order.status != "delivery_failed":
        return jsonify({"error": "Only a failed delivery can be confirmed"}), 400
    try:
        new_date = date.fromisoformat(str((request.get_json() or {}).get("rescheduledFor") or ""))
    except ValueError:
        return jsonify({"error": "Choose the new delivery date"}), 400
    if new_date < date.today():
        return jsonify({"error": "The new delivery date cannot be in the past"}), 400
    order.status = "rescheduled"
    order.rescheduled_for = new_date
    order.failed_confirmed_at = datetime.utcnow()
    order.failed_confirmed_by = current_admin().id
    db.session.add(OrderStatusHistory(order_id=order.id, status="rescheduled"))
    audit.record("delivery_rescheduled", "order", order.id, {"status": "delivery_failed"},
                 {"status": "rescheduled", "rescheduledFor": new_date.isoformat()}, order.failed_reason, current_admin())
    db.session.commit()
    return jsonify({"order": order.to_dict()})


@admin_delivery_bp.get("/orders/<int:order_id>/sticker")
@require_permission("orders")
def sticker(order_id):
    """Everything printed on the QR and barcode sticker. Taken from the stored order."""
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    data = receipt_payload(order)
    return jsonify({"sticker": {
        "orderNumber": data["orderNumber"], "qrText": data["qrText"], "barcodeValue": data["barcodeValue"],
        "customer": data["customer"], "payment": data["payment"], "itemCount": sum(i["quantity"] for i in data["items"]),
        "orderDate": data["orderDate"], "deliveryDate": data["deliveryDate"],
        "items": data["items"], "total": data["total"], "company": data["company"],
    }})


@admin_delivery_bp.get("/delivered-orders")
@require_permission("orders")
def delivered_orders():
    rows = Order.query.filter_by(status="delivered").order_by(Order.id.desc()).limit(200).all()
    items = []
    for o in rows:
        rider = db.session.get(Admin, o.rider_id) if o.rider_id else None
        items.append({
            "id": o.id, "orderNumber": o.order_number, "customerName": o.customer_name,
            "riderName": rider.name if rider else None, "total": float(o.total),
            "paymentMethod": o.payment_method,
            "deliveredAt": o.delivered_at.isoformat() if o.delivered_at else None,
            "deliveryNote": o.delivery_note,
            "hasPhoto": DeliveryProof.query.filter_by(order_id=o.id).first() is not None,
        })
    return jsonify({"orders": items})


DISPATCH_STATUSES = ("confirmed", "processing", "ready_for_delivery", "rescheduled", "shipped")


@admin_delivery_bp.get("/dispatch")
@require_permission("orders")
def dispatch():
    """Every order that still needs the office: confirmed orders to send, and orders already with a rider."""
    rows = Order.query.filter(Order.status.in_(DISPATCH_STATUSES)).order_by(Order.id.desc()).limit(300).all()
    items = []
    for o in rows:
        rider = db.session.get(Admin, o.rider_id) if o.rider_id else None
        items.append({
            "id": o.id, "orderNumber": o.order_number, "customerName": o.customer_name,
            "customerPhone": o.customer_phone, "address": o.address_line1,
            "status": o.status, "statusLabel": STATUS_LABELS.get(o.status, o.status),
            "riderId": o.rider_id, "riderName": rider.name if rider else None,
            "paymentMethod": o.payment_method, "codAmount": receipt_payload(o)["payment"]["codAmountToCollect"],
        })
    return jsonify({"orders": items})
