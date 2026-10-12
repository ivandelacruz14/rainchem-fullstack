from datetime import datetime

from flask import current_app

from app.extensions import db
from app.services import paymongo
from app.services.email_service import send_email


def start_checkout(order):
    frontend = current_app.config["FRONTEND_URL"].rstrip("/")

    if paymongo.demo_mode():
        order.payment_reference = f"demo-{order.id}"
        db.session.commit()
        return f"{frontend}/payment/demo/{order.id}"

    if not paymongo.is_configured():
        raise paymongo.PaymentError(
            "Online payment is not available right now. Please choose Cash on Delivery."
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
