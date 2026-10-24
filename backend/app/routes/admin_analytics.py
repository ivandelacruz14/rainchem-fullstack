from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Product
from app.services import sales_analytics as analytics
from app.utils.auth_decorators import require_permission, current_admin

admin_analytics_bp = Blueprint("admin_analytics", __name__, url_prefix="/api/admin/analytics")


def _scope_owner_id():
    admin = current_admin()
    return None if admin.is_head else admin.id


def _range_from_request():
    granularity = request.args.get("granularity", "daily")
    start, end = analytics.resolve_range(granularity, request.args.get("start"), request.args.get("end"))
    return granularity, start, end


@admin_analytics_bp.get("/report")
@require_permission("view_sales")
def sales_report():
    try:
        granularity, start, end = _range_from_request()
    except analytics.RangeError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify(analytics.build_report(granularity, start, end, _scope_owner_id()))


@admin_analytics_bp.get("/products/<int:product_id>/history")
@require_permission("view_sales")
def product_history(product_id):
    product = db.session.get(Product, product_id)
    owner_id = _scope_owner_id()
    if product is None or (owner_id is not None and product.owner_admin_id != owner_id):
        return jsonify({"error": "Product not found"}), 404
    try:
        granularity, start, end = _range_from_request()
    except analytics.RangeError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify(analytics.build_product_history(product, granularity, start, end))
