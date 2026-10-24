"""Sales reporting built only from recorded orders.

Recorded sales are order lines on orders that have been confirmed or moved
further along (confirmed, processing, shipped, delivered), excluding orders
whose return was approved. Dates use the shop's local time (UTC offset from
SALES_UTC_OFFSET_HOURS, default +8 for the Philippines), taken from the order
creation time. Anything under "forecast" or "recommendations" is an estimate
derived from those records, not a recorded figure.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from statistics import pstdev

from flask import current_app

from app.extensions import db
from app.models import Order, OrderItem, Product

SALE_STATUSES = ("confirmed", "processing", "shipped", "delivered")
GRANULARITIES = ("daily", "weekly", "monthly")
MAX_RANGE_DAYS = 732
LEGACY_SERVICE_CATEGORY = "Services"

RESTOCK_WINDOW_DAYS = 28
RESTOCK_COVER_DAYS = 14
FORECAST_HISTORY_WEEKS = 8
FORECAST_HORIZON_WEEKS = 4
FORECAST_MIN_WEEKS_WITH_SALES = 3
FORECAST_MIN_UNITS = 5


class RangeError(ValueError):
    pass


def _offset():
    return timedelta(hours=current_app.config.get("SALES_UTC_OFFSET_HOURS", 8))


def local_today():
    return (datetime.utcnow() + _offset()).date()


def month_start(day):
    return day.replace(day=1)


def week_start(day):
    return day - timedelta(days=day.weekday())


def bucket_start(day, granularity):
    if granularity == "weekly":
        return week_start(day)
    if granularity == "monthly":
        return month_start(day)
    return day


def next_bucket(day, granularity):
    if granularity == "weekly":
        return day + timedelta(days=7)
    if granularity == "monthly":
        return (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return day + timedelta(days=1)


def bucket_label(day, granularity):
    if granularity == "monthly":
        return day.strftime("%b %Y")
    if granularity == "weekly":
        return "Wk of " + day.strftime("%b %d")
    return day.strftime("%b %d")


def resolve_range(granularity, start_raw, end_raw):
    if granularity not in GRANULARITIES:
        raise RangeError("granularity must be daily, weekly or monthly")
    today = local_today()
    try:
        end = date.fromisoformat(end_raw) if end_raw else today
        if start_raw:
            start = date.fromisoformat(start_raw)
        elif granularity == "weekly":
            start = week_start(end) - timedelta(weeks=11)
        elif granularity == "monthly":
            first = month_start(end)
            start = first
            for _ in range(11):
                start = month_start(start - timedelta(days=1))
        else:
            start = end - timedelta(days=29)
    except ValueError:
        raise RangeError("Dates must be in YYYY-MM-DD format")
    if start > end:
        raise RangeError("The start date must be on or before the end date")
    if (end - start).days > MAX_RANGE_DAYS:
        raise RangeError("The date range is limited to two years")
    return start, end


def _money(value):
    return Decimal(str(value or 0))


def fetch_lines(start, end, owner_admin_id=None, product_id=None):
    """Recorded sale lines between two local dates, inclusive."""
    offset = _offset()
    start_utc = datetime.combine(start, datetime.min.time()) - offset
    end_utc = datetime.combine(end + timedelta(days=1), datetime.min.time()) - offset

    query = (
        db.session.query(
            Order.id, Order.created_at, OrderItem.product_id, OrderItem.product_name,
            OrderItem.quantity, OrderItem.unit_price,
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .filter(
            Order.status.in_(SALE_STATUSES),
            Order.return_status != "approved",
            Order.created_at >= start_utc,
            Order.created_at < end_utc,
        )
    )
    if owner_admin_id is not None:
        query = query.join(Product, Product.id == OrderItem.product_id).filter(
            Product.owner_admin_id == owner_admin_id
        )
    if product_id is not None:
        query = query.filter(OrderItem.product_id == product_id)

    lines = []
    for order_id, created_at, pid, name, qty, unit_price in query.all():
        lines.append({
            "orderId": order_id,
            "day": (created_at + offset).date(),
            "productId": pid,
            "name": name,
            "units": int(qty),
            "revenue": _money(unit_price) * int(qty),
        })
    return lines


def summarize(lines):
    revenue = sum((l["revenue"] for l in lines), Decimal(0))
    orders = len({l["orderId"] for l in lines})
    return {
        "revenue": float(round(revenue, 2)),
        "unitsSold": sum(l["units"] for l in lines),
        "orders": orders,
        "averageOrderValue": float(round(revenue / orders, 2)) if orders else 0.0,
    }


def build_series(lines, start, end, granularity):
    buckets = {}
    cursor = bucket_start(start, granularity)
    while cursor <= end:
        buckets[cursor] = {"revenue": Decimal(0), "units": 0, "orders": set()}
        cursor = next_bucket(cursor, granularity)
    for line in lines:
        slot = buckets.get(bucket_start(line["day"], granularity))
        if slot is None:
            continue
        slot["revenue"] += line["revenue"]
        slot["units"] += line["units"]
        slot["orders"].add(line["orderId"])
    return [
        {
            "label": bucket_label(day, granularity),
            "start": day.isoformat(),
            "revenue": float(round(slot["revenue"], 2)),
            "units": slot["units"],
            "orders": len(slot["orders"]),
        }
        for day, slot in buckets.items()
    ]


def _percent_change(current, previous):
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def _group_by_product(lines):
    grouped = {}
    for line in lines:
        key = line["productId"] if line["productId"] is not None else f"name:{line['name']}"
        entry = grouped.setdefault(key, {
            "productId": line["productId"], "name": line["name"],
            "units": 0, "revenue": Decimal(0), "orders": set(),
        })
        entry["units"] += line["units"]
        entry["revenue"] += line["revenue"]
        entry["orders"].add(line["orderId"])
    return grouped


def catalog_products(owner_admin_id=None):
    query = Product.query.filter(Product.category != LEGACY_SERVICE_CATEGORY)
    if owner_admin_id is not None:
        query = query.filter(Product.owner_admin_id == owner_admin_id)
    return query.all()


def product_table(lines, previous_lines, catalog):
    current = _group_by_product(lines)
    previous = _group_by_product(previous_lines)
    total_revenue = sum((e["revenue"] for e in current.values()), Decimal(0))
    stock_by_id = {p.id: p for p in catalog}

    rows = []
    seen = set()
    for key, entry in current.items():
        seen.add(key)
        prev = previous.get(key)
        product = stock_by_id.get(entry["productId"])
        rows.append({
            "productId": entry["productId"],
            "name": entry["name"],
            "category": product.category if product else None,
            "stock": product.stock if product else None,
            "units": entry["units"],
            "revenue": float(round(entry["revenue"], 2)),
            "orders": len(entry["orders"]),
            "share": float(round(entry["revenue"] / total_revenue * 100, 1)) if total_revenue else 0.0,
            "previousUnits": prev["units"] if prev else 0,
            "previousRevenue": float(round(prev["revenue"], 2)) if prev else 0.0,
            "unitsChange": _percent_change(entry["units"], prev["units"] if prev else 0),
        })
    for product in catalog:
        if product.id in seen:
            continue
        prev = previous.get(product.id)
        rows.append({
            "productId": product.id, "name": product.name, "category": product.category,
            "stock": product.stock, "units": 0, "revenue": 0.0, "orders": 0, "share": 0.0,
            "previousUnits": prev["units"] if prev else 0,
            "previousRevenue": float(round(prev["revenue"], 2)) if prev else 0.0,
            "unitsChange": _percent_change(0, prev["units"]) if prev else None,
        })
    rows.sort(key=lambda r: (-r["revenue"], -r["units"], r["name"]))
    return rows


def best_and_lowest(rows):
    sold = [r for r in rows if r["units"] > 0]
    if not sold:
        return None, None
    by_units = sorted(sold, key=lambda r: (-r["units"], -r["revenue"]))
    best = by_units[0]
    lowest = by_units[-1] if len(by_units) > 1 else None
    return best, lowest


def recommendations(rows, owner_admin_id=None):
    """Rule-based suggestions. Each one states the figures it is based on."""
    items = []
    sold = [r for r in rows if r["units"] > 0]

    for row in sorted(sold, key=lambda r: -r["revenue"])[:3]:
        items.append({
            "type": "prioritize", "productId": row["productId"], "name": row["name"],
            "message": f"Recorded {row['units']} units and {row['share']}% of revenue in the selected period.",
        })

    today = local_today()
    window_start = today - timedelta(days=RESTOCK_WINDOW_DAYS - 1)
    recent = _group_by_product(fetch_lines(window_start, today, owner_admin_id))
    for product in catalog_products(owner_admin_id):
        entry = recent.get(product.id)
        if not entry:
            continue
        daily_rate = entry["units"] / RESTOCK_WINDOW_DAYS
        cover_days = product.stock / daily_rate if daily_rate else None
        if cover_days is not None and cover_days < RESTOCK_COVER_DAYS:
            items.append({
                "type": "restock", "productId": product.id, "name": product.name,
                "message": (
                    f"{product.stock} in stock; sold {entry['units']} units in the last "
                    f"{RESTOCK_WINDOW_DAYS} days. At that pace stock lasts about {round(cover_days)} days."
                ),
            })

    for row in rows:
        if row["units"] == 0 and (row["stock"] or 0) > 0 and row["previousUnits"] == 0:
            items.append({
                "type": "promote", "productId": row["productId"], "name": row["name"],
                "message": "No recorded sales in this period or the one before it. Consider a promotion or better placement.",
            })
        elif row["previousUnits"] >= 3 and row["unitsChange"] is not None and row["unitsChange"] <= -30:
            items.append({
                "type": "attention", "productId": row["productId"], "name": row["name"],
                "message": f"Units sold fell {abs(row['unitsChange'])}% against the previous period ({row['previousUnits']} to {row['units']}).",
            })
    return items


def forecast(owner_admin_id=None):
    """Next-weeks demand estimate from weekly history. Not a guarantee."""
    this_week = week_start(local_today())
    history_start = this_week - timedelta(weeks=FORECAST_HISTORY_WEEKS)
    history_end = this_week - timedelta(days=1)
    lines = fetch_lines(history_start, history_end, owner_admin_id)

    weekly = defaultdict(lambda: defaultdict(int))
    totals = defaultdict(lambda: {"units": 0, "revenue": Decimal(0)})
    for line in lines:
        if line["productId"] is None:
            continue
        weekly[line["productId"]][week_start(line["day"])] += line["units"]
        totals[line["productId"]]["units"] += line["units"]
        totals[line["productId"]]["revenue"] += line["revenue"]

    week_starts = [history_start + timedelta(weeks=i) for i in range(FORECAST_HISTORY_WEEKS)]
    results = []
    expected_revenue = Decimal(0)
    for product in catalog_products(owner_admin_id):
        series = [weekly[product.id].get(w, 0) for w in week_starts]
        weeks_with_sales = sum(1 for v in series if v > 0)
        total_units = sum(series)
        entry = {
            "productId": product.id, "name": product.name, "stock": product.stock,
            "weeklyHistory": series,
        }
        if weeks_with_sales < FORECAST_MIN_WEEKS_WITH_SALES or total_units < FORECAST_MIN_UNITS:
            entry.update({"sufficientData": False, "confidence": None})
            results.append(entry)
            continue

        recent = series[-4:]
        weights = [1, 2, 3, 4]
        per_week = sum(v * w for v, w in zip(recent, weights)) / sum(weights)
        spread = pstdev(series)
        expected_units = round(per_week * FORECAST_HORIZON_WEEKS)
        low = max(0, round((per_week - spread) * FORECAST_HORIZON_WEEKS))
        high = round((per_week + spread) * FORECAST_HORIZON_WEEKS)
        avg_price = totals[product.id]["revenue"] / totals[product.id]["units"]
        expected_revenue += avg_price * expected_units
        entry.update({
            "sufficientData": True,
            "confidence": "moderate" if weeks_with_sales >= 6 else "low",
            "expectedUnits": expected_units,
            "lowUnits": low,
            "highUnits": high,
            "needsRestock": product.stock < expected_units,
        })
        results.append(entry)

    results.sort(key=lambda r: (not r["sufficientData"], -(r.get("expectedUnits") or 0), r["name"]))
    return {
        "isEstimate": True,
        "horizonWeeks": FORECAST_HORIZON_WEEKS,
        "historyWeeks": FORECAST_HISTORY_WEEKS,
        "weekLabels": [bucket_label(w, "weekly") for w in week_starts],
        "method": (
            "Weighted average of the last four complete weeks of recorded sales, "
            "with the range based on week-to-week variation. Products need sales in at "
            f"least {FORECAST_MIN_WEEKS_WITH_SALES} of the last {FORECAST_HISTORY_WEEKS} weeks "
            f"and {FORECAST_MIN_UNITS} units to be estimated."
        ),
        "expectedRevenue": float(round(expected_revenue, 2)),
        "products": results,
    }


def build_report(granularity, start, end, owner_admin_id=None):
    lines = fetch_lines(start, end, owner_admin_id)
    span = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=span - 1)
    previous_lines = fetch_lines(previous_start, previous_end, owner_admin_id)

    summary = summarize(lines)
    previous_summary = summarize(previous_lines)
    rows = product_table(lines, previous_lines, catalog_products(owner_admin_id))
    best, lowest = best_and_lowest(rows)

    return {
        "granularity": granularity,
        "range": {"start": start.isoformat(), "end": end.isoformat(), "days": span},
        "previousRange": {"start": previous_start.isoformat(), "end": previous_end.isoformat()},
        "summary": summary,
        "previousSummary": previous_summary,
        "change": {
            "revenue": _percent_change(summary["revenue"], previous_summary["revenue"]),
            "unitsSold": _percent_change(summary["unitsSold"], previous_summary["unitsSold"]),
            "orders": _percent_change(summary["orders"], previous_summary["orders"]),
        },
        "series": build_series(lines, start, end, granularity),
        "products": rows,
        "bestSeller": best,
        "lowestSeller": lowest,
        "recommendations": recommendations(rows, owner_admin_id),
        "forecast": forecast(owner_admin_id),
        "basis": "Recorded sales: confirmed, processing, shipped and delivered orders, excluding approved returns.",
    }


def build_product_history(product, granularity, start, end):
    lines = fetch_lines(start, end, product_id=product.id)
    return {
        "product": {"id": product.id, "name": product.name, "stock": product.stock, "price": float(product.price)},
        "granularity": granularity,
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "summary": summarize(lines),
        "series": build_series(lines, start, end, granularity),
    }
