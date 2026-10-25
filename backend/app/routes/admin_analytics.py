from flask import Blueprint, jsonify, request

from app.models import Product
from app.services import sales_analytics as analytics
from app.services.admin_scope import scope_product_ids
from app.utils.auth_decorators import current_admin, require_permission

admin_analytics_bp = Blueprint("admin_analytics", __name__, url_prefix="/api/admin/analytics")


def _bad_request(error):
    return jsonify({"error": str(error)}), 400


@admin_analytics_bp.get("/report")
@require_permission("analytics")
def sales_report():
    """Query: granularity=daily|weekly|monthly, start=YYYY-MM-DD, end=YYYY-MM-DD."""
    try:
        start, end = analytics.resolve_range(request.args.get("start"), request.args.get("end"))
        report = analytics.build_report(
            start, end, request.args.get("granularity", "daily"), scope_product_ids(current_admin()),
        )
    except analytics.ReportError as error:
        return _bad_request(error)
    return jsonify(report)


@admin_analytics_bp.get("/products/<int:product_id>/history")
@require_permission("analytics")
def product_history(product_id):
    ids = scope_product_ids(current_admin())
    if ids is not None and product_id not in ids:
        return jsonify({"error": "You can only view sales of your own products"}), 403
    product = Product.query.get_or_404(product_id)
    try:
        start, end = analytics.resolve_range(request.args.get("start"), request.args.get("end"))
        history = analytics.build_product_history(
            product_id, start, end, request.args.get("granularity", "weekly"),
        )
    except analytics.ReportError as error:
        return _bad_request(error)
    history["product"] = {"id": product.id, "name": product.name}
    return jsonify(history)


@admin_analytics_bp.get("/insights")
@require_permission("analytics")
def insights():
    return jsonify(analytics.build_insights(scope_product_ids(current_admin())))
