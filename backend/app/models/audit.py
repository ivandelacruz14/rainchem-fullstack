from datetime import datetime
from app.extensions import db


class AuditLog(db.Model):
    """Who changed what, when, from what to what, and why. Entries are only ever added."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    admin_name = db.Column(db.String(120), nullable=False, default="")
    action = db.Column(db.String(60), nullable=False, index=True)
    entity_type = db.Column(db.String(40), nullable=False)
    entity_id = db.Column(db.String(60), nullable=False)
    old_value = db.Column(db.JSON, nullable=True)
    new_value = db.Column(db.JSON, nullable=True)
    reason = db.Column(db.String(500), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "at": self.created_at.isoformat() if self.created_at else None,
            "admin": self.admin_name,
            "action": self.action,
            "entityType": self.entity_type,
            "entityId": self.entity_id,
            "old": self.old_value,
            "new": self.new_value,
            "reason": self.reason,
        }
