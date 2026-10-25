from datetime import datetime

from sqlalchemy import func

from app.extensions import db
from app.models import Order, ProductReview

MAX_COMMENT_LENGTH = 500


class ReviewError(Exception):
    pass


def clean_entry(entry):
    """Validates one {productId, rating, comment} entry and returns it normalised."""
    try:
        product_id = int(entry.get("productId"))
    except (TypeError, ValueError):
        raise ReviewError("Choose which product you are reviewing")
    try:
        rating = int(entry.get("rating"))
    except (TypeError, ValueError):
        raise ReviewError("Please choose a star rating")
    if rating < 1 or rating > 5:
        raise ReviewError("Rating must be between 1 and 5")
    comment = str(entry.get("comment") or "").strip()
    if len(comment) > MAX_COMMENT_LENGTH:
        raise ReviewError(f"Comments can be at most {MAX_COMMENT_LENGTH} characters")
    return {"productId": product_id, "rating": rating, "comment": comment or None}


def submit_reviews(order, entries):
    """Saves reviews for items of an order that belongs to the signed-in customer.

    Eligibility is decided here from the stored order: it must be delivered, have
    no open return, and each product can be reviewed once per order. The customer
    and order ids come from the order record, not from the request."""
    if order.status != "delivered":
        raise ReviewError("You can review a product once your order has been delivered")
    if order.return_status != "none":
        raise ReviewError("Orders with a return request cannot be reviewed")
    if not entries:
        raise ReviewError("Nothing to review")

    allowed = {item.product_id for item in order.reviewable_items}
    cleaned, seen = [], set()
    for entry in entries:
        item = clean_entry(entry)
        if item["productId"] in seen:
            raise ReviewError("Each product can only be reviewed once")
        if item["productId"] not in allowed:
            raise ReviewError("One of these products is not in this order or was already reviewed")
        seen.add(item["productId"])
        cleaned.append(item)

    now = datetime.utcnow()
    for item in cleaned:
        db.session.add(ProductReview(
            product_id=item["productId"], order_id=order.id, user_id=order.user_id,
            rating=item["rating"], comment=item["comment"], created_at=now,
        ))
    db.session.commit()
    return cleaned


def reviews_for_product(product_id, limit=50):
    """Public review list and summary for one product, delivered orders only."""
    base = (
        db.session.query(ProductReview)
        .join(Order, Order.id == ProductReview.order_id)
        .filter(ProductReview.product_id == product_id, Order.status == "delivered")
    )
    average, count = (
        db.session.query(func.avg(ProductReview.rating), func.count(ProductReview.id))
        .join(Order, Order.id == ProductReview.order_id)
        .filter(ProductReview.product_id == product_id, Order.status == "delivered")
        .one()
    )
    distribution = {str(n): 0 for n in range(1, 6)}
    for rating, total in (
        db.session.query(ProductReview.rating, func.count(ProductReview.id))
        .join(Order, Order.id == ProductReview.order_id)
        .filter(ProductReview.product_id == product_id, Order.status == "delivered")
        .group_by(ProductReview.rating)
        .all()
    ):
        distribution[str(rating)] = int(total)
    rows = base.order_by(ProductReview.created_at.desc(), ProductReview.id.desc()).limit(limit).all()
    return {
        "summary": {
            "average": round(float(average), 1) if count else 0,
            "count": int(count),
            "distribution": distribution,
        },
        "reviews": [r.public_dict() for r in rows],
    }
