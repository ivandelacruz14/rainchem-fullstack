from datetime import datetime

from app.extensions import db


class AdminSession(db.Model):
    """One signed-in admin browser session. The token carries its id, so every request can be checked
    against this row: it must not be ended, not expired, and not idle for too long."""

    __tablename__ = "admin_sessions"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    end_reason = db.Column(db.String(20), nullable=True)  # logout | idle | expired | ended


class AdminLoginChallenge(db.Model):
    """A pending admin sign-in that waits for the six-digit code emailed to the admin.
    Only hashes are stored: of the challenge token and of the code."""

    __tablename__ = "admin_login_challenges"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    challenge_hash = db.Column(db.String(64), nullable=False, index=True)
    salt = db.Column(db.String(32), nullable=False)
    code_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.SmallInteger, nullable=False, default=0)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
