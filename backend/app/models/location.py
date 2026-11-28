from datetime import datetime

from app.extensions import db


class PhLocation(db.Model):
    """Philippine places from the PSA PSGC (region, province, city or municipality, barangay).
    zip_code stays empty until an official postal dataset is loaded. It is never guessed."""

    __tablename__ = "ph_locations"

    code = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    level = db.Column(db.String(10), nullable=False, index=True)  # Reg | Prov | City | Mun | SubMun | Bgy
    parent_code = db.Column(db.String(10), nullable=True, index=True)
    zip_code = db.Column(db.String(4), nullable=True)


class UserAddress(db.Model):
    __tablename__ = "user_addresses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    label = db.Column(db.String(20), nullable=False, default="Home")  # Home | Work | Temporary | Other
    region_code = db.Column(db.String(10), nullable=False)
    region_name = db.Column(db.String(200), nullable=False)
    province_code = db.Column(db.String(10), nullable=True)
    province_name = db.Column(db.String(200), nullable=True)
    city_code = db.Column(db.String(10), nullable=False)
    city_name = db.Column(db.String(200), nullable=False)
    barangay_code = db.Column(db.String(10), nullable=False)
    barangay_name = db.Column(db.String(200), nullable=False)
    zip_code = db.Column(db.String(4), nullable=True)
    house_number = db.Column(db.String(40), nullable=True)
    street = db.Column(db.String(200), nullable=False)
    subdivision = db.Column(db.String(200), nullable=True)
    village = db.Column(db.String(200), nullable=True)
    unit = db.Column(db.String(60), nullable=True)
    landmark = db.Column(db.String(200), nullable=True)
    instructions = db.Column(db.String(500), nullable=True)
    latitude = db.Column(db.Float, nullable=True)   # the pin the customer dropped; the rider opens it in Maps
    longitude = db.Column(db.Float, nullable=True)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "label": self.label, "isDefault": bool(self.is_default),
            "region": {"code": self.region_code, "name": self.region_name},
            "province": {"code": self.province_code, "name": self.province_name} if self.province_code else None,
            "city": {"code": self.city_code, "name": self.city_name},
            "barangay": {"code": self.barangay_code, "name": self.barangay_name},
            "zipCode": self.zip_code, "houseNumber": self.house_number, "street": self.street,
            "subdivision": self.subdivision, "village": self.village, "unit": self.unit,
            "landmark": self.landmark, "instructions": self.instructions,
            "latitude": self.latitude, "longitude": self.longitude,
            "formatted": format_address(self),
        }


def format_address(a):
    line = " ".join(x for x in [a.house_number, a.street] if x)
    parts = [a.unit, line, a.subdivision, a.village, a.barangay_name, a.city_name, a.province_name, a.region_name, a.zip_code]
    return ", ".join(p for p in parts if p)
