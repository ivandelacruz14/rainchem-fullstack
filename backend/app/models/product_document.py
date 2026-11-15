from datetime import datetime
from app.extensions import db

DOC_TYPES = {
    "technical_data_sheet": "Technical data sheet",
    "manufacturer_recommendation": "Manufacturer recommendation",
    "safety_data_sheet": "Safety data sheet",
    "product_listing": "Product listing",
}
FACT_KEYS = ("viscosity_grades", "standards", "applications", "equipment", "engine_types", "compatible_with", "not_for", "warnings")


class ProductDocument(db.Model):
    """Product documentation the assistant may use. It is used only when a Head Admin has verified it
    and it is marked as authorised. Editing a document withdraws its verification until it is checked again."""

    __tablename__ = "product_documents"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    doc_type = db.Column(db.String(32), nullable=False, default="technical_data_sheet")
    version = db.Column(db.String(40), nullable=True)
    source = db.Column(db.String(255), nullable=True)           # where it came from: file name, manufacturer reference or link
    content = db.Column(db.Text, nullable=False)
    facts = db.Column(db.JSON, nullable=True)                   # the specifications, as lists, that matching relies on
    verified = db.Column(db.Boolean, nullable=False, default=False)
    authorized = db.Column(db.Boolean, nullable=False, default=False)
    verified_by = db.Column(db.String(120), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = db.relationship("Product")

    @property
    def usable(self):
        return bool(self.verified and self.authorized)

    def to_dict(self, with_content=True):
        data = {
            "id": self.id, "productId": self.product_id, "productName": self.product.name if self.product else None,
            "title": self.title, "docType": self.doc_type, "docTypeLabel": DOC_TYPES.get(self.doc_type, self.doc_type),
            "version": self.version, "source": self.source, "facts": self.facts or {},
            "verified": bool(self.verified), "authorized": bool(self.authorized), "usable": self.usable,
            "verifiedBy": self.verified_by, "verifiedAt": self.verified_at.isoformat() if self.verified_at else None,
            "createdBy": self.created_by, "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
        if with_content:
            data["content"] = self.content
        return data


class RecommendationLog(db.Model):
    """What the recommender did, without the customer's own words or identity."""

    __tablename__ = "recommendation_logs"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    status = db.Column(db.String(20), nullable=False)       # needs_info | matches | insufficient
    application = db.Column(db.String(30), nullable=True)
    slots_given = db.Column(db.JSON, nullable=True)          # which requirements were known, not their text
    product_ids = db.Column(db.JSON, nullable=True)
    document_ids = db.Column(db.JSON, nullable=True)
    top_score = db.Column(db.Float, nullable=True)
    elapsed_ms = db.Column(db.Integer, nullable=True)
