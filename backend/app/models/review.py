from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.orm import column_property

from app.extensions import db
from app.models.product import Product

MAX_COMMENT_LENGTH = 500


class ProductReview(db.Model):
    __tablename__ = "product_reviews"
    __table_args__ = (
        db.UniqueConstraint("order_id", "product_id", name="uq_review_order_product"),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.SmallInteger, nullable=False)
    comment = db.Column(db.String(MAX_COMMENT_LENGTH), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")

    def to_dict(self):
        full_name = (self.user.name if self.user else "") or "Customer"
        first, *rest = full_name.split()
        reviewer = f"{first} {rest[-1][0]}." if rest else first
        return {
            "id": self.id,
            "productId": self.product_id,
            "rating": self.rating,
            "comment": self.comment,
            "reviewer": reviewer,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


Product.review_count = column_property(
    select(func.count(ProductReview.id))
    .where(ProductReview.product_id == Product.id)
    .correlate_except(ProductReview)
    .scalar_subquery()
)
Product.review_average = column_property(
    select(func.coalesce(func.avg(ProductReview.rating), 0))
    .where(ProductReview.product_id == Product.id)
    .correlate_except(ProductReview)
    .scalar_subquery()
)
