"""Stock history and rule-based checks.

Every change to Product.stock is written to inventory_movements together with why it happened. The
sum of a product's movements is its expected stock; a gap between that and the recorded stock is
flagged for an administrator. The checks are plain rules (no machine learning), and they never
change stock or financial records by themselves."""
from contextlib import contextmanager
from datetime import datetime

from flask import g, has_request_context
from sqlalchemy import case, event, func
from sqlalchemy.orm import object_session

from app.extensions import db
from app.models import (
    InventoryAlert, InventoryMovement, Order, OrderStatusHistory, Product, SalesRecord,
)

try:
    from sqlalchemy.orm.base import NEVER_SET, NO_VALUE
except ImportError:  # pragma: no cover
    from sqlalchemy.orm.attributes import NEVER_SET, NO_VALUE

_registered = False
STACK_KEY = "stock_context"
ISSUE_TYPES = ("sale",)
RESTORE_TYPES = ("cancel_restore", "return")


@contextmanager
def stock_context(movement_type, order=None, reason=None, admin=None, reference=None, record=True):
    """Says why stock is about to change, so the movement is recorded with the right meaning.
    record=False is for a correction that puts the stock back in line with its history: the change is
    kept in the audit log instead of being added to the history a second time."""
    stack = db.session().info.setdefault(STACK_KEY, [])
    stack.append({"type": movement_type, "order_id": getattr(order, "id", None), "reason": reason,
                  "admin": admin, "reference": reference, "record": record})
    try:
        yield
    finally:
        stack.pop()


def _context(session):
    stack = session.info.get(STACK_KEY) or []
    return stack[-1] if stack else None


def _actor(ctx):
    admin = (ctx or {}).get("admin")
    if admin is None and has_request_context():
        admin = getattr(g, "admin", None)
    return (admin.id, admin.name) if admin else (None, "System")


def _on_stock_set(target, value, oldvalue, initiator):
    if oldvalue in (None, NO_VALUE, NEVER_SET):
        return
    try:
        delta = int(value) - int(oldvalue)
    except (TypeError, ValueError):
        return
    session = object_session(target)
    if delta == 0 or session is None or target.id is None:
        return
    ctx = _context(session)
    if ctx and not ctx.get("record", True):
        return
    actor_id, actor_name = _actor(ctx)
    session.add(InventoryMovement(
        product_id=target.id, product_name=target.name,
        movement_type=ctx["type"] if ctx else "untracked", quantity_change=delta,
        order_id=ctx["order_id"] if ctx else None, reference=ctx["reference"] if ctx else None,
        reason=ctx["reason"] if ctx else None, actor_admin_id=actor_id, actor_name=actor_name,
    ))


def _on_product_insert(mapper, connection, target):
    quantity = int(target.stock or 0)
    if quantity == 0:
        return
    session = object_session(target)
    ctx = _context(session) if session is not None else None
    actor_id, actor_name = _actor(ctx)
    connection.execute(InventoryMovement.__table__.insert().values(
        product_id=target.id, product_name=target.name, movement_type=(ctx or {}).get("type", "opening"),
        quantity_change=quantity, reason=(ctx or {}).get("reason") or "Stock when the product was added",
        actor_admin_id=actor_id, actor_name=actor_name, created_at=datetime.utcnow(),
    ))


def register_events():
    global _registered
    if _registered:
        return
    event.listen(Product.stock, "set", _on_stock_set, active_history=True)
    event.listen(Product, "after_insert", _on_product_insert)
    _registered = True


def ensure_baseline():
    """Products with stock but no history get an opening movement equal to today's stock, so the
    history starts balanced. Earlier orders are not replayed; only changes from now on are tracked."""
    with_history = {pid for (pid,) in db.session.query(InventoryMovement.product_id).distinct() if pid}
    created = 0
    for product in Product.query.filter(Product.category != "Services").all():
        if product.id in with_history or not product.stock:
            continue
        db.session.add(InventoryMovement(
            product_id=product.id, product_name=product.name, movement_type="opening",
            quantity_change=int(product.stock), reason="Baseline recorded when stock tracking was turned on",
            actor_name="System",
        ))
        created += 1
    if created:
        db.session.commit()
    return created


def expected_stock():
    rows = db.session.query(InventoryMovement.product_id, func.coalesce(func.sum(InventoryMovement.quantity_change), 0)) \
        .filter(InventoryMovement.product_id.isnot(None)).group_by(InventoryMovement.product_id).all()
    return {pid: int(total) for pid, total in rows}


def stock_overview():
    """One row per product: how the expected stock is made up and how it compares with the recorded stock."""
    expected = expected_stock()
    parts = {}
    for pid, mtype, total in db.session.query(
        InventoryMovement.product_id, InventoryMovement.movement_type, func.sum(InventoryMovement.quantity_change)
    ).filter(InventoryMovement.product_id.isnot(None)).group_by(InventoryMovement.product_id, InventoryMovement.movement_type):
        parts.setdefault(pid, {})[mtype] = int(total)
    rows = []
    for product in Product.query.filter(Product.category != "Services").order_by(Product.name).all():
        p = parts.get(product.id, {})
        exp = expected.get(product.id, 0)
        rows.append({
            "productId": product.id, "name": product.name, "sku": product.sku,
            "opening": p.get("opening", 0), "received": p.get("received", 0),
            "issued": -p.get("sale", 0), "returned": p.get("return", 0) + p.get("cancel_restore", 0),
            "adjusted": p.get("adjustment", 0) + p.get("write_off", 0) + p.get("untracked", 0),
            "expected": exp, "recorded": product.stock, "difference": product.stock - exp,
        })
    return rows


def _new_alert(fingerprint, category, explanation, product=None, order=None, expected=None, recorded=None, difference=None):
    if InventoryAlert.query.filter_by(fingerprint=fingerprint).first():
        return None
    alert = InventoryAlert(
        fingerprint=fingerprint[:190], category=category, explanation=explanation,
        product_id=product.id if product else None, product_name=product.name if product else None,
        order_id=order.id if order else None, order_number=order.order_number if order else None,
        expected_value=None if expected is None else str(expected), recorded_value=None if recorded is None else str(recorded),
        difference=None if difference is None else str(difference), status="open",
    )
    db.session.add(alert)
    return alert


def run_scan():
    """Looks for the conditions below and records a new alert for each one not already on file."""
    ensure_baseline()
    created = []

    def add(*args, **kwargs):
        alert = _new_alert(*args, **kwargs)
        if alert is not None:
            created.append(alert)

    products = {p.id: p for p in Product.query.filter(Product.category != "Services").all()}
    expected = expected_stock()

    for pid, product in products.items():
        exp = expected.get(pid, 0)
        if product.stock != exp:
            diff = product.stock - exp
            add(f"stock_mismatch:{pid}:{exp}:{product.stock}", "stock_mismatch",
                f"Inventory discrepancy detected: expected stock is {exp} units, but the recorded stock is "
                f"{product.stock} units. Difference: {diff:+d} units. Review the stock movement history before applying a correction.",
                product=product, expected=exp, recorded=product.stock, difference=diff)
        if product.stock < 0:
            add(f"negative_stock:{pid}:{product.stock}", "negative_stock",
                f"{product.name} has {product.stock} units recorded. Stock should not be below zero. "
                "Check for orders accepted without enough stock or for a wrong manual change.",
                product=product, expected="0 or more", recorded=product.stock, difference=product.stock)

    duplicates = db.session.query(
        InventoryMovement.movement_type, InventoryMovement.order_id, InventoryMovement.product_id, func.count(InventoryMovement.id)
    ).filter(InventoryMovement.order_id.isnot(None), InventoryMovement.movement_type.in_(ISSUE_TYPES + RESTORE_TYPES)) \
     .group_by(InventoryMovement.movement_type, InventoryMovement.order_id, InventoryMovement.product_id) \
     .having(func.count(InventoryMovement.id) > 1).all()
    for mtype, order_id, pid, count in duplicates:
        order, product = db.session.get(Order, order_id), products.get(pid)
        add(f"duplicate_movement:{mtype}:{order_id}:{pid}:{count}", "duplicate_movement",
            f"The same stock movement ({mtype.replace('_', ' ')}) was recorded {count} times for order "
            f"{order.order_number if order else order_id}. It should normally happen once for each product in an order.",
            product=product, order=order, expected=1, recorded=count, difference=count - 1)

    twice = db.session.query(OrderStatusHistory.order_id, OrderStatusHistory.status, func.count(OrderStatusHistory.id)) \
        .group_by(OrderStatusHistory.order_id, OrderStatusHistory.status).having(func.count(OrderStatusHistory.id) > 1).all()
    for order_id, status, count in twice:
        order = db.session.get(Order, order_id)
        add(f"order_twice:{order_id}:{status}:{count}", "order_processed_twice",
            f"Order {order.order_number if order else order_id} moved to \"{status}\" {count} times. "
            "An order should reach each status once. Check whether a button or payment event ran twice.",
            order=order, expected=1, recorded=count, difference=count - 1)

    for order in Order.query.filter(Order.payment_status == "paid").all():
        if order.is_online_payment and not (order.payment_reference or "").strip():
            add(f"paid_no_reference:{order.id}", "paid_without_reference",
                f"Order {order.order_number} is marked paid by {order.payment_method} but has no payment reference, "
                "so the payment cannot be traced to the payment provider.",
                order=order, expected="A payment reference", recorded="None")

    net = {}
    for order_id, pid, total, issued in db.session.query(
        InventoryMovement.order_id, InventoryMovement.product_id, func.sum(InventoryMovement.quantity_change),
        func.sum(case((InventoryMovement.movement_type == "sale", func.abs(InventoryMovement.quantity_change)), else_=0)),
    ).filter(InventoryMovement.order_id.isnot(None)).group_by(InventoryMovement.order_id, InventoryMovement.product_id):
        net[(order_id, pid)] = (int(total), int(issued or 0))
    for (order_id, pid), (total, issued) in net.items():
        order = db.session.get(Order, order_id)
        if order is None or not issued:
            continue
        if (order.status == "cancelled" or order.return_status == "approved") and total != 0:
            product = products.get(pid)
            reason = "cancelled" if order.status == "cancelled" else "returned"
            add(f"no_restore:{order_id}:{pid}:{total}", "cancelled_no_restore",
                f"Order {order.order_number} was {reason}, so the {issued} units issued should have been put back, "
                f"but the net stock movement for this order is {total:+d}. Check whether the stock was restored.",
                product=product, order=order, expected=0, recorded=total, difference=total)

    for movement in InventoryMovement.query.filter(InventoryMovement.movement_type.in_(("adjustment", "write_off"))).all():
        problems = []
        if not (movement.reason or "").strip():
            problems.append("has no explanation")
        if movement.actor_admin_id is None:
            problems.append("was not made by a signed-in administrator")
        if problems:
            add(f"adjustment:{movement.id}", "adjustment_unexplained",
                f"A stock {movement.movement_type.replace('_', ' ')} of {movement.quantity_change:+d} units on "
                f"{movement.product_name} " + " and ".join(problems) + ". Adjustments need a reason and an authorised person.",
                product=products.get(movement.product_id), expected="A reason and an administrator",
                recorded="; ".join(problems), difference=movement.quantity_change)

    for movement in InventoryMovement.query.filter_by(movement_type="untracked").all():
        add(f"untracked:{movement.id}", "untracked_change",
            f"Stock of {movement.product_name} changed by {movement.quantity_change:+d} units without a recorded process "
            "(not an order, return, adjustment or approved edit). Find out who or what changed it.",
            product=products.get(movement.product_id), expected="A recorded process", recorded="None", difference=movement.quantity_change)

    for finding in _sales_record_findings():
        add(*finding[0], **finding[1])

    db.session.commit()
    return created


def _sales_record_findings():
    totals = {
        oid: (int(count), subtotal, shipping)
        for oid, count, subtotal, shipping in db.session.query(
            SalesRecord.order_id, func.count(SalesRecord.id), func.sum(SalesRecord.line_total), func.sum(SalesRecord.shipping_share)
        ).group_by(SalesRecord.order_id)
    }
    from app.models import OrderItem
    item_counts = dict(db.session.query(OrderItem.order_id, func.count(OrderItem.id)).group_by(OrderItem.order_id).all())
    findings = []
    for order in Order.query.order_by(Order.id.desc()).limit(5000).all():
        count, line_sum, ship_sum = totals.get(order.id, (0, 0, 0))
        wanted = item_counts.get(order.id, 0)
        if count != wanted:
            findings.append(((f"sales_rows:{order.id}:{wanted}:{count}", "sales_record_mismatch",
                              f"Order {order.order_number} has {wanted} product line(s) but {count} sales record row(s).",),
                             dict(order=order, expected=wanted, recorded=count, difference=count - wanted)))
            continue
        recorded_total = float((line_sum or 0) + (ship_sum or 0))
        if abs(recorded_total - float(order.total)) > 0.01:
            findings.append(((f"sales_total:{order.id}:{float(order.total):.2f}:{recorded_total:.2f}", "sales_record_mismatch",
                              f"Order {order.order_number} totals PHP {float(order.total):.2f}, but its sales records add up to "
                              f"PHP {recorded_total:.2f}.",),
                             dict(order=order, expected=f"{float(order.total):.2f}", recorded=f"{recorded_total:.2f}",
                                  difference=f"{recorded_total - float(order.total):+.2f}")))
    return findings


def still_applies(alert):
    """For stock alerts: does the condition still exist right now? None when that cannot be checked."""
    if alert.product_id is None:
        return None
    product = db.session.get(Product, alert.product_id)
    if product is None:
        return False
    if alert.category == "stock_mismatch":
        return product.stock != expected_stock().get(product.id, 0)
    if alert.category == "negative_stock":
        return product.stock < 0
    return None


def record_movement(product, movement_type, quantity, reason, admin, order=None):
    """A deliberate stock change by an administrator (stock received, damage, a correction)."""
    with stock_context(movement_type, order=order, reason=reason, admin=admin):
        product.stock = int(product.stock) + int(quantity)
