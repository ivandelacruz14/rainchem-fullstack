from flask import Blueprint, Response, jsonify

from app.models import Order
from app.services.payment_receipt import NotPaidError, build
from app.utils.auth_decorators import current_user_id, require_permission, require_user

payment_receipts_bp = Blueprint("payment_receipts", __name__, url_prefix="/api/receipts")
HEADERS = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}


def _pdf(order):
    try:
        data, receipt = build(order)
    except NotPaidError as error:
        return jsonify({"error": str(error)}), 400
    headers = dict(HEADERS, **{"Content-Disposition": f'attachment; filename="{receipt.receipt_number}.pdf"'})
    return Response(data, mimetype="application/pdf", headers=headers)


@payment_receipts_bp.get("/orders/<int:order_id>.pdf")
@require_user
def my_payment_receipt(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user_id()).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return _pdf(order)


@payment_receipts_bp.get("/admin/orders/<int:order_id>.pdf")
@require_permission("manage_orders")
def admin_payment_receipt(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return _pdf(order)
