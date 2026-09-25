from datetime import datetime
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(120), nullable=True, unique=True)
    phone = db.Column(db.String(30), nullable=True)
    verified = db.Column(db.Boolean, nullable=False, default=False)
    phone = db.Column(db.String(30), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    avatar_photo = db.Column(db.Text(length=4294967295), nullable=True)
    verified = db.Column(db.Boolean, nullable=False, default=False)

    address_line1 = db.Column(db.String(200), nullable=True)
    address_city = db.Column(db.String(100), nullable=True)
    address_province = db.Column(db.String(100), nullable=True)
    address_region = db.Column(db.String(100), nullable=True)
    address_zip = db.Column(db.String(20), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "avatarPhoto": self.avatar_photo,
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "age": self.age,
            "gender": self.gender,
            "verified": self.verified,
            "hasGoogleLogin": self.google_id is not None,
            "address": {
                "line1": self.address_line1,
                "city": self.address_city,
                "province": self.address_province,
                "region": self.address_region,
                "zip": self.address_zip,
            },
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class EmailVerification(db.Model):
    __tablename__ = "email_verifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    pending_email = db.Column(db.String(180), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)


class PasswordReset(db.Model):
    __tablename__ = "password_resets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(120), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
