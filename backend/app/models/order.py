from datetime import datetime, timedelta
from app.extensions import db

COD = "Cash on Delivery"
GCASH = "GCash"
CARD = "Credit / Debit Card"
RETURN_WINDOW_DAYS = 7

PAYMENT_STATUS_LABELS = {
    "unpaid": "Unpaid",
    "verifying": "Verifying payment",
    "paid": "Paid",
    "refund_pending": "Refund pending",
    "refunded": "Refunded",
}

RETURN_STATUS_LABELS = {
    "none": "",
    "requested": "Return requested",
    "approved": "Return approved",
    "rejected": "Return rejected",
}

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

    payment_status = db.Column(db.String(20), nullable=False, default="unpaid")
    payment_reference = db.Column(db.String(120), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    # Manual GCash: the customer's proof-of-payment screenshot (base64) and when
    # they submitted their reference number. Verified by an admin.
    payment_proof = db.Column(db.Text(length=4294967295), nullable=True)
    payment_submitted_at = db.Column(db.DateTime, nullable=True)

    return_status = db.Column(db.String(20), nullable=False, default="none")
    return_reason = db.Column(db.String(500), nullable=True)
    return_requested_at = db.Column(db.DateTime, nullable=True)
    return_note = db.Column(db.String(500), nullable=True)

    review_rating = db.Column(db.SmallInteger, nullable=True)
    review_comment = db.Column(db.String(500), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")
    history = db.relationship(
        "OrderStatusHistory", backref="order", cascade="all, delete-orphan",
        order_by="OrderStatusHistory.changed_at",
    )
    receipt = db.relationship("Receipt", backref="order", uselist=False, cascade="all, delete-orphan")

    @property
    def is_online_payment(self):
        return self.payment_method != COD

    @property
    def delivered_at(self):
        times = [h.changed_at for h in self.history if h.status == "delivered" and h.changed_at]
        return max(times) if times else None

    @property
    def can_return(self):
        if self.status != "delivered" or self.return_status != "none":
            return False
        delivered = self.delivered_at
        return bool(delivered) and datetime.utcnow() - delivered <= timedelta(days=RETURN_WINDOW_DAYS)

    @property
    def tab(self):
        if self.status == "cancelled" or self.return_status != "none":
            return "return"
        if self.is_online_payment and self.payment_status != "paid":
            return "to_pay"
        if self.status in ("pending_confirmation", "confirmed", "processing"):
            return "to_ship"
        if self.status == "shipped":
            return "to_receive"
        if self.status == "delivered":
            return "to_review" if self.review_rating is None else "completed"
        return "completed"

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
            "paymentStatus": self.payment_status,
            "paymentStatusLabel": PAYMENT_STATUS_LABELS.get(self.payment_status, self.payment_status),
            "paidAt": self.paid_at.isoformat() if self.paid_at else None,
            # For GCash this is the reference number the customer typed in.
            # (For card it is a PayMongo session id, which is not shown.)
            "paymentReference": self.payment_reference if self.payment_method == GCASH else None,
            "paymentSubmittedAt": self.payment_submitted_at.isoformat() if self.payment_submitted_at else None,
            "hasPaymentProof": bool(self.payment_proof),
            "tab": self.tab,
            "canPay": self.status != "cancelled" and self.is_online_payment and self.payment_status in ("unpaid", "verifying"),
            "canChangePayment": self.status == "pending_confirmation" and self.payment_status in ("unpaid", "verifying"),
            "canReceive": self.status == "shipped" and self.return_status == "none",
            "canReview": self.status == "delivered" and self.review_rating is None and self.return_status == "none",
            "canReturn": self.can_return,
            "returnWindowDays": RETURN_WINDOW_DAYS,
            "returnInfo": {
                "status": self.return_status,
                "statusLabel": RETURN_STATUS_LABELS.get(self.return_status, ""),
                "reason": self.return_reason,
                "requestedAt": self.return_requested_at.isoformat() if self.return_requested_at else None,
                "note": self.return_note,
            },
            "review": {
                "rating": self.review_rating,
                "comment": self.review_comment,
                "reviewedAt": self.reviewed_at.isoformat() if self.reviewed_at else None,
            } if self.review_rating is not None else None,
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
