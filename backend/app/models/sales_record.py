from datetime import datetime
from app.extensions import db


class SalesRecord(db.Model):
    """One row per product line of an order. Rows are written from the order, never typed in by hand,
    and money fields are a snapshot of what was charged at the time."""

    __tablename__ = "sales_records"

    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False, unique=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    order_number = db.Column(db.String(40), nullable=False, index=True)
    transaction_ref = db.Column(db.String(120), nullable=False, default="")
    sold_at = db.Column(db.DateTime, nullable=False, index=True)

    customer_id = db.Column(db.Integer, nullable=True)
    customer_name = db.Column(db.String(150), nullable=False, default="")

    product_id = db.Column(db.Integer, nullable=True, index=True)
    product_name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(40), nullable=True)
    category = db.Column(db.String(80), nullable=True)

    quantity = db.Column(db.Integer, nullable=False)
    list_unit_price = db.Column(db.Numeric(10, 2), nullable=False)   # before discounts
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)        # what the customer paid per unit
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)          # list price x quantity
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)        # subtotal - discount
    shipping_share = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    order_total = db.Column(db.Numeric(10, 2), nullable=False)       # final transaction total

    payment_method = db.Column(db.String(60), nullable=False, default="")
    payment_status = db.Column(db.String(20), nullable=False, default="")
    order_status = db.Column(db.String(30), nullable=False, default="")
    fulfillment_status = db.Column(db.String(30), nullable=False, default="")
    refund_status = db.Column(db.String(20), nullable=False, default="none")
    return_status = db.Column(db.String(20), nullable=False, default="none")
    state = db.Column(db.String(12), nullable=False, default="pending", index=True)  # pending | completed | cancelled | refunded | returned
    notes = db.Column(db.String(500), nullable=True)
    overrides = db.Column(db.JSON, nullable=True)  # controlled corrections: {"sku": "...", "category": "...", "notes": "..."}

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        money = lambda v: float(v) if v is not None else 0.0
        return {
            "id": self.id,
            "orderId": self.order_id,
            "orderNumber": self.order_number,
            "transactionRef": self.transaction_ref,
            "soldAt": self.sold_at.isoformat() if self.sold_at else None,
            "customerId": self.customer_id,
            "customerName": self.customer_name,
            "productId": self.product_id,
            "productName": self.product_name,
            "sku": self.sku,
            "category": self.category,
            "quantity": self.quantity,
            "listUnitPrice": money(self.list_unit_price),
            "unitPrice": money(self.unit_price),
            "subtotal": money(self.subtotal),
            "discountAmount": money(self.discount_amount),
            "lineTotal": money(self.line_total),
            "shippingShare": money(self.shipping_share),
            "taxAmount": money(self.tax_amount),
            "orderTotal": money(self.order_total),
            "paymentMethod": self.payment_method,
            "paymentStatus": self.payment_status,
            "orderStatus": self.order_status,
            "fulfillmentStatus": self.fulfillment_status,
            "refundStatus": self.refund_status,
            "returnStatus": self.return_status,
            "state": self.state,
            "notes": self.notes,
            "corrected": bool(self.overrides),
        }
