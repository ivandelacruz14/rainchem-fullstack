from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import CartItem, Product
from app.services.catalog import serialize_products
from app.services.pricing import bulk_discount_rate, compute_shipping, money, unit_price_after_discount
from app.utils.auth_decorators import current_user_id, require_user

cart_bp = Blueprint("cart", __name__, url_prefix="/api/cart")

MAX_LINE_QTY = 999


def cart_payload(user_id):
    """The signed-in customer's cart, priced from the current product records."""
    rows = (
        CartItem.query.filter_by(user_id=user_id)
        .order_by(CartItem.id)
        .all()
    )
    products = [row.product for row in rows if row.product]
    serialized = {p["id"]: p for p in serialize_products(products)}

    items, subtotal, original, total_qty = [], 0, 0, 0
    for row in rows:
        product = row.product
        if not product:
            continue
        rate = bulk_discount_rate(row.quantity)
        unit = unit_price_after_discount(product.price, rate)
        line_total = unit * row.quantity
        subtotal += line_total
        original += money(product.price) * row.quantity
        total_qty += row.quantity
        items.append({
            "product": serialized[product.id],
            "qty": row.quantity,
            "discountRate": float(rate),
            "unitPrice": float(unit),
            "lineTotal": float(line_total),
        })

    shipping = compute_shipping(subtotal, total_qty) if items else 0
    return {
        "items": items,
        "summary": {
            "subtotal": float(subtotal),
            "savings": float(original - subtotal),
            "shipping": float(shipping),
            "total": float(subtotal + shipping),
            "totalQty": total_qty,
        },
    }


def _parse_qty(value):
    try:
        qty = int(value)
    except (TypeError, ValueError):
        return None
    return qty if 0 <= qty <= MAX_LINE_QTY else None


@cart_bp.get("")
@require_user
def get_cart():
    return jsonify(cart_payload(current_user_id()))


@cart_bp.post("/items")
@require_user
def add_item():
    """Adds `qty` units of a product (default 1) to the caller's own cart."""
    user_id = current_user_id()
    data = request.get_json() or {}
    product = db.session.get(Product, data.get("productId")) if data.get("productId") else None
    if not product or product.category == "Services":
        return jsonify({"error": "That product is not available"}), 404
    qty = _parse_qty(data.get("qty", 1))
    if not qty:
        return jsonify({"error": "Quantity must be at least 1"}), 400
    if product.stock <= 0:
        return jsonify({"error": f"{product.name} is out of stock"}), 400

    row = CartItem.query.filter_by(user_id=user_id, product_id=product.id).first()
    wanted = (row.quantity if row else 0) + qty
    if wanted > product.stock:
        return jsonify({"error": f"Only {product.stock} units of {product.name} are available"}), 400
    if row:
        row.quantity = wanted
    else:
        db.session.add(CartItem(user_id=user_id, product_id=product.id, quantity=wanted))
    db.session.commit()
    return jsonify(cart_payload(user_id))


@cart_bp.put("/items/<int:product_id>")
@require_user
def set_item_quantity(product_id):
    """Sets the quantity of one line. 0 removes it."""
    user_id = current_user_id()
    qty = _parse_qty((request.get_json() or {}).get("qty"))
    if qty is None:
        return jsonify({"error": "Enter a valid quantity"}), 400

    row = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()
    if not row:
        return jsonify({"error": "That item is not in your cart"}), 404
    if qty == 0:
        db.session.delete(row)
    else:
        product = row.product
        if product and qty > product.stock:
            return jsonify({"error": f"Only {product.stock} units of {product.name} are available"}), 400
        row.quantity = qty
    db.session.commit()
    return jsonify(cart_payload(user_id))


@cart_bp.delete("/items/<int:product_id>")
@require_user
def remove_item(product_id):
    user_id = current_user_id()
    CartItem.query.filter_by(user_id=user_id, product_id=product_id).delete()
    db.session.commit()
    return jsonify(cart_payload(user_id))


@cart_bp.delete("")
@require_user
def clear_cart():
    user_id = current_user_id()
    CartItem.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify(cart_payload(user_id))
