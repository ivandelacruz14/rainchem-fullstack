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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "price": float(self.price),
            "stock": self.stock,
            "rating": float(self.rating),
            "reviews": self.reviews,
            "imageGlyph": self.image_glyph,
            "imagePhoto": self.image_photo,
            "shortDesc": self.short_desc,
            "description": self.description,
            "specs": self.specs or [],
            "benefits": self.benefits or [],
            "usage": self.usage_steps or [],
        }
