from datetime import datetime

from sqlalchemy.dialects.mysql import LONGBLOB

from app.extensions import db


class OrderScan(db.Model):
    """Every barcode scan at delivery, accepted or rejected, with who scanned it and when."""

    __tablename__ = "order_scans"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    rider_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    code = db.Column(db.String(64), nullable=False)
    result = db.Column(db.String(12), nullable=False)  # accepted | rejected
    reason = db.Column(db.String(120), nullable=True)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)


class DeliveryProof(db.Model):
    """One photo per delivered order, kept in the database like chat images. It cannot be replaced."""

    __tablename__ = "delivery_proofs"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    rider_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    data = db.deferred(db.Column(db.LargeBinary().with_variant(LONGBLOB(), "mysql"), nullable=False))
    mime = db.Column(db.String(30), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DeliveryReceiptUpload(db.Model):
    """A completed delivery receipt uploaded by the rider. Kept as a history: a rejected receipt is followed by a new row."""

    __tablename__ = "delivery_receipt_uploads"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    rider_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    data = db.deferred(db.Column(db.LargeBinary().with_variant(LONGBLOB(), "mysql"), nullable=False))
    mime = db.Column(db.String(30), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    signature = db.deferred(db.Column(db.LargeBinary().with_variant(LONGBLOB(), "mysql"), nullable=False))
    printed_name = db.Column(db.String(120), nullable=False)
    acknowledged_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending_verification", index=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reject_reason = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

