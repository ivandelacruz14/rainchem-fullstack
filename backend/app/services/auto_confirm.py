"""The customer confirms that the item arrived. If they never do, it is confirmed for them after a few days.

There is no background worker, so this runs when the customer opens their orders and when the office opens
Delivery Management. It does nothing for orders that are not due yet."""
import time
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models import Order
from app.services.notify import notify_order

_last_full_run = 0.0


def _sweep(orders):
    now = datetime.utcnow()
    days = current_app.config.get("AUTO_CONFIRM_DAYS", 3)
    reminder_days = current_app.config.get("AUTO_CONFIRM_REMINDER_DAYS", 2)
    changed = False
    for order in orders:
        delivered = order.delivered_at
        if not delivered:
            continue
        if now >= delivered + timedelta(days=days):
            order.received_confirmed_at = now
            order.auto_confirmed = True
            notify_order(order, f"{order.order_number} was confirmed as received",
                         f"We confirmed this order for you because {days} days passed after delivery. "
                         "If something is wrong, you can still request a return or contact us.")
            changed = True
        elif order.received_reminder_at is None and now >= delivered + timedelta(days=reminder_days):
            order.received_reminder_at = now
            notify_order(order, f"Did you receive {order.order_number}?",
                         f"Please confirm in My Orders. If you do not, we will confirm it for you in {max(days - reminder_days, 1)} day(s).")
            changed = True
    if changed:
        db.session.commit()


def _due_query():
    return Order.query.filter(Order.status == "delivered", Order.received_confirmed_at.is_(None))


def sweep_user(user_id):
    _sweep(_due_query().filter(Order.user_id == user_id).all())


def sweep_all(min_gap_seconds=300):
    """For the office screens. Runs at most once every few minutes."""
    global _last_full_run
    if time.time() - _last_full_run < min_gap_seconds:
        return
    _last_full_run = time.time()
    _sweep(_due_query().all())
