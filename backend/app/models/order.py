from datetime import datetime
from app.extensions import db

ORDER_STATUSES = [
    "pending_confirmation",
    "confirmed",
    "processing",
    "shipped",
    "delivered",
    "cancelled",
]

STATUS_LABELS = {
    "pending_confirmation": "Pending Confirmation",
    "confirmed": "Confirmed",
    "processing": "Processing",
    "shipped": "Shipped",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
}


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(40), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="pending_confirmation")
    tracking_number = db.Column(db.String(40), nullable=False)

    customer_name = db.Column(db.String(150), nullable=False)
    customer_phone = db.Column(db.String(30), nullable=False)
    customer_email = db.Column(db.String(180), nullable=False)

    address_line1 = db.Column(db.String(200), nullable=False)
    address_city = db.Column(db.String(100), nullable=False)
    address_province = db.Column(db.String(100), nullable=False)
    address_region = db.Column(db.String(100), nullable=False)
    address_zip = db.Column(db.String(20), nullable=False)

    payment_method = db.Column(db.String(60), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    shipping_fee = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")
    history = db.relationship(
        "OrderStatusHistory", backref="order", cascade="all, delete-orphan",
        order_by="OrderStatusHistory.changed_at",
    )
    receipt = db.relationship("Receipt", backref="order", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "orderNumber": self.order_number,
            "userId": self.user_id,
            "status": self.status,
            "statusLabel": STATUS_LABELS.get(self.status, self.status),
            "trackingNumber": self.tracking_number,
            "customer": {
                "name": self.customer_name,
                "phone": self.customer_phone,
                "email": self.customer_email,
            },
            "address": {
                "line1": self.address_line1,
                "city": self.address_city,
                "province": self.address_province,
                "region": self.address_region,
                "zip": self.address_zip,
            },
            "paymentMethod": self.payment_method,
            "subtotal": float(self.subtotal),
            "shippingFee": float(self.shipping_fee),
            "total": float(self.total),
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "confirmedAt": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "cancelledAt": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "canCancel": self.status == "pending_confirmation",
            "hasReceipt": self.receipt is not None,
            "items": [item.to_dict() for item in self.items],
            "history": [h.to_dict() for h in self.history],
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    product_name = db.Column(db.String(200), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_rate = db.Column(db.Numeric(4, 2), nullable=False, default=0)
    quantity = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "productId": self.product_id,
            "name": self.product_name,
            "unitPrice": float(self.unit_price),
            "discountRate": float(self.discount_rate),
            "quantity": self.quantity,
            "lineTotal": round(float(self.unit_price) * self.quantity, 2),
        }


class OrderStatusHistory(db.Model):
    __tablename__ = "order_status_history"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    status = db.Column(db.String(40), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "status": self.status,
            "statusLabel": STATUS_LABELS.get(self.status, self.status),
            "changedAt": self.changed_at.isoformat() if self.changed_at else None,
        }


class Receipt(db.Model):
    __tablename__ = "receipts"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, unique=True)
    receipt_number = db.Column(db.String(40), nullable=False, unique=True)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    items_snapshot = db.Column(db.JSON, nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    shipping_fee = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)

    def to_dict(self):
        return {
            "receiptNumber": self.receipt_number,
            "issuedAt": self.issued_at.isoformat() if self.issued_at else None,
            "items": self.items_snapshot,
            "subtotal": float(self.subtotal),
            "shippingFee": float(self.shipping_fee),
            "total": float(self.total),
        }
