"""Sales records: one spreadsheet row per product line of an order.

Rows are written from the order itself, inside the same database transaction that changes the order,
so they cannot drift from it and repeated payment events cannot create duplicates (one row per
order line, enforced by a unique key). Money is a snapshot of what was charged at the time."""
import csv
import io
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import event, func
from sqlalchemy.orm import Session

from app.extensions import db
from app.models import Order, OrderItem, Product, SalesRecord
from app.services import sales_analytics as dates

_registered = False
DIRTY_KEY = "sales_dirty_orders"
WRITING_KEY = "sales_writing"
CENT = Decimal("0.01")

FULFILLMENT = {
    "pending_confirmation": "Not yet processed", "confirmed": "Not yet shipped", "processing": "Preparing",
    "shipped": "Shipped", "delivered": "Delivered", "cancelled": "Cancelled",
}
STATE_LABELS = {
    "pending": "Pending", "completed": "Completed", "cancelled": "Cancelled", "refunded": "Refunded", "returned": "Returned",
}
OVERRIDABLE = ("sku", "category", "notes")


def _money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def sale_state(order):
    """pending: not paid yet. completed: paid and still standing. cancelled, refunded, returned: as they say."""
    if order.payment_status in ("refund_pending", "refunded"):
        return "refunded"
    if order.return_status == "approved":
        return "returned"
    if order.status == "cancelled":
        return "cancelled"
    if order.payment_status == "paid":
        return "completed"
    return "pending"


def _note(order):
    parts = []
    if order.status == "cancelled":
        parts.append("Order cancelled")
    if order.return_status != "none":
        parts.append(f"Return {order.return_status}" + (f": {order.return_reason}" if order.return_reason else ""))
    if order.payment_status == "refund_pending":
        parts.append("Refund pending")
    elif order.payment_status == "refunded":
        parts.append("Refunded")
    return "; ".join(parts)[:500] or None


def sync_order(session, order_id):
    order = session.get(Order, order_id)
    if order is None:
        return
    items = session.query(OrderItem).filter_by(order_id=order.id).order_by(OrderItem.id).all()
    if not items:
        return
    products = {p.id: p for p in session.query(Product).filter(Product.id.in_([i.product_id for i in items if i.product_id])).all()}
    existing = {r.order_item_id: r for r in session.query(SalesRecord).filter_by(order_id=order.id).all()}

    lines = [_money(i.unit_price) * i.quantity for i in items]
    shipping, total_lines = _money(order.shipping_fee), sum(lines) or Decimal(1)
    shares, allocated = [], Decimal(0)
    for index, line in enumerate(lines):
        share = (shipping - allocated) if index == len(lines) - 1 else _money(shipping * line / total_lines)
        shares.append(share)
        allocated += share

    state = sale_state(order)
    for item, line_total, share in zip(items, lines, shares):
        unit = _money(item.unit_price)
        rate = Decimal(item.discount_rate or 0)
        list_unit = _money(unit / (Decimal(1) - rate)) if rate < 1 else unit
        subtotal = list_unit * item.quantity
        discount = max(subtotal - line_total, Decimal(0))
        product = products.get(item.product_id)
        record = existing.get(item.id)
        if record is None:
            record = SalesRecord(
                order_item_id=item.id, order_id=order.id, order_number=order.order_number, sold_at=order.created_at,
                sku=(product.sku or f"RC-{product.id:04d}") if product else None,
                category=product.category if product else None,
            )
            session.add(record)
        record.transaction_ref = (order.payment_reference or order.order_number)[:120]
        record.customer_id, record.customer_name = order.user_id, order.customer_name
        record.product_id, record.product_name = item.product_id, item.product_name
        record.quantity, record.list_unit_price, record.unit_price = item.quantity, list_unit, unit
        record.subtotal, record.discount_amount, record.line_total = subtotal, discount, line_total
        record.shipping_share, record.order_total = share, _money(order.total)
        record.payment_method, record.payment_status, record.order_status = order.payment_method, order.payment_status, order.status
        record.fulfillment_status = FULFILLMENT.get(order.status, order.status)
        record.refund_status = order.payment_status if order.payment_status in ("refund_pending", "refunded") else "none"
        record.return_status = order.return_status
        record.state = state
        record.notes = _note(order)
        for field, value in (record.overrides or {}).items():
            if field in OVERRIDABLE:
                setattr(record, field, value)


def sync_all(session=None):
    """Creates or refreshes the rows for every order. Safe to run any number of times."""
    session = session or db.session
    ids = [oid for (oid,) in session.query(Order.id).order_by(Order.id).all()]
    for oid in ids:
        sync_order(session, oid)
    session.commit()
    return len(ids)


def _collect(session, flush_context):
    if session.info.get(WRITING_KEY):  # the rows being written must not queue themselves again
        return
    dirty = session.info.setdefault(DIRTY_KEY, set())
    for obj in list(session.new) + list(session.dirty):
        if isinstance(obj, Order) and obj.id:
            dirty.add(obj.id)
        elif isinstance(obj, OrderItem) and obj.order_id:
            dirty.add(obj.order_id)


def _write(session):
    dirty = session.info.pop(DIRTY_KEY, set())
    if not dirty:
        return
    session.info[WRITING_KEY] = True
    try:
        for order_id in dirty:
            sync_order(session, order_id)
        session.flush()
    finally:
        session.info.pop(WRITING_KEY, None)
        session.info.pop(DIRTY_KEY, None)


def _forget(session):
    session.info.pop(DIRTY_KEY, None)


def register_events():
    global _registered
    if _registered:
        return
    event.listen(Session, "after_flush", _collect)
    event.listen(Session, "before_commit", _write)
    event.listen(Session, "after_rollback", _forget)
    _registered = True


# ---------------------------------------------------------------- queries

SORTS = {
    "date": SalesRecord.sold_at, "quantity": SalesRecord.quantity, "price": SalesRecord.unit_price,
    "total": SalesRecord.line_total, "order_total": SalesRecord.order_total,
    "customer": SalesRecord.customer_name, "product": SalesRecord.product_name,
}


def _window(start, end):
    offset = dates.utc_offset()
    return datetime.combine(start, time.min) - offset, datetime.combine(end + timedelta(days=1), time.min) - offset


def filtered_query(args):
    query = SalesRecord.query
    text = (args.get("q") or "").strip().lower()
    if text:
        like = f"%{text}%"
        query = query.filter(db.or_(*[
            func.lower(col).like(like) for col in
            (SalesRecord.order_number, SalesRecord.customer_name, SalesRecord.product_name, SalesRecord.sku, SalesRecord.transaction_ref)
        ]))
    if args.get("from") or args.get("to"):
        start = dates.parse_day(args.get("from"), "From date") if args.get("from") else datetime(2000, 1, 1).date()
        end = dates.parse_day(args.get("to"), "To date") if args.get("to") else dates.local_today()
        if end < start:
            raise dates.ReportError("The end date cannot be before the start date")
        lo, hi = _window(start, end)
        query = query.filter(SalesRecord.sold_at >= lo, SalesRecord.sold_at < hi)
    for arg, column in (("product_id", SalesRecord.product_id), ("category", SalesRecord.category),
                        ("payment_status", SalesRecord.payment_status), ("order_status", SalesRecord.order_status),
                        ("state", SalesRecord.state)):
        value = args.get(arg)
        if value not in (None, "", "all"):
            query = query.filter(column == (int(value) if arg == "product_id" else value))
    return query


def sorted_query(query, args):
    column = SORTS.get(args.get("sort"), SalesRecord.sold_at)
    descending = args.get("dir", "desc") != "asc"
    return query.order_by(column.desc() if descending else column.asc(), SalesRecord.id.desc() if descending else SalesRecord.id.asc())


def page_of(args):
    try:
        page = max(1, int(args.get("page", 1)))
        per_page = min(100, max(5, int(args.get("per_page", 25))))
    except ValueError:
        raise dates.ReportError("Page numbers must be whole numbers")
    return page, per_page


def totals_for(query):
    row = query.with_entities(
        func.count(SalesRecord.id), func.coalesce(func.sum(SalesRecord.quantity), 0), func.coalesce(func.sum(SalesRecord.subtotal), 0),
        func.coalesce(func.sum(SalesRecord.discount_amount), 0), func.coalesce(func.sum(SalesRecord.line_total), 0),
        func.coalesce(func.sum(SalesRecord.shipping_share), 0),
    ).one()
    return {"rows": int(row[0]), "units": int(row[1]), "subtotal": float(row[2]), "discounts": float(row[3]),
            "lineTotal": float(row[4]), "shipping": float(row[5])}


CSV_COLUMNS = [
    ("Record ID", "id"), ("Order", "orderNumber"), ("Transaction reference", "transactionRef"), ("Date and time (UTC)", "soldAt"),
    ("Customer ID", "customerId"), ("Customer", "customerName"), ("Product ID", "productId"), ("Product", "productName"),
    ("SKU", "sku"), ("Category", "category"), ("Quantity", "quantity"), ("List price", "listUnitPrice"), ("Unit price paid", "unitPrice"),
    ("Subtotal", "subtotal"), ("Discount", "discountAmount"), ("Line total", "lineTotal"), ("Shipping share", "shippingShare"),
    ("Tax", "taxAmount"), ("Order total", "orderTotal"), ("Payment method", "paymentMethod"), ("Payment status", "paymentStatus"),
    ("Order status", "orderStatus"), ("Fulfillment", "fulfillmentStatus"), ("Refund", "refundStatus"), ("Return", "returnStatus"),
    ("Sale state", "state"), ("Notes", "notes"),
]


def _safe_cell(value):
    """A cell that starts with = + - or @ would run as a formula in Excel, so it is shown as text."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return "" if value is None else value


def to_csv(rows):
    buffer = io.StringIO()
    buffer.write("\ufeff")  # lets Excel read the file as UTF-8
    writer = csv.writer(buffer)
    writer.writerow([name for name, _ in CSV_COLUMNS])
    for row in rows:
        data = row.to_dict()
        writer.writerow([_safe_cell(data.get(key)) for _, key in CSV_COLUMNS])
    return buffer.getvalue()


# ---------------------------------------------------------------- reports

def build_summary(start, end, granularity):
    if granularity not in dates.GRANULARITIES:
        raise dates.ReportError("Choose daily, weekly or monthly")
    lo, hi = _window(start, end)
    prev_start, prev_end = dates.previous_range(start, end)
    plo, phi = _window(prev_start, prev_end)
    rows = SalesRecord.query.filter(SalesRecord.sold_at >= lo, SalesRecord.sold_at < hi).all()
    previous = SalesRecord.query.filter(SalesRecord.sold_at >= plo, SalesRecord.sold_at < phi).all()

    def money(rs, attr):
        return float(sum((getattr(r, attr) for r in rs), Decimal(0)))

    by_state = defaultdict(list)
    for r in rows:
        by_state[r.state].append(r)
    happened = by_state["completed"] + by_state["refunded"] + by_state["returned"]
    gross, discounts = money(happened, "subtotal"), money(happened, "discount_amount")
    refunds = money(by_state["refunded"] + by_state["returned"], "line_total")
    summary = {
        "recordedRows": len(rows), "recordedValue": money(rows, "line_total"),
        "completedRows": len(by_state["completed"]), "completedValue": money(by_state["completed"], "line_total"),
        "units": sum(r.quantity for r in by_state["completed"]),
        "grossSales": round(gross, 2), "discounts": round(discounts, 2), "refunds": round(refunds, 2),
        "netSales": round(gross - discounts - refunds, 2),
        "pendingRows": len(by_state["pending"]), "pendingValue": money(by_state["pending"], "line_total"),
        "cancelledRows": len(by_state["cancelled"]), "cancelledValue": money(by_state["cancelled"], "line_total"),
        "refundedRows": len(by_state["refunded"]) + len(by_state["returned"]),
        "shippingCollected": money(by_state["completed"], "shipping_share"),
    }

    buckets, cursor = {}, dates.bucket_start(start, granularity)
    while cursor <= end:
        buckets[cursor] = {"net": Decimal(0), "units": 0}
        cursor = dates.next_bucket(cursor, granularity)
    for r in by_state["completed"]:
        b = buckets.get(dates.bucket_start(dates.to_local_date(r.sold_at), granularity))
        if b is not None:
            b["net"] += r.line_total
            b["units"] += r.quantity
    series = [{"start": d.isoformat(), "label": dates.bucket_label(d, granularity), "netSales": float(v["net"]), "units": v["units"]}
              for d, v in buckets.items()]

    def per_product(rs):
        out = defaultdict(lambda: {"units": 0, "net": Decimal(0), "name": ""})
        for r in rs:
            if r.state != "completed":
                continue
            key = r.product_id if r.product_id is not None else f"name:{r.product_name}"
            out[key]["units"] += r.quantity
            out[key]["net"] += r.line_total
            out[key]["name"] = r.product_name
        return out

    now, before = per_product(rows), per_product(previous)
    best = sorted(({"productId": k if isinstance(k, int) else None, "name": v["name"], "units": v["units"], "net": float(v["net"])}
                   for k, v in now.items()), key=lambda x: (-x["units"], -x["net"]))[:5]
    declining = []
    for key, old in before.items():
        new_units = now[key]["units"] if key in now else 0
        if old["units"] > 0 and new_units < old["units"]:
            declining.append({
                "productId": key if isinstance(key, int) else None, "name": old["name"],
                "previousUnits": old["units"], "units": new_units,
                "changePercent": round((new_units - old["units"]) / old["units"] * 100, 1),
            })
    declining.sort(key=lambda x: x["changePercent"])
    return {
        "range": {"start": start.isoformat(), "end": end.isoformat(), "previousStart": prev_start.isoformat(),
                  "previousEnd": prev_end.isoformat(), "granularity": granularity},
        "summary": summary, "series": series, "bestSelling": best, "declining": declining[:5],
        "definitions": {
            "completed": "Paid orders that were not cancelled, refunded or returned.",
            "grossSales": "List price of completed, refunded and returned lines, before discounts.",
            "netSales": "Gross sales minus discounts minus refunds and returns. Shipping fees and tax are not included, and this is not profit.",
        },
    }
