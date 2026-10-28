"""The customer-facing journey of an order, built only from what is stored in the database.

Milestones follow the real workflow (pending_confirmation, confirmed, processing, shipped,
delivered, cancelled). Nothing is estimated or invented: a milestone shows a time only when
the database has an event for it, and a stage is never shown as reached before its status is."""

MILESTONES = [
    ("received", "Order Received"),
    ("verification", "Order Verification"),
    ("approved", "Order Approved"),
    ("preparing", "Preparing Your Products"),
    ("in_transit", "In Transit"),
    ("delivered", "Delivered"),
]

# The milestone an order is "at" for each status.
STAGE_FOR_STATUS = {
    "pending_confirmation": 1,
    "confirmed": 2,
    "processing": 3,
    "shipped": 4,
    "delivered": 5,
}

RETURN_ALERTS = {
    "requested": ("Return requested", "Your return request was sent and is waiting for review."),
    "approved": ("Return approved", "Your return request was approved."),
    "rejected": ("Return rejected", "Your return request was not approved."),
}


def _iso(value):
    return value.isoformat() if value else None


def _history_times(order):
    times = {}
    for entry in order.history:
        if entry.changed_at and (entry.status not in times or entry.changed_at > times[entry.status]):
            times[entry.status] = entry.changed_at
    return times


def _description(key, state, order):
    destination = ", ".join(p for p in (order.address_city, order.address_province) if p)
    online = order.is_online_payment
    if key == "received":
        return f"Order {order.order_number} was placed."
    if key == "verification":
        if state == "done":
            return "The order details and payment were checked."
        if online and order.payment_status == "unpaid":
            return "Waiting for your payment. Pay for the order so it can be verified."
        if online and order.payment_status == "verifying":
            return "We are verifying your payment."
        if online and order.payment_status == "paid":
            return "Payment received. Waiting for approval."
        return "Our team is checking your order details."
    if key == "approved":
        return {"done": "The order was approved for processing.",
                "current": "Your order is approved and waiting to be prepared."}.get(state, "Waiting for approval.")
    if key == "preparing":
        return {"done": "Your products were prepared.",
                "current": "Your products are being prepared."}.get(state, "Your products will be prepared after approval.")
    if key == "in_transit":
        where = f" to {destination}" if destination else ""
        return {"done": f"Your order was sent out for delivery{where}.",
                "current": f"Your order is on its way{where}."}.get(state, "Waiting to be sent out for delivery.")
    return {"done": "Your order was delivered."}.get(state, "Waiting for delivery.")


def build_journey(order):
    times = _history_times(order)
    cancelled = order.status == "cancelled"

    if cancelled:
        reached = [STAGE_FOR_STATUS[s] for s in times if s in STAGE_FOR_STATUS]
        stage = max(reached) if reached else 1
    else:
        stage = STAGE_FOR_STATUS.get(order.status, 1)
    delivered = order.status == "delivered"

    moments = {
        "received": order.created_at,
        "verification": order.paid_at or order.payment_submitted_at if order.is_online_payment else None,
        "approved": order.confirmed_at or times.get("confirmed"),
        "preparing": times.get("processing"),
        "in_transit": times.get("shipped"),
        "delivered": times.get("delivered"),
    }

    milestones = []
    for index, (key, title) in enumerate(MILESTONES):
        if key == "received":
            state = "done"
        elif delivered:
            state = "done"
        elif index < stage:
            state = "done"
        elif index == stage:
            state = "stopped" if cancelled else "current"
        else:
            state = "upcoming"
        milestones.append({
            "key": key, "title": title, "state": state,
            "description": _description(key, state, order),
            "at": _iso(moments[key]) if state in ("done", "current", "stopped") else None,
        })

    alerts = []
    if cancelled:
        alerts.append({
            "kind": "cancelled", "title": "Order cancelled",
            "message": "This order was cancelled and will not be delivered.",
            "at": _iso(order.cancelled_at or times.get("cancelled")),
        })
    elif order.is_online_payment and order.status == "pending_confirmation" and order.payment_status == "unpaid":
        alerts.append({"kind": "payment", "title": "Payment needed",
                       "message": "Your order cannot be verified until the payment is completed.", "at": None})
    elif order.payment_status == "verifying":
        alerts.append({"kind": "payment", "title": "Verifying your payment",
                       "message": "We received your payment details and are checking them.",
                       "at": _iso(order.payment_submitted_at)})
    if order.payment_status == "refund_pending":
        alerts.append({"kind": "refund", "title": "Refund pending",
                       "message": "Your refund is being processed.", "at": None})
    elif order.payment_status == "refunded":
        alerts.append({"kind": "refund", "title": "Refunded", "message": "Your payment was refunded.", "at": None})
    if order.return_status in RETURN_ALERTS:
        title, message = RETURN_ALERTS[order.return_status]
        alerts.append({"kind": "return", "title": title, "message": message, "at": _iso(order.return_requested_at)})

    if cancelled:
        headline = "Cancelled"
    elif delivered:
        headline = "Delivered"
    else:
        headline = MILESTONES[stage][1]

    events = [order.created_at, order.paid_at, order.payment_submitted_at, order.confirmed_at,
              order.cancelled_at, order.return_requested_at, *times.values()]
    latest = max((e for e in events if e), default=None)

    return {
        "state": "cancelled" if cancelled else "completed" if delivered else "in_progress",
        "headline": headline,
        "stageNumber": (len(MILESTONES) if delivered else stage + 1),
        "stageCount": len(MILESTONES),
        "milestones": milestones,
        "alerts": alerts,
        "updatedAt": _iso(latest),
    }
