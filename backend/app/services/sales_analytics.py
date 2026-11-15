"""Sales reporting built only from recorded orders.

A recorded sale is an order that the shop confirmed and that was not cancelled,
returned or refunded. Dates are grouped in the shop's local time
(STORE_UTC_OFFSET_HOURS). Revenue is merchandise revenue: shipping fees are not included.
Forecasts are labelled estimates and are only produced when enough history exists.
"""
import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from flask import current_app

from app.extensions import db
from app.models import Order, OrderItem, Product

SALE_STATUSES = ("confirmed", "processing", "shipped", "delivered")
NOT_A_SALE_PAYMENT_STATES = ("refund_pending", "refunded")
GRANULARITIES = ("daily", "weekly", "monthly")
MAX_RANGE_DAYS = 366

LOOKBACK_WEEKS = 8
MIN_HISTORY_DAYS = 28
MIN_ORDERS_FOR_ESTIMATE = 3
RESTOCK_WITHIN_DAYS = 21
FORECAST_DAYS = 30


class ReportError(ValueError):
    pass


def utc_offset():
    return timedelta(hours=current_app.config.get("STORE_UTC_OFFSET_HOURS", 8))


def local_today():
    return (datetime.utcnow() + utc_offset()).date()


def to_local_date(utc_datetime):
    return (utc_datetime + utc_offset()).date()


def parse_day(value, name):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise ReportError(f"{name} must be a date like 2026-10-24")


def resolve_range(start_raw, end_raw):
    end = parse_day(end_raw, "End date") if end_raw else local_today()
    start = parse_day(start_raw, "Start date") if start_raw else end - timedelta(days=29)
    if end < start:
        raise ReportError("The end date cannot be before the start date")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise ReportError(f"Choose a range of at most {MAX_RANGE_DAYS} days")
    return start, end


def previous_range(start, end):
    length = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    return prev_end - timedelta(days=length - 1), prev_end


def fetch_sale_lines(start, end, product_ids=None):
    """Order lines of recorded sales placed from `start` to `end` (inclusive, local dates)."""
    offset = utc_offset()
    start_utc = datetime.combine(start, time.min) - offset
    end_utc = datetime.combine(end + timedelta(days=1), time.min) - offset

    query = (
        db.session.query(OrderItem, Order)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.status.in_(SALE_STATUSES),
            Order.return_status != "approved",
            Order.payment_status.notin_(NOT_A_SALE_PAYMENT_STATES),
            Order.created_at >= start_utc,
            Order.created_at < end_utc,
        )
    )
    if product_ids is not None:
        query = query.filter(OrderItem.product_id.in_(list(product_ids) or [-1]))

    lines = []
    for item, order in query.all():
        lines.append({
            "day": to_local_date(order.created_at),
            "orderId": order.id,
            "productId": item.product_id,
            "name": item.product_name,
            "qty": item.quantity,
            "revenue": Decimal(item.unit_price) * item.quantity,
        })
    return lines


def bucket_start(day, granularity):
    if granularity == "weekly":
        return day - timedelta(days=day.weekday())
    if granularity == "monthly":
        return day.replace(day=1)
    return day


def next_bucket(day, granularity):
    if granularity == "weekly":
        return day + timedelta(days=7)
    if granularity == "monthly":
        return (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return day + timedelta(days=1)


def bucket_label(day, granularity):
    if granularity == "weekly":
        end = day + timedelta(days=6)
        return f"{day.strftime('%b')} {day.day} - {end.strftime('%b')} {end.day}"
    if granularity == "monthly":
        return day.strftime("%b %Y")
    return f"{day.strftime('%b')} {day.day}"


def summarize(lines):
    revenue = sum((l["revenue"] for l in lines), Decimal(0))
    units = sum(l["qty"] for l in lines)
    orders = len({l["orderId"] for l in lines})
    average = (revenue / orders) if orders else Decimal(0)
    return {
        "revenue": float(round(revenue, 2)),
        "units": units,
        "orders": orders,
        "averageOrderValue": float(round(average, 2)),
    }


def change_percent(current, previous):
    """None when there is nothing to compare against (never a made-up number)."""
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def build_series(lines, start, end, granularity):
    buckets = {}
    cursor = bucket_start(start, granularity)
    while cursor <= end:
        buckets[cursor] = {"revenue": Decimal(0), "units": 0, "orders": set()}
        cursor = next_bucket(cursor, granularity)
    for line in lines:
        bucket = buckets[bucket_start(line["day"], granularity)]
        bucket["revenue"] += line["revenue"]
        bucket["units"] += line["qty"]
        bucket["orders"].add(line["orderId"])
    return [
        {
            "start": day.isoformat(),
            "label": bucket_label(day, granularity),
            "revenue": float(round(data["revenue"], 2)),
            "units": data["units"],
            "orders": len(data["orders"]),
        }
        for day, data in buckets.items()
    ]


def catalog_products(product_ids=None):
    query = Product.query.filter(Product.category != "Services")
    if product_ids is not None:
        query = query.filter(Product.id.in_(list(product_ids) or [-1]))
    return query.order_by(Product.id).all()


def product_rows(current_lines, previous_lines, products):
    """One row per catalog product, including products with no sales in the range."""
    def tally(lines):
        totals = defaultdict(lambda: {"units": 0, "revenue": Decimal(0), "orders": set(), "name": ""})
        for line in lines:
            key = line["productId"] if line["productId"] is not None else f"name:{line['name']}"
            row = totals[key]
            row["units"] += line["qty"]
            row["revenue"] += line["revenue"]
            row["orders"].add(line["orderId"])
            row["name"] = line["name"]
        return totals

    now, before = tally(current_lines), tally(previous_lines)
    total_revenue = sum((r["revenue"] for r in now.values()), Decimal(0))

    rows, seen = [], set()
    for product in products:
        seen.add(product.id)
        cur, prev = now.get(product.id), before.get(product.id)
        rows.append(_row(product.id, product.name, product.category, product.stock, cur, prev, total_revenue))
    for key, cur in now.items():  # sold in the range but no longer in the catalog
        if key in seen:
            continue
        rows.append(_row(None, cur["name"], None, None, cur, before.get(key), total_revenue))
    return rows


def _row(product_id, name, category, stock, cur, prev, total_revenue):
    units = cur["units"] if cur else 0
    revenue = cur["revenue"] if cur else Decimal(0)
    prev_units = prev["units"] if prev else 0
    prev_revenue = prev["revenue"] if prev else Decimal(0)
    return {
        "productId": product_id,
        "name": name,
        "category": category,
        "stock": stock,
        "units": units,
        "revenue": float(round(revenue, 2)),
        "orders": len(cur["orders"]) if cur else 0,
        "revenueShare": round(float(revenue / total_revenue) * 100, 1) if total_revenue else 0,
        "previousUnits": prev_units,
        "previousRevenue": float(round(prev_revenue, 2)),
        "unitsChange": change_percent(units, prev_units),
        "revenueChange": change_percent(float(revenue), float(prev_revenue)),
        "discontinued": product_id is None,
    }


def build_report(start, end, granularity, product_ids=None):
    if granularity not in GRANULARITIES:
        raise ReportError("Choose daily, weekly or monthly")
    prev_start, prev_end = previous_range(start, end)

    current = fetch_sale_lines(start, end, product_ids)
    previous = fetch_sale_lines(prev_start, prev_end, product_ids)
    rows = product_rows(current, previous, catalog_products(product_ids))

    sold = sorted((r for r in rows if r["units"] > 0), key=lambda r: (-r["units"], -r["revenue"]))
    ranked_for_lowest = sorted(
        (r for r in rows if not r["discontinued"]), key=lambda r: (r["units"], r["revenue"], r["name"])
    )

    summary, prior = summarize(current), summarize(previous)
    return {
        "range": {
            "start": start.isoformat(), "end": end.isoformat(),
            "previousStart": prev_start.isoformat(), "previousEnd": prev_end.isoformat(),
            "granularity": granularity,
        },
        "summary": summary,
        "previous": prior,
        "change": {
            "revenue": change_percent(summary["revenue"], prior["revenue"]),
            "units": change_percent(summary["units"], prior["units"]),
            "orders": change_percent(summary["orders"], prior["orders"]),
        },
        "series": build_series(current, start, end, granularity),
        "products": sorted(rows, key=lambda r: (-r["units"], -r["revenue"], r["name"])),
        "bestSelling": sold[:5],
        "lowestSelling": ranked_for_lowest[:5],
        "basis": "Recorded sales: orders that were confirmed and not cancelled, returned or refunded. "
                 "Revenue excludes shipping fees.",
    }


def build_product_history(product_id, start, end, granularity):
    if granularity not in GRANULARITIES:
        raise ReportError("Choose daily, weekly or monthly")
    lines = fetch_sale_lines(start, end, [product_id])
    return {
        "range": {"start": start.isoformat(), "end": end.isoformat(), "granularity": granularity},
        "summary": summarize(lines),
        "series": build_series(lines, start, end, granularity),
    }


def recorded_revenue(product_ids=None):
    """Merchandise revenue of every recorded sale, all time. Used on the dashboard overview."""
    query = (
        db.session.query(OrderItem, Order)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.status.in_(SALE_STATUSES),
            Order.return_status != "approved",
            Order.payment_status.notin_(NOT_A_SALE_PAYMENT_STATES),
        )
    )
    if product_ids is not None:
        query = query.filter(OrderItem.product_id.in_(list(product_ids) or [-1]))
    total, orders = Decimal(0), set()
    for item, order in query.all():
        total += Decimal(item.unit_price) * item.quantity
        orders.add(order.id)
    return float(round(total, 2)), len(orders)


def first_sale_day(product_ids=None):
    query = (
        db.session.query(db.func.min(Order.created_at))
        .join(OrderItem, OrderItem.order_id == Order.id)
        .filter(
            Order.status.in_(SALE_STATUSES),
            Order.return_status != "approved",
            Order.payment_status.notin_(NOT_A_SALE_PAYMENT_STATES),
        )
    )
    if product_ids is not None:
        query = query.filter(OrderItem.product_id.in_(list(product_ids) or [-1]))
    first = query.scalar()
    return to_local_date(first) if first else None


def weighted_average(values):
    """Recent weeks count more: weights 1, 2, 3 ... oldest to newest."""
    weights = range(1, len(values) + 1)
    return sum(v * w for v, w in zip(values, weights)) / sum(weights)


def build_insights(product_ids=None):
    """Demand estimates and suggestions. Everything here is derived from recorded weekly
    sales of the last LOOKBACK_WEEKS full weeks; nothing is guaranteed."""
    today = local_today()
    this_week = today - timedelta(days=today.weekday())
    week_starts = [this_week - timedelta(days=7 * n) for n in range(LOOKBACK_WEEKS, 0, -1)]
    window_start, window_end = week_starts[0], this_week - timedelta(days=1)

    first_day = first_sale_day(product_ids)
    history_days = (today - first_day).days if first_day else 0
    enough_history = history_days >= MIN_HISTORY_DAYS

    lines = fetch_sale_lines(window_start, window_end, product_ids)
    weekly = defaultdict(lambda: [0] * LOOKBACK_WEEKS)
    order_ids = defaultdict(set)
    for line in lines:
        if line["productId"] is None:
            continue
        index = (bucket_start(line["day"], "weekly") - window_start).days // 7
        weekly[line["productId"]][index] += line["qty"]
        order_ids[line["productId"]].add(line["orderId"])

    items, suggestions = [], []
    for product in catalog_products(product_ids):
        units = weekly.get(product.id, [0] * LOOKBACK_WEEKS)
        orders = len(order_ids.get(product.id, ()))
        item = {
            "productId": product.id, "name": product.name, "stock": product.stock,
            "weeklyUnits": units, "ordersInWindow": orders,
            "status": "not_enough_data",
        }
        if not enough_history:
            item["note"] = f"Needs at least {MIN_HISTORY_DAYS} days of recorded sales; there are {history_days} so far."
        elif sum(units) == 0:
            item["status"] = "no_recent_sales"
            item["note"] = f"No sales recorded in the last {LOOKBACK_WEEKS} weeks."
            if product.stock > 0:
                suggestions.append({
                    "type": "promote", "productId": product.id, "name": product.name,
                    "message": f"{product.name} had no recorded sales in the last {LOOKBACK_WEEKS} weeks "
                               f"and {product.stock} units are in stock. It may need promotion.",
                })
        elif orders < MIN_ORDERS_FOR_ESTIMATE:
            item["note"] = f"Only {orders} order(s) in the last {LOOKBACK_WEEKS} weeks, too few for an estimate."
        else:
            per_week = weighted_average(units)
            recent, prior = sum(units[LOOKBACK_WEEKS // 2:]), sum(units[:LOOKBACK_WEEKS // 2])
            if prior == 0:
                trend = "up"
            else:
                ratio = recent / prior
                trend = "up" if ratio >= 1.15 else "down" if ratio <= 0.85 else "flat"
            estimate = per_week * FORECAST_DAYS / 7
            days_of_stock = round(product.stock / (per_week / 7), 1) if per_week > 0 else None
            item.update({
                "status": "estimate",
                "estimatedWeeklyUnits": round(per_week, 1),
                "estimatedUnitsNext30Days": round(estimate),
                "estimateLow": math.floor(min(units) * FORECAST_DAYS / 7),
                "estimateHigh": math.ceil(max(units) * FORECAST_DAYS / 7),
                "trend": trend,
                "daysOfStock": days_of_stock,
            })
            if days_of_stock is not None and days_of_stock < RESTOCK_WITHIN_DAYS:
                shortfall = max(0, math.ceil(estimate - product.stock))
                suggestions.append({
                    "type": "restock", "productId": product.id, "name": product.name,
                    "message": f"{product.name}: {product.stock} in stock covers about {days_of_stock} days "
                               f"at the recent pace. Roughly {shortfall} more units would cover the next {FORECAST_DAYS} days.",
                })
            elif trend == "up":
                suggestions.append({
                    "type": "prioritize", "productId": product.id, "name": product.name,
                    "message": f"{product.name} is selling faster than before (about {round(per_week, 1)} units a week). "
                               "Keep it in stock and visible.",
                })
            elif trend == "down" and days_of_stock and days_of_stock > 90:
                suggestions.append({
                    "type": "promote", "productId": product.id, "name": product.name,
                    "message": f"{product.name} sales are slowing and current stock would last about "
                               f"{days_of_stock} days. A promotion may help.",
                })
        items.append(item)

    order = {"restock": 0, "prioritize": 1, "promote": 2}
    suggestions.sort(key=lambda s: (order[s["type"]], s["name"]))
    return {
        "enoughHistory": enough_history,
        "historyDays": history_days,
        "window": {"start": window_start.isoformat(), "end": window_end.isoformat(), "weeks": LOOKBACK_WEEKS},
        "method": f"Estimates use a weighted average of weekly units over the last {LOOKBACK_WEEKS} full weeks "
                  "(recent weeks count more). The range is the slowest and fastest recorded week. "
                  "A product needs a few orders and about a month of shop history before an estimate is shown.",
        "disclaimer": "These are estimates from past sales, not guarantees. Actual demand can differ.",
        "products": items,
        "suggestions": suggestions,
    }
