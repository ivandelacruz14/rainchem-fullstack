"""In-app notifications for the customer (the bell in the header)."""
from app.extensions import db
from app.models import Notification


def notify_order(order, subject, body):
    """Adds a notification for the order's customer. The caller commits."""
    if not order.user_id:
        return
    db.session.add(Notification(
        user_id=order.user_id, channel="app", subject=subject[:200], body=body,
        order_id=order.id, link="/account/orders", is_read=False,
    ))
