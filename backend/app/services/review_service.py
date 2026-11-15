from sqlalchemy import func

from app.extensions import db
from app.models import Order, OrderItem, ProductReview
from app.models.review import MAX_COMMENT_LENGTH

REVIEWABLE_RETURN_STATES = ("none", "rejected")


class ReviewError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def clean_rating(value):
    try:
        rating = int(value)
    except (TypeError, ValueError):
        raise ReviewError("Please choose a star rating from 1 to 5")
    if rating < 1 or rating > 5:
        raise ReviewError("Rating must be between 1 and 5")
    return rating


def clean_comment(value):
    comment = str(value or "").strip()
    if len(comment) > MAX_COMMENT_LENGTH:
        raise ReviewError(f"Comments can be at most {MAX_COMMENT_LENGTH} characters")
    return comment or None


def eligible_order_for(user_id, product_id):
    """Oldest delivered order of this user that contains the product and has
    no review for it yet. Eligibility is always decided here, never by the client."""
    reviewed_order_ids = db.session.query(ProductReview.order_id).filter(
        ProductReview.user_id == user_id, ProductReview.product_id == product_id,
    )
    return (
        Order.query
        .join(OrderItem, OrderItem.order_id == Order.id)
        .filter(
            Order.user_id == user_id,
            Order.status == "delivered",
            Order.return_status.in_(REVIEWABLE_RETURN_STATES),
            OrderItem.product_id == product_id,
            ~Order.id.in_(reviewed_order_ids),
        )
        .order_by(Order.created_at.asc())
        .first()
    )


def has_delivered_purchase(user_id, product_id):
    return db.session.query(Order.id).join(OrderItem, OrderItem.order_id == Order.id).filter(
        Order.user_id == user_id, Order.status == "delivered",
        Order.return_status.in_(REVIEWABLE_RETURN_STATES), OrderItem.product_id == product_id,
    ).first() is not None


def add_review(user_id, order, product_id, rating, comment):
    review = ProductReview(
        product_id=product_id, order_id=order.id, user_id=user_id,
        rating=rating, comment=comment,
    )
    db.session.add(review)
    return review


def add_reviews_for_order(order, rating, comment):
    """Order-level review from My Orders: one review per product in the order."""
    existing = {
        pid for (pid,) in db.session.query(ProductReview.product_id).filter_by(order_id=order.id)
    }
    created = []
    for item in order.items:
        if item.product_id and item.product_id not in existing:
            existing.add(item.product_id)
            created.append(add_review(order.user_id, order, item.product_id, rating, comment))
    return created


def rating_summary(product_id):
    rows = (
        db.session.query(ProductReview.rating, func.count(ProductReview.id))
        .filter(ProductReview.product_id == product_id)
        .group_by(ProductReview.rating)
        .all()
    )
    distribution = {str(star): 0 for star in range(1, 6)}
    total = 0
    weighted = 0
    for rating, count in rows:
        distribution[str(rating)] = count
        total += count
        weighted += rating * count
    average = round(weighted / total, 1) if total else None
    return {"average": average, "count": total, "distribution": distribution}
