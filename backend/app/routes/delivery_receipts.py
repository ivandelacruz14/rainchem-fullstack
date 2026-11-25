import hashlib
import io
from datetime import datetime

import segno
from flask import Blueprint, Response, current_app, jsonify, request

from app.extensions import db
from app.models import Order, OrderStatusHistory
from app.models.delivery import DeliveryReceiptUpload
from app.services import audit
from app.services.pod import (clean_printed_name, delivery_stage, detect_receipt_file, latest_upload, matches_order,
                              order_from_qr, parse_signature, receipt_payload, upload_payload, qr_text)
from app.utils.auth_decorators import current_admin, require_permission

delivery_receipts_bp = Blueprint("delivery_receipts", __name__, url_prefix="/api")
SAFE_FILE_HEADERS = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
                     "Content-Security-Policy": "default-src 'none'; sandbox"}


def _err(message, status=400):
    return jsonify({"error": message}), status


def _my_order(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.rider_id != current_admin().id:
        return None
    return order


def _qr_png(text):
    buf = io.BytesIO()
    segno.make(text, error="m").save(buf, kind="png", scale=6, border=2)
    return Response(buf.getvalue(), mimetype="image/png", headers={"Cache-Control": "private, no-store"})


# ---------- receipt data ----------
@delivery_receipts_bp.get("/rider/orders/<int:order_id>/receipt")
@require_permission("deliveries")
def rider_receipt(order_id):
    order = _my_order(order_id)
    if not order:
        return _err("Order not found", 404)
    return jsonify({"receipt": receipt_payload(order)})


@delivery_receipts_bp.get("/rider/orders/<int:order_id>/receipt/qr.png")
@require_permission("deliveries")
def rider_receipt_qr(order_id):
    order = _my_order(order_id)
    if not order:
        return _err("Order not found", 404)
    return _qr_png(qr_text(order))


@delivery_receipts_bp.get("/admin/orders/<int:order_id>/receipt")
@require_permission("orders")
def admin_receipt(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return _err("Order not found", 404)
    return jsonify({"receipt": receipt_payload(order)})


@delivery_receipts_bp.get("/admin/orders/<int:order_id>/receipt/qr.png")
@require_permission("orders")
def admin_receipt_qr(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return _err("Order not found", 404)
    return _qr_png(qr_text(order))


@delivery_receipts_bp.post("/rider/orders/<int:order_id>/confirm-scan")
@require_permission("deliveries")
def rider_confirm_scan(order_id):
    """Step 1 for the rider: the scanned code must belong to this order before the receipt can be photographed."""
    order = _my_order(order_id)
    if not order:
        return _err("Order not found", 404)
    code = (request.get_json() or {}).get("code")
    if not matches_order(order, code):
        return _err("This code does not belong to this order. Check the receipt and scan again.", 400)
    return jsonify({"confirmed": True, "orderNumber": order.order_number})


@delivery_receipts_bp.post("/receipts/verify")
@require_permission("orders")
def verify_receipt_code():
    """Scanning the QR code on a receipt. Returns only the order number and its status, never customer details."""
    order = order_from_qr((request.get_json() or {}).get("code"))
    if order is None:
        return _err("This code does not match any order", 404)
    upload = latest_upload(order)
    return jsonify({"orderNumber": order.order_number, "deliveryStage": delivery_stage(order, upload),
                    "receiptStatus": upload.status if upload else "none"})


# ---------- rider upload ----------
@delivery_receipts_bp.post("/rider/orders/<int:order_id>/receipt-upload")
@require_permission("deliveries")
def rider_upload_receipt(order_id):
    order = _my_order(order_id)
    if not order:
        return _err("Order not found", 404)
    if order.status != "shipped":
        return _err("Start the delivery before uploading the receipt")
    latest = latest_upload(order)
    if latest and latest.status in ("pending_verification", "verified"):
        return _err("A receipt for this order is already waiting for review or has been verified", 409)

    upload = request.files.get("file")
    if upload is None or upload.filename == "":
        return _err("Choose the completed receipt (JPG, PNG, WEBP, or PDF)")
    limit = current_app.config["RECEIPT_MAX_MB"] * 1024 * 1024
    data = upload.read(limit + 1)
    if len(data) > limit:
        return _err(f"The receipt is larger than {current_app.config['RECEIPT_MAX_MB']} MB", 413)
    mime = detect_receipt_file(data)
    if mime is None:
        return _err("Only JPG, PNG, WEBP, or PDF files are accepted")

    if not matches_order(order, request.form.get("scanCode")):
        return _err("Scan this order's QR code or barcode first, then upload the receipt")
    signature = parse_signature(request.form.get("signature")) or b""  # optional: the signature is on the printed paper
    printed_name = clean_printed_name(request.form.get("printedName"))
    if printed_name is None:
        return _err("Enter the customer's printed name")
    if request.form.get("acknowledged") != "yes":
        return _err("The customer must acknowledge that the items were received")

    row = DeliveryReceiptUpload(
        order_id=order.id, rider_id=current_admin().id, data=data, mime=mime, size=len(data),
        sha256=hashlib.sha256(data).hexdigest(), signature=signature, printed_name=printed_name,
        acknowledged_at=datetime.utcnow(), status="pending_verification",
    )
    db.session.add(row)
    db.session.flush()
    audit.record("receipt_uploaded", "order", order.id, None,
                 {"upload": row.id, "mime": mime, "size": len(data)}, None, current_admin())
    db.session.commit()
    return jsonify({"upload": upload_payload(row)}), 201


# ---------- admin review ----------
TABS = {"pending_confirmation", "pending_verification", "verified", "rejected"}


@delivery_receipts_bp.get("/admin/delivery-confirmations")
@require_permission("orders")
def list_confirmations():
    tab = request.args.get("status", "pending_verification")
    if tab not in TABS:
        return _err("Unknown tab")
    search = (request.args.get("q") or "").strip()[:60]
    rows = []
    if tab == "pending_confirmation":
        for order in Order.query.filter_by(status="shipped").order_by(Order.id.desc()).limit(200).all():
            upload = latest_upload(order)
            if upload is None or upload.status == "rejected":
                rows.append((order, upload))
    else:
        wanted = {"pending_verification": "pending_verification", "verified": "verified", "rejected": "rejected"}[tab]
        for upload in DeliveryReceiptUpload.query.filter_by(status=wanted).order_by(DeliveryReceiptUpload.id.desc()).limit(200).all():
            rows.append((db.session.get(Order, upload.order_id), upload))
    items = []
    for order, upload in rows:
        if order is None:
            continue
        if search and search.lower() not in (order.order_number + " " + order.customer_name).lower():
            continue
        receipt = receipt_payload(order)
        items.append({
            "orderId": order.id, "orderNumber": order.order_number, "customerName": order.customer_name,
            "rider": receipt["rider"], "paymentMethod": order.payment_method,
            "codAmount": receipt["payment"]["codAmountToCollect"], "deliveryDate": receipt["deliveryDate"],
            "deliveryStage": receipt["deliveryStage"],
            "upload": upload_payload(upload) if upload else None,
        })
    return jsonify({"tab": tab, "items": items})


@delivery_receipts_bp.get("/admin/delivery-confirmations/<int:upload_id>/file")
@require_permission("orders")
def receipt_file(upload_id):
    row = db.session.get(DeliveryReceiptUpload, upload_id)
    if not row:
        return _err("Receipt not found", 404)
    return Response(row.data, mimetype=row.mime, headers=dict(SAFE_FILE_HEADERS, **{"Content-Disposition": "inline"}))


@delivery_receipts_bp.get("/admin/delivery-confirmations/<int:upload_id>/signature.png")
@require_permission("orders")
def receipt_signature(upload_id):
    row = db.session.get(DeliveryReceiptUpload, upload_id)
    if not row or not row.signature:
        return _err("No digital signature for this receipt", 404)
    return Response(row.signature, mimetype="image/png", headers=SAFE_FILE_HEADERS)


@delivery_receipts_bp.post("/admin/delivery-confirmations/<int:upload_id>/verify")
@require_permission("manage_orders")
def verify_receipt(upload_id):
    row = db.session.get(DeliveryReceiptUpload, upload_id)
    if not row:
        return _err("Receipt not found", 404)
    if row.status != "pending_verification":
        return _err("This receipt has already been reviewed", 409)
    row.status, row.reviewed_by, row.reviewed_at = "verified", current_admin().id, datetime.utcnow()
    audit.record("receipt_verified", "order", row.order_id, {"status": "pending_verification"},
                 {"status": "verified", "upload": row.id}, None, current_admin())
    db.session.commit()
    return jsonify({"upload": upload_payload(row)})


@delivery_receipts_bp.post("/admin/delivery-confirmations/<int:upload_id>/reject")
@require_permission("manage_orders")
def reject_receipt(upload_id):
    row = db.session.get(DeliveryReceiptUpload, upload_id)
    if not row:
        return _err("Receipt not found", 404)
    if row.status != "pending_verification":
        return _err("This receipt has already been reviewed", 409)
    reason = str((request.get_json() or {}).get("reason") or "").strip()[:500]
    if len(reason) < 5:
        return _err("Give a clear reason for rejecting the receipt")
    row.status, row.reviewed_by, row.reviewed_at, row.reject_reason = "rejected", current_admin().id, datetime.utcnow(), reason
    audit.record("receipt_rejected", "order", row.order_id, {"status": "pending_verification"},
                 {"status": "rejected", "upload": row.id}, reason, current_admin())
    db.session.commit()
    return jsonify({"upload": upload_payload(row)})
