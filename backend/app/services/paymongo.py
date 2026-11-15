import hashlib
import hmac
import json

import requests
from flask import current_app

API_BASE = "https://api.paymongo.com/v1"
TIMEOUT = 20

# PayMongo is only used for cards. GCash is paid directly to the store's own
# GCash number/link (see payment_flow.gcash_details), not through PayMongo.
METHOD_TYPES = {
    "Credit / Debit Card": "card",
}


class PaymentError(Exception):
    pass


def is_configured():
    return bool(current_app.config.get("PAYMONGO_SECRET_KEY"))


def demo_mode():
    return bool(current_app.config.get("PAYMENT_DEMO_MODE")) and not is_configured()


def available_methods():
    if is_configured() or demo_mode():
        return list(METHOD_TYPES.keys())
    return []


def _auth():
    return (current_app.config["PAYMONGO_SECRET_KEY"], "")


def _request(method, path, **kwargs):
    try:
        res = requests.request(method, f"{API_BASE}{path}", auth=_auth(), timeout=TIMEOUT, **kwargs)
    except requests.RequestException:
        raise PaymentError("Could not reach the payment provider. Please try again in a moment.")
    if res.status_code >= 400:
        current_app.logger.error("PayMongo error %s: %s", res.status_code, res.text[:500])
        raise PaymentError("The payment provider could not start this payment. Please try again.")
    return res.json()


def create_checkout_session(order, success_url, cancel_url):
    method_type = METHOD_TYPES.get(order.payment_method)
    if not method_type:
        raise PaymentError("This payment method is not available for online payment")

    line_items = [
        {
            "currency": "PHP",
            "amount": int(round(float(item.unit_price) * 100)),
            "name": item.product_name[:250],
            "quantity": item.quantity,
        }
        for item in order.items
    ]
    if float(order.shipping_fee) > 0:
        line_items.append({
            "currency": "PHP",
            "amount": int(round(float(order.shipping_fee) * 100)),
            "name": "Shipping fee",
            "quantity": 1,
        })

    payload = {"data": {"attributes": {
        "billing": {"name": order.customer_name, "email": order.customer_email, "phone": order.customer_phone},
        "line_items": line_items,
        "payment_method_types": [method_type],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "description": f"Rainchem order {order.order_number}",
        "reference_number": order.order_number,
        "send_email_receipt": False,
        "show_description": True,
        "show_line_items": True,
    }}}
    data = _request("POST", "/checkout_sessions", json=payload)["data"]
    return data["id"], data["attributes"]["checkout_url"]


def is_session_paid(session_id):
    data = _request("GET", f"/checkout_sessions/{session_id}")["data"]["attributes"]
    for payment in data.get("payments") or []:
        if payment.get("attributes", {}).get("status") == "paid":
            return True
    intent = data.get("payment_intent") or {}
    return intent.get("attributes", {}).get("status") == "succeeded"


def verify_webhook(raw_body, signature_header):
    secret = current_app.config.get("PAYMONGO_WEBHOOK_SECRET")
    if not secret or not signature_header:
        return False
    parts = dict(p.split("=", 1) for p in signature_header.split(",") if "=" in p)
    timestamp = parts.get("t")
    if not timestamp:
        return False
    expected = hmac.new(secret.encode(), f"{timestamp}.{raw_body.decode('utf-8')}".encode(), hashlib.sha256).hexdigest()
    candidates = [parts.get("li"), parts.get("te")]
    return any(c and hmac.compare_digest(expected, c) for c in candidates)


def parse_paid_event(raw_body):
    try:
        event = json.loads(raw_body)
        attrs = event["data"]["attributes"]
        if attrs.get("type") != "checkout_session.payment.paid":
            return None
        session = attrs["data"]
        return session["id"], session["attributes"].get("reference_number")
    except (KeyError, TypeError, ValueError):
        return None
