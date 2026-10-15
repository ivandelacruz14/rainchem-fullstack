import random
from datetime import datetime
from app.extensions import db
from app.models import Receipt


def _unique_number(make, model, column):
    """Random numbers can repeat. Check the database so two customers never get the
    same order/receipt number (that used to cause a server error at checkout)."""
    for attempt in range(40):
        candidate = make(wide=attempt >= 20)  # fall back to more digits on very busy days
        if not db.session.query(model.id).filter(column == candidate).first():
            return candidate
    raise RuntimeError("Could not generate a unique number")


def generate_order_number():
    from app.models import Order
    today = datetime.utcnow().strftime("%Y%m%d")

    def make(wide):
        suffix = random.randint(100000, 999999) if wide else random.randint(1000, 9999)
        return f"ORD-{today}-{suffix}"

    return _unique_number(make, Order, Order.order_number)


def generate_tracking_number():
    return f"RC-TRK-{random.randint(10000, 99999)}"


def generate_receipt_number():
    today = datetime.utcnow().strftime("%Y%m%d")

    def make(wide):
        suffix = random.randint(1000000, 9999999) if wide else random.randint(10000, 99999)
        return f"RCPT-{today}-{suffix}"

    return _unique_number(make, Receipt, Receipt.receipt_number)


def create_receipt_for_order(order, commit=True):
    """Called when an admin confirms an order. Snapshots the order items
    so the receipt stays accurate even if products change later.
    Safe to call twice: an order only ever has one receipt."""
    if order.receipt:
        return order.receipt

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
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return receipt
