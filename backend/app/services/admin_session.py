"""Admin sessions: how long an admin stays signed in, and when it ends.

- Idle timeout: if no request arrives for ADMIN_IDLE_MINUTES (default 10), the session ends.
- Absolute limit: the session ends after ADMIN_SESSION_HOURS (default 8), even if it was active.
- The frontend sends a heartbeat while the person is active, so a person who is reading is not signed out.
- Closing the browser removes the token from sessionStorage, so the next visit needs a new login."""
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models import AdminSession

TOUCH_SECONDS = 30  # how often last_seen_at is written, to keep the database quiet
REASON_MESSAGES = {
    "idle": "You were signed out because there was no activity on the admin site for {m} minutes. Please sign in again.",
    "expired": "Your admin session has expired. Please sign in again.",
    "logout": "You have signed out. Sign in again if you need to.",
    "ended": "This session is no longer active. Please sign in again.",
}


def idle_minutes():
    return int(current_app.config.get("ADMIN_IDLE_MINUTES", 10))


def session_hours():
    return int(current_app.config.get("ADMIN_SESSION_HOURS", 8))


def open_session(admin):
    now = datetime.utcnow()
    session = AdminSession(
        admin_id=admin.id, created_at=now, last_seen_at=now, expires_at=now + timedelta(hours=session_hours()),
    )
    db.session.add(session)
    db.session.commit()
    return session


def end(session, reason):
    if session.ended_at is None:
        session.ended_at = datetime.utcnow()
        session.end_reason = reason
        db.session.commit()


def check_and_touch(session):
    """Returns None when the session is valid (and refreshes it), otherwise the reason it has ended."""
    if session.ended_at is not None:
        return session.end_reason or "ended"
    now = datetime.utcnow()
    if now >= session.expires_at:
        end(session, "expired")
        return "expired"
    idle = now - session.last_seen_at
    if idle > timedelta(minutes=idle_minutes()):
        end(session, "idle")
        return "idle"
    if idle.total_seconds() >= TOUCH_SECONDS:
        session.last_seen_at = now
        db.session.commit()
    return None


def message_for(reason):
    return REASON_MESSAGES.get(reason, REASON_MESSAGES["ended"]).format(m=idle_minutes())
