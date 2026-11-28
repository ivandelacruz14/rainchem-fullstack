"""Cash on delivery: what each rider collected, what the office received, and what is still with the rider.
Also a small performance summary per rider."""
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Admin, Order
from app.services import audit
from app.utils.auth_decorators import current_admin, require_permission

admin_remittance_bp = Blueprint("admin_remittance", __name__, url_prefix="/api/admin/remittances")


def _money(value):
    return round(float(value or 0), 2)


def rider_cash(rider_id):
    """(collected, remitted) totals for one rider."""
    rows = Order.query.filter(Order.rider_id == rider_id, Order.cod_amount.isnot(None)).all()
    collected = sum(float(o.cod_amount) for o in rows)
    remitted = sum(float(o.cod_amount) for o in rows if o.cod_remitted_at)
    return round(collected, 2), round(remitted, 2)


@admin_remittance_bp.get("")
@require_permission("orders")
def summary():
    riders = Admin.query.filter(Admin.role == "Rider").order_by(Admin.name).all()
    out = []
    for rider in riders:
        orders = Order.query.filter(Order.rider_id == rider.id).all()
        cod = [o for o in orders if o.cod_amount is not None]
        delivered = [o for o in orders if o.status == "delivered"]
        failed = [o for o in orders if o.failed_at is not None]
        collected = sum(float(o.cod_amount) for o in cod)
        remitted = sum(float(o.cod_amount) for o in cod if o.cod_remitted_at)
        out.append({
            "riderId": rider.id, "riderName": rider.name, "phone": rider.phone, "isActive": bool(rider.is_active),
            "delivered": len(delivered), "failed": len(failed),
            "collected": round(collected, 2), "remitted": round(remitted, 2),
            "outstanding": round(collected - remitted, 2),
            "pending": [{
                "id": o.id, "orderNumber": o.order_number, "customer": o.customer_name,
                "amount": _money(o.cod_amount),
                "deliveredAt": o.delivered_at.isoformat() if o.delivered_at else None,
            } for o in sorted(cod, key=lambda x: x.id) if not o.cod_remitted_at],
        })
    return jsonify({
        "riders": out,
        "totals": {
            "collected": round(sum(r["collected"] for r in out), 2),
            "remitted": round(sum(r["remitted"] for r in out), 2),
            "outstanding": round(sum(r["outstanding"] for r in out), 2),
        },
    })


@admin_remittance_bp.post("/receive")
@require_permission("manage_orders")
def receive():
    """The office received the cash for these orders from the rider."""
    ids = (request.get_json(silent=True) or {}).get("orderIds")
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "Choose at least one order"}), 400
    orders = Order.query.filter(Order.id.in_([int(i) for i in ids if str(i).isdigit()]),
                                Order.cod_amount.isnot(None), Order.cod_remitted_at.is_(None)).all()
    if not orders:
        return jsonify({"error": "These orders were already received or have no cash to remit"}), 400
    now = datetime.utcnow()
    admin = current_admin()
    for order in orders:
        order.cod_remitted_at = now
        order.cod_remitted_by = admin.id
        audit.record("cod_received", "order", order.id, {"remitted": False}, {"remitted": True}, None, admin)
    db.session.commit()
    return jsonify({"received": len(orders), "amount": round(sum(float(o.cod_amount) for o in orders), 2)})
