from flask import Blueprint, request, jsonify
from sqlalchemy import func

from app.extensions import db
from app.models import Admin, ChangeRequest, Product
from app.services import change_requests
from app.services import product_changes as changes
from app.services.catalog import serialize_product, serialize_products
from app.services.reviews import reviews_for_product
from app.utils.auth_decorators import current_admin, require_permission

products_bp = Blueprint("products", __name__, url_prefix="/api/products")


def _pending_response(admin, kind, product, payload):
    """Anyone except a Head Admin only sends a request; nothing changes until it is approved."""
    request_row = change_requests.submit(admin, kind, product, payload)
    return jsonify({
        "pendingApproval": True,
        "message": "Sent to the Head Admin for approval. Nothing changes until it is approved.",
        "request": change_requests.to_dict(request_row),
    }), 202


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
    if admin.is_scoped:
        query = query.filter(Product.owner_admin_id == admin.id)
    products = serialize_products(query.order_by(Product.id).all(), admin_view=True)
    pending = db.session.query(ChangeRequest.product_id, func.count(ChangeRequest.id)).filter(
        ChangeRequest.status == "pending", ChangeRequest.product_id.isnot(None)
    )
    if not admin.is_head:
        pending = pending.filter(ChangeRequest.requested_by == admin.id)
    counts = dict(pending.group_by(ChangeRequest.product_id).all())
    for product in products:
        product["pendingRequests"] = counts.get(product["id"], 0)
    payload = {"products": products}
    if not admin.is_scoped:
        payload["distributors"] = [
            {"id": a.id, "name": a.name} for a in Admin.query.order_by(Admin.name).all() if a.is_scoped
        ]
    return jsonify(payload)


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
    values, errors = changes.read_fields(data, creating=True)
    if errors:
        return jsonify({"error": ". ".join(errors)}), 400
    try:
        owner_id = changes.resolve_owner(data, admin)
    except changes.ProductChangeError as error:
        return jsonify({"error": str(error)}), error.status

    payload = changes.build_payload(values, data, owner_id, owner_given=True)
    if not admin.is_head:
        return _pending_response(admin, "product_create", None, payload)

    product = changes.apply_create(payload)
    db.session.commit()
    return jsonify({"product": serialize_product(product, admin_view=True)}), 201


@products_bp.put("/<int:product_id>")
@require_permission("products")
def update_product(product_id):
    admin = current_admin()
    product = Product.query.get_or_404(product_id)
    if not changes.can_manage(product, admin):
        return jsonify({"error": "You can only manage your own products"}), 403

    data = request.get_json() or {}
    values, errors = changes.read_fields(data, creating=False)
    if errors:
        return jsonify({"error": ". ".join(errors)}), 400
    try:
        owner_id = changes.resolve_owner(data, admin, current_owner=product.owner_admin_id)
    except changes.ProductChangeError as error:
        return jsonify({"error": str(error)}), error.status

    payload = changes.build_payload(values, data, owner_id, owner_given=True)
    if not admin.is_head:
        return _pending_response(admin, "product_update", product, payload)

    changes.apply_update(product, payload)
    db.session.commit()
    return jsonify({"product": serialize_product(product, admin_view=True)})


@products_bp.delete("/<int:product_id>")
@require_permission("products")
def delete_product(product_id):
    admin = current_admin()
    product = Product.query.get_or_404(product_id)
    if not changes.can_manage(product, admin):
        return jsonify({"error": "You can only manage your own products"}), 403
    try:
        changes.check_deletable(product)
    except changes.ProductChangeError as error:
        return jsonify({"error": str(error)}), error.status

    if not admin.is_head:
        return _pending_response(admin, "product_delete", product, {"values": {}})

    changes.apply_delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"})
