import random
from datetime import datetime
from app.extensions import db
from app.models import Receipt


def generate_order_number():
    today = datetime.utcnow().strftime("%Y%m%d")
    suffix = random.randint(1000, 9999)
    return f"ORD-{today}-{suffix}"


def generate_tracking_number():
    return f"RC-TRK-{random.randint(10000, 99999)}"


def generate_receipt_number():
    today = datetime.utcnow().strftime("%Y%m%d")
    suffix = random.randint(10000, 99999)
    return f"RCPT-{today}-{suffix}"


def create_receipt_for_order(order):
    """Called when an admin confirms an order. Snapshots the order items
    so the receipt stays accurate even if products change later."""
    items_snapshot = [item.to_dict() for item in order.items]

    receipt = Receipt(
        order_id=order.id,
        receipt_number=generate_receipt_number(),
        items_snapshot=items_snapshot,
        subtotal=order.subtotal,
        shipping_fee=order.shipping_fee,
        total=order.total,
    )
    db.session.add(receipt)
    db.session.commit()
    return receipt
