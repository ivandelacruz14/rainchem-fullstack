from datetime import datetime
from app.extensions import db

BOOKING_STATUSES = ["requested", "confirmed", "completed", "cancelled"]


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80), nullable=True)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    owner_admin_id = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    areas = db.relationship(
        "ServiceArea", backref="service", cascade="all, delete-orphan",
        order_by="ServiceArea.area_name",
    )

    def to_dict(self, include_unavailable=True):
        areas = self.areas if include_unavailable else [a for a in self.areas if a.is_available]
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "requirements": self.requirements,
            "isActive": bool(self.is_active),
            "ownerAdminId": self.owner_admin_id,
            "areas": [a.to_dict() for a in areas],
        }


class ServiceArea(db.Model):
    __tablename__ = "service_areas"
    __table_args__ = (
        db.UniqueConstraint("service_id", "area_name", name="uq_service_area_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False, index=True)
    area_name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    is_available = db.Column(db.Boolean, nullable=False, default=True)
    note = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "serviceId": self.service_id,
            "areaName": self.area_name,
            "price": float(self.price),
            "isAvailable": bool(self.is_available),
            "note": self.note,
        }


class ServiceBooking(db.Model):
    __tablename__ = "service_bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey("service_areas.id"), nullable=True)
    service_name = db.Column(db.String(160), nullable=False)
    area_name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    contact_name = db.Column(db.String(150), nullable=False)
    contact_phone = db.Column(db.String(30), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    preferred_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="requested")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self, include_contact=True):
        data = {
            "id": self.id,
            "serviceId": self.service_id,
            "serviceName": self.service_name,
            "areaName": self.area_name,
            "price": float(self.price),
            "preferredDate": self.preferred_date.isoformat() if self.preferred_date else None,
            "notes": self.notes,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
        if include_contact:
            data.update({
                "contactName": self.contact_name,
                "contactPhone": self.contact_phone,
                "address": self.address,
            })
        return data
