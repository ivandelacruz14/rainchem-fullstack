import os
import re
from datetime import datetime

from flask import current_app

from app.extensions import db
from app.models.order import COD, GCASH, CARD
from app.models.setting import get_setting
from app.services import paymongo, qrph
from app.services.email_service import send_email

GCASH_KEYS = ("gcash_number", "gcash_name", "gcash_link", "gcash_qr", "gcash_note")
_ENV_FALLBACK = {
    "gcash_number": "GCASH_NUMBER",
    "gcash_name": "GCASH_ACCOUNT_NAME",
    "gcash_link": "GCASH_PAYMENT_LINK",
    "gcash_note": "GCASH_NOTE",
}


def gcash_details():
    """GCash payment details shown to the customer. Set by an admin under
    Payment Settings (or by GCASH_* environment variables as a fallback)."""
    details = {}
    for key in GCASH_KEYS:
        value = get_setting(key, "")
        if not value and key in _ENV_FALLBACK:
            value = os.environ.get(_ENV_FALLBACK[key], "")
        details[key] = (value or "").strip()
    return {
        "number": details["gcash_number"],
        "accountName": details["gcash_name"],
        "link": details["gcash_link"],
        "qr": details["gcash_qr"],
        "note": details["gcash_note"],
    }


def gcash_qr_payload():
    """The text inside the shop's own GCash / QR Ph code (admin only)."""
    return get_setting("gcash_qr_payload", "").strip()


def gcash_configured():
    d = gcash_details()
    return bool(d["number"] or d["link"] or d["qr"] or gcash_qr_payload())


def gcash_for_order(order):
    """What the customer sees for this order. If the shop saved its QR code text,
    the QR shown has this order's amount already filled in."""
    details = gcash_details()
    dynamic = None
    payload = gcash_qr_payload()
    if payload:
        try:
            dynamic = qrph.to_svg_data_uri(qrph.with_amount(payload, order.total))
        except qrph.QrError:
            dynamic = None  # a damaged saved code must never break the payment page
    details["dynamicQr"] = dynamic
    details["amount"] = f"{float(order.total):.2f}"
    return details


def card_available():
    return CARD in paymongo.available_methods()


def available_online_methods():
    methods = []
    if gcash_configured():
        methods.append(GCASH)
    if card_available():
        methods.append(CARD)
    return methods


def available_methods():
    return [COD] + available_online_methods()


def valid_gcash_reference(value):
    """GCash reference numbers are 13 digits, but be forgiving: 6-30 letters/digits."""
    cleaned = re.sub(r"[\s-]", "", value or "").upper()
    return cleaned if re.fullmatch(r"[A-Z0-9]{6,30}", cleaned) else None


def reset_payment(order):
    """Clears everything tied to the previous payment method."""
    order.payment_reference = None
    order.payment_proof = None
    order.payment_submitted_at = None
    order.payment_status = "unpaid"
    order.paid_at = None


def start_checkout(order):
    """Starts a PayMongo card checkout. Only cards use PayMongo."""
    if order.payment_method != CARD:
        raise paymongo.PaymentError("This order is not set to pay by card.")

    frontend = current_app.config["FRONTEND_URL"].rstrip("/")

    if paymongo.demo_mode():
        order.payment_reference = f"demo-{order.id}"
        db.session.commit()
        return f"{frontend}/payment/demo/{order.id}"

    if not paymongo.is_configured():
        raise paymongo.PaymentError(
            "Card payment is not available right now. Please choose GCash or Cash on Delivery."
        )

    result_url = f"{frontend}/payment/result?order={order.id}"
    session_id, checkout_url = paymongo.create_checkout_session(
        order, success_url=result_url, cancel_url=result_url + "&cancelled=1",
    )
    order.payment_reference = session_id
    db.session.commit()
    return checkout_url


def mark_paid(order, reference=None):
    if order.payment_status == "paid":
        return False
    order.payment_status = "paid"
    order.paid_at = datetime.utcnow()
    if reference:
        order.payment_reference = reference
    db.session.commit()

    send_email(
        order.customer_email, f"Payment received - {order.order_number}",
        f"Hi {order.customer_name},\n\nWe received your {order.payment_method} payment of "
        f"PHP {float(order.total):.2f} for order {order.order_number}. Our team will confirm "
        "and prepare your order shortly.",
        user_id=order.user_id,
    )
    return True
