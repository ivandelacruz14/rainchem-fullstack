from datetime import datetime
from app.extensions import db

MOVEMENT_TYPES = {
    "opening": "Opening stock",
    "received": "Stock received",
    "sale": "Issued to an order",
    "return": "Returned by customer",
    "cancel_restore": "Restored after cancellation",
    "adjustment": "Manual adjustment",
    "write_off": "Damaged or written off",
    "untracked": "Change with no recorded process",
}


class InventoryMovement(db.Model):
    """Every change to a product's stock. The sum of a product's movements is its expected stock."""

    __tablename__ = "inventory_movements"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    product_name = db.Column(db.String(200), nullable=False, default="")
    movement_type = db.Column(db.String(24), nullable=False)
    quantity_change = db.Column(db.Integer, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    reference = db.Column(db.String(120), nullable=True)
    reason = db.Column(db.String(255), nullable=True)
    actor_admin_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    actor_name = db.Column(db.String(120), nullable=False, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "productId": self.product_id,
            "productName": self.product_name,
            "type": self.movement_type,
            "typeLabel": MOVEMENT_TYPES.get(self.movement_type, self.movement_type),
            "change": self.quantity_change,
            "orderId": self.order_id,
            "reference": self.reference,
            "reason": self.reason,
            "actor": self.actor_name,
            "at": self.created_at.isoformat() if self.created_at else None,
        }


ALERT_CATEGORIES = {
    "stock_mismatch": "Stock does not match history",
    "negative_stock": "Negative stock",
    "duplicate_movement": "Duplicate stock movement",
    "order_processed_twice": "Order processed more than once",
    "paid_without_reference": "Paid without a payment reference",
    "cancelled_no_restore": "Stock not restored",
    "adjustment_unexplained": "Adjustment without explanation",
    "untracked_change": "Stock changed outside a recorded process",
    "sales_record_mismatch": "Sales record does not match its order",
}


class InventoryAlert(db.Model):
    """A rule-based finding for an administrator to review. Nothing is changed automatically."""

    __tablename__ = "inventory_alerts"

    id = db.Column(db.Integer, primary_key=True)
    fingerprint = db.Column(db.String(190), nullable=False, unique=True)
    category = db.Column(db.String(30), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    product_name = db.Column(db.String(200), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    order_number = db.Column(db.String(40), nullable=True)
    expected_value = db.Column(db.String(80), nullable=True)
    recorded_value = db.Column(db.String(80), nullable=True)
    difference = db.Column(db.String(80), nullable=True)
    explanation = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open")  # open | under_review | resolved
    assigned_admin_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    assigned_name = db.Column(db.String(120), nullable=True)
    resolution_note = db.Column(db.Text, nullable=True)
    resolved_by = db.Column(db.String(120), nullable=True)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "categoryLabel": ALERT_CATEGORIES.get(self.category, self.category),
            "productId": self.product_id,
            "productName": self.product_name,
            "orderId": self.order_id,
            "orderNumber": self.order_number,
            "expected": self.expected_value,
            "recorded": self.recorded_value,
            "difference": self.difference,
            "explanation": self.explanation,
            "status": self.status,
            "assignedTo": self.assigned_name,
            "resolutionNote": self.resolution_note,
            "resolvedBy": self.resolved_by,
            "detectedAt": self.detected_at.isoformat() if self.detected_at else None,
            "resolvedAt": self.resolved_at.isoformat() if self.resolved_at else None,
        }
