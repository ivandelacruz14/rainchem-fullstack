from datetime import datetime
from app.extensions import db


class AdminEmailChange(db.Model):
    """A pending change of an admin's own email. It only takes effect once the
    one-time code sent to the NEW address is entered."""

    __tablename__ = "admin_email_changes"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    new_email = db.Column(db.String(180), nullable=False)
    salt = db.Column(db.String(32), nullable=False)
    code_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.SmallInteger, nullable=False, default=0)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
