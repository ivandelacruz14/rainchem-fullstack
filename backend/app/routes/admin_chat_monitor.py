from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.extensions import db
from app.models import ChatLog, KnowledgeEntry, LiveConversation, User
from app.utils.auth_decorators import require_permission

admin_chat_monitor_bp = Blueprint("admin_chat_monitor", __name__, url_prefix="/api/admin/chat-monitor")

CONTEXT_WINDOW = timedelta(hours=1)


def _log_dict(log, user=None):
    data = log.to_dict()
    data["user"] = {"id": user.id, "name": user.name} if user else None
    return data


@admin_chat_monitor_bp.get("")
@require_permission("chatbot")
def chat_monitor():
    """?view=all|unanswered|resolved. `resolved=true|false` is still accepted."""
    query = ChatLog.query
    view = request.args.get("view")
    legacy = request.args.get("resolved")
    if view == "unanswered":
        query = query.filter(ChatLog.resolved.is_(False), ChatLog.admin_resolved_at.is_(None))
    elif view == "resolved":
        query = query.filter(db.or_(ChatLog.resolved.is_(True), ChatLog.admin_resolved_at.isnot(None)))
    elif legacy == "true":
        query = query.filter_by(resolved=True)
    elif legacy == "false":
        query = query.filter_by(resolved=False)

    search = (request.args.get("search") or "").strip().lower()
    if search:
        query = query.filter(func.lower(ChatLog.question).like(f"%{search}%"))

    logs = query.order_by(ChatLog.created_at.desc(), ChatLog.id.desc()).limit(100).all()
    users = {u.id: u for u in User.query.filter(User.id.in_({l.user_id for l in logs if l.user_id})).all()} if logs else {}

    total = ChatLog.query.count()
    resolved = ChatLog.query.filter_by(resolved=True).count()
    average = db.session.query(func.avg(ChatLog.confidence)).scalar() or 0
    return jsonify({
        "logs": [_log_dict(l, users.get(l.user_id)) for l in logs],
        "stats": {
            "total": total,
            "resolved": resolved,
            "unresolved": total - resolved,
            "unanswered": ChatLog.query.filter(ChatLog.resolved.is_(False), ChatLog.admin_resolved_at.is_(None)).count(),
            "adminResolved": ChatLog.query.filter(ChatLog.admin_resolved_at.isnot(None)).count(),
            "handedOff": ChatLog.query.filter(ChatLog.handed_off_at.isnot(None)).count(),
            "averageConfidence": round(float(average)),
        },
    })


@admin_chat_monitor_bp.get("/<int:log_id>")
@require_permission("chatbot")
def log_detail(log_id):
    """One question with the conversation around it, so the admin can judge the AI's answer."""
    log = db.session.get(ChatLog, log_id)
    if log is None:
        return jsonify({"error": "Record not found"}), 404
    user = db.session.get(User, log.user_id) if log.user_id else None

    context = []
    if log.user_id and log.created_at:
        context = (
            ChatLog.query.filter(
                ChatLog.user_id == log.user_id, ChatLog.id != log.id,
                ChatLog.created_at >= log.created_at - CONTEXT_WINDOW,
                ChatLog.created_at <= log.created_at + CONTEXT_WINDOW,
            ).order_by(ChatLog.created_at, ChatLog.id).limit(8).all()
        )
    matched = db.session.get(KnowledgeEntry, log.matched_knowledge_id) if log.matched_knowledge_id else None
    has_live_chat = bool(log.user_id and LiveConversation.query.filter_by(user_id=log.user_id).first())
    return jsonify({
        "log": _log_dict(log, user),
        "context": [c.to_dict() for c in context],
        "matchedQuestion": matched.question if matched else None,
        "hasLiveChat": has_live_chat,
    })


@admin_chat_monitor_bp.post("/<int:log_id>/resolve")
@require_permission("chatbot")
def set_resolved(log_id):
    """Marks a question as dealt with (or reopens it). The AI's own resolved flag is left alone."""
    log = db.session.get(ChatLog, log_id)
    if log is None:
        return jsonify({"error": "Record not found"}), 404
    resolved = bool((request.get_json() or {}).get("resolved", True))
    log.admin_resolved_at = datetime.utcnow() if resolved else None
    db.session.commit()
    return jsonify({"log": log.to_dict()})


@admin_chat_monitor_bp.delete("/<int:log_id>")
@require_permission("chatbot")
def delete_log(log_id):
    """Deletes this one monitoring record. Orders, the customer's live chat and the knowledge
    base are separate tables and are not touched."""
    log = db.session.get(ChatLog, log_id)
    if log is None:
        return jsonify({"error": "Record not found"}), 404
    db.session.delete(log)
    db.session.commit()
    return jsonify({"message": "Record deleted"})
