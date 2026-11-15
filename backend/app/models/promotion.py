from datetime import datetime
from app.extensions import db


class ProductSale(db.Model):
    """A percentage-off sale on one product for a window of time (stored in UTC)."""

    __tablename__ = "product_sales"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    discount_percent = db.Column(db.SmallInteger, nullable=False)
    starts_at = db.Column(db.DateTime, nullable=False)
    ends_at = db.Column(db.DateTime, nullable=False)
    label = db.Column(db.String(60), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")

    def status(self, now=None):
        now = now or datetime.utcnow()
        if not self.is_active or now >= self.ends_at:
            return "ended"
        return "active" if self.starts_at <= now else "scheduled"
