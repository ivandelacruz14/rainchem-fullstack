from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import Product
from app.utils.auth_decorators import require_admin

products_bp = Blueprint("products", __name__, url_prefix="/api/products")


@products_bp.get("")
def list_products():
    category = request.args.get("category")
    query = Product.query
    if category and category != "All":
        query = query.filter_by(category=category)
    products = query.order_by(Product.id).all()
    return jsonify({"products": [p.to_dict() for p in products]})


@products_bp.get("/<int:product_id>")
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({"product": product.to_dict()})


@products_bp.post("")
@require_admin
def create_product():
    data = request.get_json() or {}
    product = Product(
        name=data.get("name", ""),
        category=data.get("category", "Oils & Fluids"),
        price=data.get("price", 0),
        stock=data.get("stock", 0),
        rating=data.get("rating", 4.5),
        reviews=data.get("reviews", 0),
        image_glyph=data.get("imageGlyph", "oil-synthetic"),
        image_photo=data.get("imagePhoto"),
        short_desc=data.get("shortDesc", ""),
        description=data.get("description", ""),
        specs=data.get("specs", []),
        benefits=data.get("benefits", []),
        usage_steps=data.get("usage", []),
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({"product": product.to_dict()}), 201


@products_bp.put("/<int:product_id>")
@require_admin
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json() or {}

    for field, column in [
        ("name", "name"), ("category", "category"), ("price", "price"),
        ("stock", "stock"), ("rating", "rating"), ("shortDesc", "short_desc"),
        ("description", "description"), ("specs", "specs"),
        ("benefits", "benefits"),
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
@require_admin
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"})
