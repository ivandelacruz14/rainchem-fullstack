from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Product, ProductReview
from app.services import review_service as reviews
from app.utils.auth_decorators import require_user, current_user_id

reviews_bp = Blueprint("reviews", __name__, url_prefix="/api/products")

PAGE_LIMIT = 50


@reviews_bp.get("/<int:product_id>/reviews")
def list_reviews(product_id):
    Product.query.get_or_404(product_id)
    items = (
        ProductReview.query.filter_by(product_id=product_id)
        .order_by(ProductReview.created_at.desc())
        .limit(PAGE_LIMIT)
        .all()
    )
    return jsonify({
        "summary": reviews.rating_summary(product_id),
        "reviews": [r.to_dict() for r in items],
    })


@reviews_bp.get("/<int:product_id>/reviews/eligibility")
@require_user
def review_eligibility(product_id):
    Product.query.get_or_404(product_id)
    user_id = current_user_id()
    if reviews.eligible_order_for(user_id, product_id):
        return jsonify({"canReview": True})
    if reviews.has_delivered_purchase(user_id, product_id):
        return jsonify({"canReview": False, "reason": "You already reviewed this product."})
    return jsonify({
        "canReview": False,
        "reason": "Only customers who received this product can review it.",
    })


@reviews_bp.post("/<int:product_id>/reviews")
@require_user
def create_review(product_id):
    Product.query.get_or_404(product_id)
    user_id = current_user_id()
    data = request.get_json() or {}

    try:
        rating = reviews.clean_rating(data.get("rating"))
        comment = reviews.clean_comment(data.get("comment"))
    except reviews.ReviewError as error:
        return jsonify({"error": error.message}), error.status

    order = reviews.eligible_order_for(user_id, product_id)
    if order is None:
        status = 409 if reviews.has_delivered_purchase(user_id, product_id) else 403
        message = (
            "You already reviewed this product." if status == 409
            else "Only customers who received this product can review it."
        )
        return jsonify({"error": message}), status

    review = reviews.add_review(user_id, order, product_id, rating, comment)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "You already reviewed this product."}), 409
    return jsonify({
        "review": review.to_dict(),
        "summary": reviews.rating_summary(product_id),
    }), 201
