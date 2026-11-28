from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Notification
from app.services import auto_confirm
from app.utils.auth_decorators import current_user_id, require_user

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


def _mine():
    return Notification.query.filter_by(user_id=current_user_id(), channel="app")


@notifications_bp.get("")
@require_user
def list_mine():
    auto_confirm.sweep_user(current_user_id())
    rows = _mine().order_by(Notification.id.desc()).limit(30).all()
    unread = _mine().filter_by(is_read=False).count()
    return jsonify({
        "unread": unread,
        "notifications": [{
            "id": n.id, "subject": n.subject, "body": n.body, "orderId": n.order_id, "link": n.link,
            "isRead": bool(n.is_read), "sentAt": n.sent_at.isoformat() if n.sent_at else None,
        } for n in rows],
    })


@notifications_bp.post("/read")
@require_user
def mark_read():
    ids = (request.get_json(silent=True) or {}).get("ids")
    query = _mine().filter_by(is_read=False)
    if isinstance(ids, list) and ids:
        query = query.filter(Notification.id.in_([int(i) for i in ids if str(i).isdigit()]))
    query.update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"ok": True})
