from datetime import datetime
from sqlalchemy.orm import deferred

from app.extensions import db


class ChangeRequest(db.Model):
    """A product change waiting for the Head Admin. It is also the audit trail: who asked,
    who decided, when, and what the change was."""

    __tablename__ = "change_requests"

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(30), nullable=False)  # product_create | product_update | product_delete
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending | approved | rejected | cancelled
    product_id = db.Column(db.Integer, nullable=True, index=True)
    target_name = db.Column(db.String(200), nullable=False)
    payload = db.Column(db.JSON, nullable=True)
    image_photo = deferred(db.Column(db.Text(length=4294967295), nullable=True))

    requested_by = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    requester_name = db.Column(db.String(120), nullable=False, default="")
    requester_role = db.Column(db.String(60), nullable=False, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    decided_by = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    decider_name = db.Column(db.String(120), nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    decision_note = db.Column(db.String(255), nullable=True)


class ApprovalOtp(db.Model):
    """One emailed approval code. Only a salted hash of the code is stored."""

    __tablename__ = "approval_otps"

    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="CASCADE"), nullable=False)
    salt = db.Column(db.String(32), nullable=False)
    code_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.SmallInteger, nullable=False, default=0)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
