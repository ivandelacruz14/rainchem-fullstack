from datetime import datetime
from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    rating = db.Column(db.Numeric(2, 1), nullable=False, default=4.5)
    reviews = db.Column(db.Integer, nullable=False, default=0)
    image_glyph = db.Column(db.String(60), nullable=True)
    image_photo = db.Column(db.Text(length=4294967295), nullable=True)
    short_desc = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    specs = db.Column(db.JSON, nullable=True)
    benefits = db.Column(db.JSON, nullable=True)
    usage_steps = db.Column(db.JSON, nullable=True)
    owner_admin_id = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self, average_rating=0.0, review_count=0, sale=None):
        """Public view. Rating and review count come from real review records
        (see services/catalog.py); the old rating/reviews columns are not shown."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "price": float(self.price),
            "stock": self.stock,
            "rating": round(float(average_rating or 0), 1),
            "reviews": int(review_count or 0),
            **self._sale_fields(sale),
            "imageGlyph": self.image_glyph,
            "imagePhoto": self.image_photo,
            "shortDesc": self.short_desc,
            "description": self.description,
            "specs": self.specs or [],
            "benefits": self.benefits or [],
            "usage": self.usage_steps or [],
        }

    def to_admin_dict(self, average_rating=0.0, review_count=0, sale=None):
        data = self.to_dict(average_rating, review_count, sale)
        data["ownerId"] = self.owner_admin_id
        return data

    def _sale_fields(self, sale):
        """`price` always stays the regular price; the sale price is shown next to it."""
        if sale is None:
            return {"onSale": False, "salePercent": 0, "salePrice": None, "saleEndsAt": None, "saleEndDate": None, "saleLabel": None}
        from app.services.pricing import unit_price_after_discount
        from app.services.promotions import local_days
        rate = sale.discount_percent / 100
        return {
            "onSale": True,
            "salePercent": sale.discount_percent,
            "salePrice": float(unit_price_after_discount(self.price, rate)),
            "saleEndsAt": sale.ends_at.isoformat(),
            "saleEndDate": local_days(sale)[1].isoformat(),  # last day of the sale, shop time
            "saleLabel": sale.label,
        }
