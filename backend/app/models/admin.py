from datetime import datetime
from app.extensions import db

ROLE_HEAD_ADMIN = "Head Admin"
ROLE_DISTRIBUTOR = "Distributor"

PERMISSIONS = {
    "manage_products": "Add and edit own products",
    "manage_services": "Add and edit own services and service areas",
    "view_orders": "View orders that contain own products",
    "view_sales": "View sales analytics for own products",
}


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(60), nullable=False, default=ROLE_HEAD_ADMIN)
    permissions = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_distributor(self):
        return self.role == ROLE_DISTRIBUTOR

    @property
    def is_head(self):
        # Accounts created before roles existed ("Super Admin", "Admin", ...)
        # keep the full access they always had.
        return not self.is_distributor

    def has_permission(self, key):
        if self.is_head:
            return True
        return bool(self.is_active and key in (self.permissions or []))

    def effective_permissions(self):
        if self.is_head:
            return list(PERMISSIONS.keys())
        return [key for key in (self.permissions or []) if key in PERMISSIONS]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "isHead": self.is_head,
            "isActive": bool(self.is_active),
            "permissions": self.effective_permissions(),
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
