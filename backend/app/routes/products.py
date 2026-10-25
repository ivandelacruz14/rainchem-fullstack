from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Admin, CartItem, OrderItem, Product, ProductReview
from app.services.catalog import serialize_product, serialize_products
from app.services.reviews import reviews_for_product
from app.utils.auth_decorators import current_admin, require_permission

products_bp = Blueprint("products", __name__, url_prefix="/api/products")

CATEGORIES = ["Oils & Fluids", "Coolant", "Filters", "Brakes", "Accessories"]
MAX_PRICE = Decimal("1000000")


def _visible_to_admin(product, admin):
    return admin.is_head or product.owner_admin_id == admin.id


def _owner_from_payload(data, admin, current_owner=None):
    """Distributors always own what they create. Only a Head Admin can assign an owner."""
    if not admin.is_head:
        return admin.id if current_owner is None else current_owner
    if "ownerId" not in data:
        return current_owner
    owner_id = data.get("ownerId")
    if owner_id in (None, "", 0):
        return None
    owner = db.session.get(Admin, int(owner_id))
    if owner is None:
        raise ValueError("The selected distributor does not exist")
    return owner.id


def _read_fields(data, creating):
    """Returns (values, errors). Only fields present in the request are returned when updating."""
    values, errors = {}, []

    def present(key):
        return creating or key in data

    if present("name"):
        name = str(data.get("name") or "").strip()
        if not name:
            errors.append("Product name is required")
        values["name"] = name[:200]
    if present("category"):
        category = data.get("category") or CATEGORIES[0]
        if category not in CATEGORIES:
            errors.append("Choose a valid category")
        values["category"] = category
    if present("price"):
        try:
            price = Decimal(str(data.get("price")))
            if not price.is_finite() or price <= 0 or price > MAX_PRICE:
                raise InvalidOperation
            values["price"] = price.quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError):
            errors.append("Enter a price greater than 0")
    if present("stock"):
        try:
            stock = int(data.get("stock"))
            if stock < 0:
                raise ValueError
            values["stock"] = stock
        except (ValueError, TypeError):
            errors.append("Stock must be a whole number, 0 or more")
    if present("shortDesc"):
        short = str(data.get("shortDesc") or "").strip()
        if not short:
            errors.append("A short description is required")
        values["short_desc"] = short[:255]
    if present("description"):
        description = str(data.get("description") or "").strip()
        if not description:
            errors.append("A full description is required")
        values["description"] = description
    for key, column in (("specs", "specs"), ("benefits", "benefits"), ("usage", "usage_steps")):
        if key in data or creating:
            items = data.get(key) or []
            if not isinstance(items, list):
                errors.append(f"{key} must be a list")
            else:
                values[column] = [str(i).strip() for i in items if str(i).strip()]
    return values, errors


@products_bp.get("")
def list_products():
    category = request.args.get("category")
    query = Product.query.filter(Product.category != "Services")  # services now live in their own module
    if category and category != "All":
        query = query.filter_by(category=category)
    products = query.order_by(Product.id).all()
    return jsonify({"products": serialize_products(products)})


@products_bp.get("/manage")
@require_permission("products")
def list_manageable_products():
    """The catalog as the signed-in admin may manage it: everything for a Head Admin,
    only their own products for a distributor."""
    admin = current_admin()
    query = Product.query.filter(Product.category != "Services")
    if not admin.is_head:
        query = query.filter(Product.owner_admin_id == admin.id)
    return jsonify({"products": serialize_products(query.order_by(Product.id).all(), admin_view=True)})


@products_bp.get("/<int:product_id>")
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({"product": serialize_product(product)})


@products_bp.get("/<int:product_id>/reviews")
def product_reviews(product_id):
    Product.query.get_or_404(product_id)
    return jsonify(reviews_for_product(product_id))


@products_bp.post("")
@require_permission("products")
def create_product():
    admin = current_admin()
    data = request.get_json() or {}
    values, errors = _read_fields(data, creating=True)
    if errors:
        return jsonify({"error": ". ".join(errors)}), 400
    try:
        owner_id = _owner_from_payload(data, admin)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    product = Product(
        image_glyph=data.get("imageGlyph") or "oil-synthetic",
        image_photo=data.get("imagePhoto"),
        owner_admin_id=owner_id,
        **values,
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({"product": serialize_product(product, admin_view=True)}), 201


@products_bp.put("/<int:product_id>")
@require_permission("products")
def update_product(product_id):
    admin = current_admin()
    product = Product.query.get_or_404(product_id)
    if not _visible_to_admin(product, admin):
        return jsonify({"error": "You can only manage your own products"}), 403

    data = request.get_json() or {}
    values, errors = _read_fields(data, creating=False)
    if errors:
        return jsonify({"error": ". ".join(errors)}), 400
    try:
        owner_id = _owner_from_payload(data, admin, current_owner=product.owner_admin_id)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    for column, value in values.items():
        setattr(product, column, value)
    product.owner_admin_id = owner_id
    # Only overwrite the photo if a new one was actually uploaded.
    if data.get("imagePhoto"):
        product.image_photo = data["imagePhoto"]

    db.session.commit()
    return jsonify({"product": serialize_product(product, admin_view=True)})


@products_bp.delete("/<int:product_id>")
@require_permission("products")
def delete_product(product_id):
    admin = current_admin()
    product = Product.query.get_or_404(product_id)
    if not _visible_to_admin(product, admin):
        return jsonify({"error": "You can only manage your own products"}), 403

    if ProductReview.query.filter_by(product_id=product.id).first():
        return jsonify({
            "error": "This product has customer reviews and cannot be deleted. Set its stock to 0 to stop selling it."
        }), 409

    # Past order lines keep the product name they were sold under; they just lose the link.
    OrderItem.query.filter_by(product_id=product.id).update({"product_id": None})
    CartItem.query.filter_by(product_id=product.id).delete()
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"})
