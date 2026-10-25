"""Reading, validating and applying product changes.

A Head Admin's change is applied straight away. For everyone else the same validated change
is stored as a request (see change_requests.py) and applied only after the Head Admin approves it."""
from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models import Admin, CartItem, OrderItem, Product, ProductReview

CATEGORIES = ["Oils & Fluids", "Coolant", "Filters", "Brakes", "Accessories"]
MAX_PRICE = Decimal("1000000")
LIST_COLUMNS = (("specs", "specs"), ("benefits", "benefits"), ("usage", "usage_steps"))


class ProductChangeError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def can_manage(product, admin):
    return not admin.is_scoped or product.owner_admin_id == admin.id


def read_fields(data, creating):
    """Returns (values, errors). Only fields present in the request are returned when updating.
    Values are JSON friendly (the price is kept as text) so they can be stored in a request."""
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
            values["price"] = str(price.quantize(Decimal("0.01")))
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
    for key, column in LIST_COLUMNS:
        if key in data or creating:
            items = data.get(key) or []
            if not isinstance(items, list):
                errors.append(f"{key} must be a list")
            else:
                values[column] = [str(i).strip() for i in items if str(i).strip()]
    return values, errors


def resolve_owner(data, admin, current_owner=None):
    """Distributors always own what they make. Anyone else may assign an owner."""
    if admin.is_scoped:
        return admin.id if current_owner is None else current_owner
    if "ownerId" not in data:
        return current_owner
    owner_id = data.get("ownerId")
    if owner_id in (None, "", 0):
        return None
    owner = db.session.get(Admin, int(owner_id))
    if owner is None:
        raise ProductChangeError("The selected distributor does not exist")
    return owner.id


def build_payload(values, data, owner_id, owner_given):
    return {
        "values": values,
        "ownerId": owner_id,
        "ownerSet": owner_given,
        "imageGlyph": data.get("imageGlyph") or None,
        "imagePhoto": data.get("imagePhoto") or None,
    }


def _db_values(values):
    result = dict(values)
    if "price" in result:
        result["price"] = Decimal(result["price"])
    return result


def check_deletable(product):
    if ProductReview.query.filter_by(product_id=product.id).first():
        raise ProductChangeError(
            "This product has customer reviews and cannot be deleted. Set its stock to 0 to stop selling it.", 409
        )


def apply_create(payload):
    product = Product(
        image_glyph=payload.get("imageGlyph") or "oil-synthetic",
        image_photo=payload.get("imagePhoto"),
        owner_admin_id=payload.get("ownerId"),
        **_db_values(payload["values"]),
    )
    db.session.add(product)
    return product


def apply_update(product, payload):
    for column, value in _db_values(payload["values"]).items():
        setattr(product, column, value)
    if payload.get("ownerSet"):
        product.owner_admin_id = payload.get("ownerId")
    if payload.get("imagePhoto"):  # only replace the photo if a new one was uploaded
        product.image_photo = payload["imagePhoto"]
    return product


def apply_delete(product):
    check_deletable(product)
    # Past order lines keep the product name they were sold under; they just lose the link.
    OrderItem.query.filter_by(product_id=product.id).update({"product_id": None})
    CartItem.query.filter_by(product_id=product.id).delete()
    db.session.delete(product)
