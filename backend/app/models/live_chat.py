from datetime import datetime
from app.extensions import db

TOPICS = {
    "order": "Order help",
    "product": "Product question",
    "payment": "Payment concern",
    "account": "Account issue",
    "ai": "Question from the AI assistant",
    "other": "Something else",
}


class LiveConversation(db.Model):
    """One conversation per customer. It is reused for every later message, so the admin
    always finds a customer's whole history in one place."""

    __tablename__ = "live_conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    topic = db.Column(db.String(20), nullable=False, default="other")
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User")
    order = db.relationship("Order")
    messages = db.relationship(
        "LiveMessage", backref="conversation", cascade="all, delete-orphan", order_by="LiveMessage.id",
    )


class LiveMessage(db.Model):
    """sent = stored on the server. delivered = the other side's app received it.
    read = the other side opened the conversation. A deleted message keeps only a marker."""

    __tablename__ = "live_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("live_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_type = db.Column(db.String(10), nullable=False)  # user | admin
    sender_admin_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    sender_name = db.Column(db.String(120), nullable=False, default="")
    kind = db.Column(db.String(10), nullable=False, default="text")  # text | context (handed over from the AI chat)
    body = db.Column(db.Text, nullable=False, default="")
    meta = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime, nullable=True)
    read_at = db.Column(db.DateTime, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.String(10), nullable=True)  # user | admin
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @property
    def status(self):
        if self.deleted_at:
            return "deleted"
        if self.read_at:
            return "read"
        if self.delivered_at:
            return "delivered"
        return "sent"

    def to_dict(self, viewer):
        deleted = self.deleted_at is not None
        return {
            "id": self.id,
            "sender": self.sender_type,
            "senderName": self.sender_name,
            "mine": self.sender_type == viewer,
            "kind": self.kind,
            "body": None if deleted else self.body,
            "meta": None if deleted else self.meta,
            "deleted": deleted,
            "deletedBy": self.deleted_by if deleted else None,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "deliveredAt": self.delivered_at.isoformat() if self.delivered_at else None,
            "readAt": self.read_at.isoformat() if self.read_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
