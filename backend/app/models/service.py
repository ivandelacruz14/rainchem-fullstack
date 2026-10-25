from datetime import datetime
from app.extensions import db


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=True)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    owner_admin_id = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    areas = db.relationship(
        "ServiceArea", backref="service", cascade="all, delete-orphan",
        order_by="ServiceArea.area_name",
    )

    def area_named(self, name):
        wanted = (name or "").strip().lower()
        for area in self.areas:
            if area.area_name.lower() == wanted:
                return area
        return None

    def to_dict(self, admin_view=False):
        data = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "requirements": self.requirements,
            "areas": [a.to_dict() for a in self.areas],
        }
        if admin_view:
            data["isActive"] = bool(self.is_active)
            data["ownerId"] = self.owner_admin_id
        return data


class ServiceArea(db.Model):
    __tablename__ = "service_areas"
    __table_args__ = (db.UniqueConstraint("service_id", "area_name", name="uq_service_area_name"),)

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    area_name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    is_available = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.area_name,
            "price": float(self.price),
            "available": bool(self.is_available),
            "notes": self.notes,
        }


BOOKING_STATUSES = ["requested", "confirmed", "completed", "cancelled"]
BOOKING_LABELS = {
    "requested": "Requested",
    "confirmed": "Confirmed",
    "completed": "Completed",
    "cancelled": "Cancelled",
}


class ServiceBooking(db.Model):
    """A customer's request for a service in one area. The price is copied from
    the area at booking time, so later price changes do not alter old bookings."""

    __tablename__ = "service_bookings"

    id = db.Column(db.Integer, primary_key=True)
    booking_number = db.Column(db.String(40), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    service_area_id = db.Column(db.Integer, db.ForeignKey("service_areas.id"), nullable=True)
    service_name = db.Column(db.String(150), nullable=False)
    area_name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    customer_name = db.Column(db.String(150), nullable=False)
    customer_phone = db.Column(db.String(30), nullable=False)
    customer_email = db.Column(db.String(180), nullable=True)
    address = db.Column(db.String(255), nullable=False)
    preferred_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.String(500), nullable=True)

    status = db.Column(db.String(20), nullable=False, default="requested")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    service = db.relationship("Service")

    def to_dict(self, admin_view=False):
        data = {
            "id": self.id,
            "bookingNumber": self.booking_number,
            "serviceId": self.service_id,
            "serviceName": self.service_name,
            "area": self.area_name,
            "price": float(self.price),
            "address": self.address,
            "preferredDate": self.preferred_date.isoformat() if self.preferred_date else None,
            "notes": self.notes,
            "status": self.status,
            "statusLabel": BOOKING_LABELS.get(self.status, self.status),
            "canCancel": self.status == "requested",
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
        if admin_view:
            data["customer"] = {
                "name": self.customer_name,
                "phone": self.customer_phone,
                "email": self.customer_email,
            }
        return data
