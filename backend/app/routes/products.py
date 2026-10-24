from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Product, OrderItem
from app.utils.auth_decorators import require_permission, current_admin

products_bp = Blueprint("products", __name__, url_prefix="/api/products")

LEGACY_SERVICE_CATEGORY = "Services"


def _visible_to(admin, product):
    return admin.is_head or product.owner_admin_id == admin.id


def _parse_price_and_stock(data, product=None):
    """Returns (price, stock, error)."""
    price = product.price if product else None
    stock = product.stock if product else None
    if "price" in data or product is None:
        try:
            price = Decimal(str(data.get("price")))
        except (InvalidOperation, TypeError):
            return None, None, "Please enter a valid price"
        if price < 0 or price > Decimal("9999999"):
            return None, None, "Price is out of range"
    if "stock" in data or product is None:
        try:
            stock = int(data.get("stock"))
        except (TypeError, ValueError):
            return None, None, "Please enter a valid stock number"
        if stock < 0:
            return None, None, "Stock cannot be negative"
    return price, stock, None


@products_bp.get("")
def list_products():
    category = request.args.get("category")
    query = Product.query.filter(Product.category != LEGACY_SERVICE_CATEGORY)
    if category and category != "All":
        query = query.filter_by(category=category)
    products = query.order_by(Product.id).all()
    return jsonify({"products": [p.to_dict() for p in products]})


@products_bp.get("/manage")
@require_permission("manage_products")
def list_managed_products():
    admin = current_admin()
    query = Product.query.filter(Product.category != LEGACY_SERVICE_CATEGORY)
    if not admin.is_head:
        query = query.filter_by(owner_admin_id=admin.id)
    return jsonify({"products": [p.to_dict() for p in query.order_by(Product.id).all()]})


@products_bp.get("/<int:product_id>")
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({"product": product.to_dict()})


@products_bp.post("")
@require_permission("manage_products")
def create_product():
    admin = current_admin()
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Please enter a product name"}), 400
    price, stock, error = _parse_price_and_stock(data)
    if error:
        return jsonify({"error": error}), 400

    product = Product(
        name=name,
        category=data.get("category", "Oils & Fluids"),
        price=price,
        stock=stock,
        image_glyph=data.get("imageGlyph", "oil-synthetic"),
        image_photo=data.get("imagePhoto"),
        short_desc=data.get("shortDesc", ""),
        description=data.get("description", ""),
        specs=data.get("specs", []),
        benefits=data.get("benefits", []),
        usage_steps=data.get("usage", []),
        owner_admin_id=None if admin.is_head else admin.id,
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({"product": product.to_dict()}), 201


@products_bp.put("/<int:product_id>")
@require_permission("manage_products")
def update_product(product_id):
    admin = current_admin()
    product = Product.query.get_or_404(product_id)
    if not _visible_to(admin, product):
        return jsonify({"error": "You can only edit products assigned to you"}), 403

    data = request.get_json() or {}
    price, stock, error = _parse_price_and_stock(data, product)
    if error:
        return jsonify({"error": error}), 400
    product.price = price
    product.stock = stock

    for field, column in [
        ("name", "name"), ("category", "category"), ("shortDesc", "short_desc"),
        ("description", "description"), ("specs", "specs"), ("benefits", "benefits"),
    ]:
        if field in data:
            setattr(product, column, data[field])

    if "usage" in data:
        product.usage_steps = data["usage"]
    # Only overwrite the photo if a new one was actually uploaded, so
    # editing other fields doesn't accidentally wipe an existing photo.
    if data.get("imagePhoto"):
        product.image_photo = data["imagePhoto"]

    db.session.commit()
    return jsonify({"product": product.to_dict()})


@products_bp.delete("/<int:product_id>")
@require_permission("manage_products")
def delete_product(product_id):
    admin = current_admin()
    product = Product.query.get_or_404(product_id)
    if not _visible_to(admin, product):
        return jsonify({"error": "You can only delete products assigned to you"}), 403
    if OrderItem.query.filter_by(product_id=product.id).first():
        return jsonify({
            "error": "This product has order history. Set its stock to 0 instead of deleting it.",
        }), 409
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"})
