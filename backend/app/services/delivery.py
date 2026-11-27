"""Delivery verification. An order can be delivered only when every unit is scanned and a proof photo is uploaded.
Scans are checked against the order on the server, never trusted from the screen."""
from datetime import datetime

from sqlalchemy import func

from app.extensions import db
from app.models import Product
from app.models.delivery import OrderScan


def required(order):
    """product id -> units in the order. Lines without a product cannot be scanned."""
    counts = {}
    for item in order.items:
        if item.product_id:
            counts[item.product_id] = counts.get(item.product_id, 0) + item.quantity
    return counts


def accepted(order):
    """Accepted scans for the current delivery attempt. After a reschedule the units leave the warehouse again,
    so only scans made after the admin confirmed the reschedule count. Older scans stay in the history."""
    query = (db.session.query(OrderScan.product_id, func.count(OrderScan.id))
             .filter(OrderScan.order_id == order.id, OrderScan.result == "accepted"))
    if order.failed_confirmed_at:
        query = query.filter(OrderScan.scanned_at >= order.failed_confirmed_at)
    rows = query.group_by(OrderScan.product_id).all()
    return {pid: int(n) for pid, n in rows}


def missing(order):
    """Everything still blocking delivery: unscannable lines, and products with fewer scanned units than ordered."""
    need, got = required(order), accepted(order)
    out = []
    for item in order.items:
        if not item.product_id:
            out.append({"productId": None, "name": item.product_name, "required": item.quantity, "scanned": 0,
                        "reason": "This product no longer exists and cannot be scanned"})
    for pid, qty in need.items():
        if got.get(pid, 0) < qty:
            name = next((i.product_name for i in order.items if i.product_id == pid), "")
            product = db.session.get(Product, pid)
            out.append({"productId": pid, "name": name, "required": qty, "scanned": got.get(pid, 0),
                        "barcodeSet": bool(product and product.barcode)})
    return out


def record_scan(order, rider, code):
    code = (code or "").strip()
    product = Product.query.filter_by(barcode=code).first() if code else None
    if not product:
        result, reason, pid = "rejected", "Unrecognized barcode or QR code", None
    elif product.id not in required(order):
        result, reason, pid = "rejected", f"{product.name} is not part of this order", product.id
    elif accepted(order).get(product.id, 0) >= required(order)[product.id]:
        result, reason, pid = "rejected", f"All units of {product.name} are already scanned", product.id
    else:
        result, reason, pid = "accepted", None, product.id
    db.session.add(OrderScan(order_id=order.id, product_id=pid, rider_id=rider.id, code=code[:64],
                             result=result, reason=reason, scanned_at=datetime.utcnow()))
    db.session.commit()
    return result == "accepted", reason or f"{product.name} verified", product


def confirm_package_scan(order, rider, code):
    """The order sticker is the QR code of the whole package. Scanning it confirms every unit that is still
    missing, so the rider does not need a separate barcode for each item. Each unit is still recorded."""
    got = accepted(order)
    now = datetime.utcnow()
    for pid, qty in required(order).items():
        for _ in range(max(0, qty - got.get(pid, 0))):
            db.session.add(OrderScan(order_id=order.id, product_id=pid, rider_id=rider.id, code=(code or "")[:64],
                                     result="accepted", reason="Confirmed by the order sticker", scanned_at=now))
    db.session.commit()

