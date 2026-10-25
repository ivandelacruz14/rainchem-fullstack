from datetime import datetime
from app.extensions import db
from app.services.permissions import PERMISSIONS, is_head_role, clean_permissions


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(60), nullable=False, default="Head Admin")
    # Permission keys granted to non-head accounts (see services/permissions.py).
    permissions = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_head(self):
        return is_head_role(self.role)

    def permission_keys(self):
        if self.is_head:
            return list(PERMISSIONS)
        return clean_permissions(self.permissions)

    def has_permission(self, key):
        return self.is_head or key in self.permission_keys()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "isHead": self.is_head,
            "isActive": bool(self.is_active),
            "permissions": self.permission_keys(),
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
