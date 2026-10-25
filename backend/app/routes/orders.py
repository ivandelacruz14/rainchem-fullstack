from decimal import Decimal
from datetime import datetime

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import CartItem, Order, OrderItem, OrderStatusHistory, Product, User
from app.models.order import COD
from app.services import payment_flow
from app.services.auth_utils import is_valid_email, is_valid_phone
from app.services.pricing import compute_shipping, effective_discount_rate, unit_price_after_discount, money
from app.services.receipt_service import generate_order_number, generate_tracking_number, create_receipt_for_order
from app.services.email_service import send_email
from app.services.catalog import serialize_products
from app.services.promotions import active_sales
from app.services.recommendations import get_recommendations
from app.services.reviews import ReviewError, submit_reviews
from app.utils.auth_decorators import require_user, current_user_id

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@orders_bp.post("")
@require_user
def create_order():
    data = request.get_json() or {}
    cart_items = data.get("items")
    if not cart_items:
        # No lines in the request: fall back to the saved cart of the signed-in customer.
        cart_items = [
            {"productId": row.product_id, "qty": row.quantity}
            for row in CartItem.query.filter_by(user_id=current_user_id()).all()
        ]
    customer = data.get("customer") or {}
    address = data.get("address") or {}
    payment_method = data.get("paymentMethod", COD)

    if not cart_items:
        return jsonify({"error": "Your cart is empty"}), 400
    if payment_method not in payment_flow.available_methods():
        return jsonify({"error": f"{payment_method} is not available right now. Please choose another payment method."}), 400
    if not is_valid_phone(customer.get("phone", "")):
        return jsonify({"error": "Please enter a valid contact number"}), 400
    if not is_valid_email(customer.get("email", "")):
        return jsonify({"error": "Please enter a valid email address"}), 400

    line_items = []
    subtotal = Decimal(0)
    total_qty = 0
    sales = active_sales()

    for line in cart_items:
        product = Product.query.get(line.get("productId"))
        if not product:
            continue
        try:
            qty = int(line.get("qty", 1))
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid quantity"}), 400
        if qty < 1:
            return jsonify({"error": "Quantity must be at least 1"}), 400
        if qty > product.stock:
            return jsonify({"error": f"Only {product.stock} units of {product.name} are available"}), 400

        sale = sales.get(product.id)
        rate = effective_discount_rate(qty, sale.discount_percent if sale else 0)
        unit_price = unit_price_after_discount(product.price, rate)
        line_items.append({"product": product, "qty": qty, "unit_price": unit_price, "rate": rate})
        subtotal += unit_price * qty
        total_qty += qty

    if not line_items:
        return jsonify({"error": "No valid items in cart"}), 400

    shipping_fee = compute_shipping(subtotal, total_qty)
    total = subtotal + shipping_fee

    order = Order(
        order_number=generate_order_number(),
        user_id=current_user_id(),
        status="pending_confirmation",
        tracking_number=generate_tracking_number(),
        customer_name=customer.get("name", ""),
        customer_phone=customer.get("phone", ""),
        customer_email=customer.get("email", ""),
        address_line1=address.get("line1", ""),
        address_city=address.get("city", ""),
        address_province=address.get("province", ""),
        address_region=address.get("region", ""),
        address_zip=address.get("zip", ""),
        payment_method=payment_method,
        payment_status="unpaid",
        subtotal=money(subtotal),
        shipping_fee=shipping_fee,
        total=money(total),
    )
    db.session.add(order)
    db.session.flush()

    for line in line_items:
        db.session.add(OrderItem(
            order_id=order.id,
            product_id=line["product"].id,
            product_name=line["product"].name,
            unit_price=line["unit_price"],
            discount_rate=line["rate"],
            quantity=line["qty"],
        ))
        line["product"].stock -= line["qty"]

    db.session.add(OrderStatusHistory(order_id=order.id, status="pending_confirmation"))

    user = User.query.get(current_user_id())
    if user:
        user.address_line1 = address.get("line1", user.address_line1)
        user.address_city = address.get("city", user.address_city)
        user.address_province = address.get("province", user.address_province)
        user.address_region = address.get("region", user.address_region)
        user.address_zip = address.get("zip", user.address_zip)
        user.phone = customer.get("phone", user.phone)

    CartItem.query.filter(
        CartItem.user_id == current_user_id(),
        CartItem.product_id.in_([line["product"].id for line in line_items]),
    ).delete(synchronize_session=False)

    db.session.commit()

    online = order.is_online_payment
    send_email(
        order.customer_email, f"Order received - {order.order_number}",
        f"Hi {order.customer_name},\n\nWe received your order {order.order_number} "
        f"for a total of PHP {order.total:.2f}. "
        + (f"Please complete your {order.payment_method} payment from My Orders > To Pay "
           "so we can start processing it. You can also switch to another payment method there. "
           if online else
           "It is now pending confirmation from our team, and you'll get another email once it's confirmed. ")
        + "You can still cancel this order from My Orders while it's pending.\n\n"
        f"Tracking number: {order.tracking_number}",
        user_id=order.user_id,
    )

    recommendations = get_recommendations(order)
    return jsonify({
        "order": order.to_dict(),
        "recommendations": serialize_products(recommendations),
        # Online methods continue on our own payment page, where the customer can
        # see the GCash details / card button and switch method.
        "payPath": f"/payment/{order.id}" if online else None,
    }), 201


@orders_bp.get("")
@require_user
def list_my_orders():
    orders = (
        Order.query.filter_by(user_id=current_user_id())
        .order_by(Order.created_at.desc())
        .all()
    )
    return jsonify({"orders": [o.to_dict() for o in orders]})


@orders_bp.get("/<int:order_id>")
@require_user
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user_id():
        return jsonify({"error": "Not found"}), 404
    return jsonify({"order": order.to_dict()})


@orders_bp.post("/<int:order_id>/cancel")
@require_user
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user_id():
        return jsonify({"error": "Not found"}), 404
    if order.status != "pending_confirmation":
        return jsonify({"error": "This order can no longer be cancelled"}), 400

    order.status = "cancelled"
    order.cancelled_at = datetime.utcnow()
    if order.payment_status == "paid":
        order.payment_status = "refund_pending"
    db.session.add(OrderStatusHistory(order_id=order.id, status="cancelled"))

    for item in order.items:
        if item.product_id:
            product = Product.query.get(item.product_id)
            if product:
                product.stock += item.quantity

    db.session.commit()

    send_email(
        order.customer_email, f"Order cancelled - {order.order_number}",
        f"Hi {order.customer_name},\n\nYour order {order.order_number} has been "
        "cancelled as requested. "
        + ("Your payment will be refunded by our team. " if order.payment_status == "refund_pending" else "")
        + "If this was a mistake, feel free to place a new order.",
        user_id=order.user_id,
    )
    return jsonify({"order": order.to_dict()})


@orders_bp.post("/<int:order_id>/received")
@require_user
def mark_received(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user_id():
        return jsonify({"error": "Not found"}), 404
    if order.status != "shipped":
        return jsonify({"error": "Only shipped orders can be marked as received"}), 400

    order.status = "delivered"
    if order.payment_status == "unpaid" and not order.is_online_payment:
        order.payment_status = "paid"
        order.paid_at = datetime.utcnow()
    db.session.add(OrderStatusHistory(order_id=order.id, status="delivered"))
    db.session.commit()
    return jsonify({"order": order.to_dict()})


def _review_response(order):
    return jsonify({"order": order.to_dict()})


@orders_bp.post("/<int:order_id>/reviews")
@require_user
def review_order_items(order_id):
    """Body: {"reviews": [{"productId": 1, "rating": 5, "comment": "..."}]}"""
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user_id():
        return jsonify({"error": "Not found"}), 404
    entries = (request.get_json() or {}).get("reviews")
    if not isinstance(entries, list):
        return jsonify({"error": "Send the reviews as a list"}), 400
    try:
        submit_reviews(order, entries)
    except ReviewError as error:
        return jsonify({"error": str(error)}), 400
    return _review_response(order)


@orders_bp.post("/<int:order_id>/review")
@require_user
def review_order(order_id):
    """Rates every product in the order that has not been reviewed yet with one rating
    and comment. Kept so older clients keep working."""
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user_id():
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    entries = [
        {"productId": item.product_id, "rating": data.get("rating"), "comment": data.get("comment")}
        for item in order.reviewable_items
    ]
    if not entries:
        return jsonify({"error": "There is nothing left to review on this order"}), 400
    try:
        submit_reviews(order, entries)
    except ReviewError as error:
        return jsonify({"error": str(error)}), 400
    return _review_response(order)


@orders_bp.post("/<int:order_id>/return")
@require_user
def request_return(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user_id():
        return jsonify({"error": "Not found"}), 404
    if not order.can_return:
        return jsonify({"error": "This order can no longer be returned"}), 400

    reason = str((request.get_json() or {}).get("reason") or "").strip()
    if len(reason) < 5:
        return jsonify({"error": "Please tell us why you are returning this order"}), 400

    order.return_status = "requested"
    order.return_reason = reason[:500]
    order.return_requested_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"order": order.to_dict()})


@orders_bp.get("/track/<tracking_number>")
@require_user
def track_order(tracking_number):
    """Tracking numbers are short, so only the customer who placed the order can look one up."""
    order = Order.query.filter_by(tracking_number=tracking_number, user_id=current_user_id()).first()
    if not order:
        order = Order.query.filter_by(order_number=tracking_number, user_id=current_user_id()).first()
    if not order:
        return jsonify({"error": "No order found with that tracking number"}), 404
    return jsonify({"order": order.to_dict()})


@orders_bp.get("/<int:order_id>/receipt")
@require_user
def get_receipt(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user_id():
        return jsonify({"error": "Not found"}), 404
    if not order.receipt and order.status in ("confirmed", "processing", "shipped", "delivered"):
        create_receipt_for_order(order)  # order was confirmed before receipts were saved
    if not order.receipt:
        return jsonify({"error": "A receipt is only available once the order is confirmed"}), 404
    return jsonify({
        "order": order.to_dict(),
        "receipt": order.receipt.to_dict(),
    })
