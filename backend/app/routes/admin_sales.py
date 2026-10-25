from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Product, ProductSale
from app.services.admin_scope import scope_product_ids
from app.services.pricing import unit_price_after_discount
from app.services.promotions import (
    SaleError, local_days, overlapping, read_label, read_percent, read_window,
)
from app.utils.auth_decorators import current_admin, require_permission

admin_sales_bp = Blueprint("admin_sales", __name__, url_prefix="/api/admin/sales")


def _sale_dict(sale, now=None):
    start, end = local_days(sale)
    product = sale.product
    return {
        "id": sale.id,
        "productId": sale.product_id,
        "productName": product.name if product else "",
        "originalPrice": float(product.price) if product else 0,
        "percent": sale.discount_percent,
        "salePrice": float(unit_price_after_discount(product.price, sale.discount_percent / 100)) if product else 0,
        "label": sale.label,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "status": sale.status(now),
    }


def _allowed_ids(admin):
    ids = scope_product_ids(admin)
    return ids  # None means every product


def _can_manage(sale, admin):
    ids = _allowed_ids(admin)
    return ids is None or sale.product_id in ids


@admin_sales_bp.get("")
@require_permission("products")
def list_sales():
    admin = current_admin()
    ids = _allowed_ids(admin)
    query = ProductSale.query
    if ids is not None:
        query = query.filter(ProductSale.product_id.in_(ids or [-1]))
    now = datetime.utcnow()
    rows = query.order_by(ProductSale.starts_at.desc(), ProductSale.id.desc()).limit(300).all()
    return jsonify({"sales": [_sale_dict(s, now) for s in rows]})


@admin_sales_bp.post("")
@require_permission("products")
def create_sales():
    """Body: {productIds: [..], percent: 30, startDate: "2026-11-02", endDate: "2026-11-08", label: "Weekend Sale"}"""
    admin = current_admin()
    data = request.get_json() or {}
    try:
        percent = read_percent(data.get("percent"))
        label = read_label(data.get("label"))
        starts_at, ends_at = read_window(data.get("startDate"), data.get("endDate"))
    except SaleError as error:
        return jsonify({"error": str(error)}), 400

    product_ids = data.get("productIds")
    if not isinstance(product_ids, list) or not product_ids:
        return jsonify({"error": "Choose at least one product"}), 400

    allowed = _allowed_ids(admin)
    products = []
    for pid in dict.fromkeys(product_ids):  # keep order, drop duplicates
        product = db.session.get(Product, pid) if isinstance(pid, int) else None
        if product is None or product.category == "Services":
            return jsonify({"error": "One of the selected products does not exist"}), 400
        if allowed is not None and product.id not in allowed:
            return jsonify({"error": "You can only put your own products on sale"}), 403
        clash = overlapping(product.id, starts_at, ends_at)
        if clash:
            return jsonify({"error": f"{product.name} already has a sale during those dates. End or edit that sale first."}), 400
        products.append(product)

    created = []
    for product in products:
        sale = ProductSale(
            product_id=product.id, discount_percent=percent, starts_at=starts_at, ends_at=ends_at,
            label=label, is_active=True, created_by=admin.id,
        )
        db.session.add(sale)
        created.append(sale)
    db.session.commit()
    return jsonify({"sales": [_sale_dict(s) for s in created]}), 201


@admin_sales_bp.put("/<int:sale_id>")
@require_permission("products")
def update_sale(sale_id):
    admin = current_admin()
    sale = ProductSale.query.get_or_404(sale_id)
    if not _can_manage(sale, admin):
        return jsonify({"error": "You can only manage sales on your own products"}), 403
    status = sale.status()
    if status == "ended":
        return jsonify({"error": "This sale has ended and can no longer be edited"}), 400

    data = request.get_json() or {}
    try:
        if "percent" in data:
            sale.discount_percent = read_percent(data["percent"])
        if "label" in data:
            sale.label = read_label(data["label"])
        if "startDate" in data or "endDate" in data:
            current_start = local_days(sale)[0]
            if status == "active" and data.get("startDate", current_start.isoformat()) != current_start.isoformat():
                return jsonify({"error": "A sale that is already running keeps its start date"}), 400
            starts_at, ends_at = _window_for_edit(sale, status, data, current_start)
            clash = overlapping(sale.product_id, starts_at, ends_at, ignore_id=sale.id)
            if clash:
                return jsonify({"error": "That would overlap another sale on this product"}), 400
            sale.starts_at, sale.ends_at = starts_at, ends_at
    except SaleError as error:
        return jsonify({"error": str(error)}), 400
    db.session.commit()
    return jsonify({"sale": _sale_dict(sale)})


def _window_for_edit(sale, status, data, current_start):
    """New dates for an edit. A running sale keeps its start; only a scheduled one can move it."""
    from datetime import date
    from app.services.promotions import MAX_DAYS, window_for
    try:
        end_day = date.fromisoformat(str(data.get("endDate", local_days(sale)[1].isoformat())))
        start_day = current_start if status == "active" else date.fromisoformat(str(data.get("startDate", current_start.isoformat())))
    except ValueError:
        raise SaleError("Choose a start date and an end date")
    if end_day < start_day:
        raise SaleError("The end date cannot be before the start date")
    if status == "scheduled":
        starts_at, ends_at = read_window(start_day.isoformat(), end_day.isoformat())
        return starts_at, ends_at
    if (end_day - start_day).days + 1 > MAX_DAYS:
        raise SaleError(f"A sale can run for at most {MAX_DAYS} days")
    starts_at, ends_at = window_for(start_day, end_day)
    if ends_at <= datetime.utcnow():
        raise SaleError("The end date has already passed. Use End sale instead.")
    return sale.starts_at, ends_at


@admin_sales_bp.post("/<int:sale_id>/end")
@require_permission("products")
def end_sale(sale_id):
    """Stops a running sale right now, or cancels one that has not started yet. History is kept."""
    admin = current_admin()
    sale = ProductSale.query.get_or_404(sale_id)
    if not _can_manage(sale, admin):
        return jsonify({"error": "You can only manage sales on your own products"}), 403
    status = sale.status()
    if status == "ended":
        return jsonify({"error": "This sale has already ended"}), 400
    if status == "active":
        sale.ends_at = datetime.utcnow()
    else:
        sale.is_active = False
    db.session.commit()
    return jsonify({"sale": _sale_dict(sale)})
