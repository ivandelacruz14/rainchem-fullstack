from flask import g, has_request_context

from app.extensions import db
from app.models import AuditLog


def record(action, entity_type, entity_id, old=None, new=None, reason=None, admin=None, actor_name=None):
    """Adds an audit entry to the current transaction. The caller commits."""
    if admin is None and has_request_context():
        admin = getattr(g, "admin", None)
    entry = AuditLog(
        admin_id=admin.id if admin else None,
        admin_name=actor_name or (admin.name if admin else "System"),
        action=action, entity_type=entity_type, entity_id=str(entity_id),
        old_value=old, new_value=new, reason=(reason or None) and str(reason)[:500],
    )
    db.session.add(entry)
    return entry
