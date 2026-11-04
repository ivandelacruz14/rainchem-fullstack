"""Reading, validating and applying product changes.

A Head Admin's change is applied straight away. For everyone else the same validated change
is stored as a request (see change_requests.py) and applied only after the Head Admin approves it."""
import re
from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models import CartItem, InventoryMovement, OrderItem, Product, ProductReview
from app.services.inventory import stock_context

CATEGORIES = ["Oils & Fluids", "Coolant", "Filters", "Brakes", "Accessories"]
MAX_PRICE = Decimal("1000000")
LIST_COLUMNS = (("specs", "specs"), ("benefits", "benefits"), ("usage", "usage_steps"))


class ProductChangeError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


SKU_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,39}$")


def read_fields(data, creating, product_id=None):
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
    if "sku" in data or creating:
        sku = str(data.get("sku") or "").strip()
        if sku and not SKU_PATTERN.match(sku):
            errors.append("The SKU can use letters, numbers, dots, dashes and underscores (2 to 40 characters)")
        elif sku:
            clash = Product.query.filter(db.func.lower(Product.sku) == sku.lower())
            if product_id:
                clash = clash.filter(Product.id != product_id)
            if clash.first():
                errors.append("Another product already uses this SKU")
        values["sku"] = sku or None
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


def build_payload(values, data):
    return {
        "values": values,
        "stockReason": (str(data.get("stockReason") or "").strip()[:255]) or None,
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
        **_db_values(payload["values"]),
    )
    db.session.add(product)
    return product


def apply_update(product, payload, admin=None, reference=None):
    # A stock change made here is recorded as a manual adjustment with the reason that was given.
    with stock_context("adjustment", reason=payload.get("stockReason"), admin=admin, reference=reference):
        for column, value in _db_values(payload["values"]).items():
            setattr(product, column, value)
    if payload.get("imagePhoto"):  # only replace the photo if a new one was uploaded
        product.image_photo = payload["imagePhoto"]
    return product


def apply_delete(product):
    check_deletable(product)
    # Past order lines keep the product name they were sold under; they just lose the link.
    OrderItem.query.filter_by(product_id=product.id).update({"product_id": None})
    InventoryMovement.query.filter_by(product_id=product.id).update({"product_id": None})  # the history stays, by name
    CartItem.query.filter_by(product_id=product.id).delete()
    db.session.delete(product)
