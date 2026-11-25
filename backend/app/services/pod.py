"""Delivery receipt and proof of delivery. Everything shown on a receipt comes from the stored order.
The QR code holds only the order number and a keyed reference, never the customer's details."""
import base64
import binascii
import hashlib
import hmac
import re
from datetime import datetime

from flask import current_app

from app.models import Admin, Order, Product
from app.models.delivery import DeliveryReceiptUpload

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
SIGNATURE_MAX_BYTES = 300_000
NAME_RE = re.compile(r"^[^\W\d_](?:[^\W\d_]|[ .'\-])*$")


def detect_receipt_file(data):
    """Recognises a real file by its first bytes, not by its name. Returns the MIME type or None."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == PNG_MAGIC:
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:5] == b"%PDF-":
        return "application/pdf"
    return None


def parse_signature(data_url):
    prefix = "data:image/png;base64,"
    if not isinstance(data_url, str) or not data_url.startswith(prefix):
        return None
    try:
        raw = base64.b64decode(data_url[len(prefix):], validate=True)
    except (binascii.Error, ValueError):
        return None
    if raw[:8] != PNG_MAGIC or len(raw) > SIGNATURE_MAX_BYTES:
        return None
    return raw


def clean_printed_name(value):
    name = " ".join(str(value or "").split())
    if len(name) < 2 or len(name) > 120 or not NAME_RE.match(name):
        return None
    return name


def latest_upload(order):
    return DeliveryReceiptUpload.query.filter_by(order_id=order.id).order_by(DeliveryReceiptUpload.id.desc()).first()


def delivery_stage(order, upload):
    if order.status == "delivered":
        return "delivered"
    if order.status != "shipped":
        return "not_out_for_delivery"
    if upload is None or upload.status == "rejected":
        return "awaiting_receipt"
    if upload.status == "pending_verification":
        return "pending_verification"
    return "verified"


def qr_token(order):
    key = current_app.config["SECRET_KEY"].encode()
    return hmac.new(key, f"receipt|{order.order_number}".encode(), hashlib.sha256).hexdigest()[:16]


def qr_text(order):
    return f"RCPT|{order.order_number}|{qr_token(order)}"


def order_from_qr(text):
    parts = (text or "").strip().split("|")
    if len(parts) != 3 or parts[0] != "RCPT":
        return None
    order = Order.query.filter_by(order_number=parts[1]).first()
    if order is None or not hmac.compare_digest(parts[2], qr_token(order)):
        return None
    return order


def receipt_payload(order):
    upload = latest_upload(order)
    delivered_at = max((h.changed_at for h in order.history if h.status == "delivered" and h.changed_at), default=None)
    items, discount_total = [], 0.0
    for item in order.items:
        unit, qty = float(item.unit_price), int(item.quantity)
        rate = float(item.discount_rate or 0)
        list_unit = unit / (1 - rate) if 0 < rate < 1 else unit  # the stored unit price is already after the discount
        discount = round((list_unit - unit) * qty, 2)
        discount_total += discount
        product = Product.query.get(item.product_id) if item.product_id else None
        items.append({
            "productId": item.product_id, "name": item.product_name, "sku": product.sku if product else None,
            "quantity": qty, "unitPrice": unit, "discountRate": rate, "discount": discount,
            "subtotal": round(unit * qty, 2),
        })
    cod = order.payment_method.lower().startswith("cash") or order.payment_method.upper() == "COD"
    return {
        "company": "Rainchem International, Inc.",
        "receiptTitle": "Delivery Receipt",
        "receiptNumber": order.receipt.receipt_number if order.receipt else None,
        "orderNumber": order.order_number,
        "barcodeValue": order.order_number,
        "qrText": qr_text(order),
        "orderDate": order.created_at.isoformat() if order.created_at else None,
        "deliveryDate": delivered_at.isoformat() if delivered_at else None,
        "deliveryStage": delivery_stage(order, upload),
        "customer": {
            "name": order.customer_name, "phone": order.customer_phone,
            "address": ", ".join(x for x in [order.address_line1, order.address_city, order.address_province,
                                             order.address_region, order.address_zip] if x),
        },
        "items": items,
        "subtotal": float(order.subtotal), "discount": round(discount_total, 2),
        "shippingFee": float(order.shipping_fee), "total": float(order.total),
        "payment": {
            "method": order.payment_method, "status": order.payment_status,
            "isPrepaid": not cod, "isPaid": order.payment_status == "paid",
            "codAmountToCollect": float(order.total) if cod and order.payment_status != "paid" else 0.0,
        },
        "rider": Admin.query.get(order.rider_id).name if order.rider_id and Admin.query.get(order.rider_id) else None,
        "upload": upload_payload(upload) if upload else None,
    }


def upload_payload(row):
    return {
        "id": row.id, "orderId": row.order_id, "status": row.status, "mime": row.mime, "size": row.size,
        "printedName": row.printed_name, "acknowledgedAt": row.acknowledged_at.isoformat(),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "reviewedAt": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "rejectReason": row.reject_reason,
    }


def matches_order(order, code):
    """The rider confirms the order by scanning its QR code or barcode. The barcode holds the order number."""
    code = (code or "").strip()
    if not code:
        return False
    if code.startswith("RCPT|"):
        return order_from_qr(code) is not None and order_from_qr(code).id == order.id
    return code == order.order_number
