from datetime import datetime
from app.extensions import db


class ProductReview(db.Model):
    """One review per product per order. Customer, product and order are always
    taken from the server side order record, never from the browser."""

    __tablename__ = "product_reviews"
    __table_args__ = (db.UniqueConstraint("order_id", "product_id", name="uq_review_order_product"),)

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.SmallInteger, nullable=False)
    comment = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order = db.relationship("Order", backref=db.backref("reviews", cascade="all, delete-orphan"))
    user = db.relationship("User")
    product = db.relationship("Product")

    def public_dict(self):
        """What visitors see: a first name and last initial, never an email."""
        full = (self.user.name if self.user else "").strip().split()
        author = "Customer"
        if full:
            author = full[0] + (f" {full[-1][0]}." if len(full) > 1 else "")
        return {
            "id": self.id,
            "rating": self.rating,
            "comment": self.comment,
            "author": author,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
