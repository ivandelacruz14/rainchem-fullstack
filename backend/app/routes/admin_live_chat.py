from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.extensions import db
from app.models import LiveConversation, LiveMessage, User
from app.services import live_chat as chat
from app.utils.auth_decorators import current_admin, require_head_admin, require_permission

admin_live_chat_bp = Blueprint("admin_live_chat", __name__, url_prefix="/api/admin/live-chat")


def _fail(error):
    return jsonify({"error": str(error)}), error.status


def _user_dict(user):
    return {"id": user.id, "name": user.name, "email": user.email} if user else None


def _conversation_row(conversation):
    return {
        **chat.conversation_dict(conversation),
        "user": _user_dict(conversation.user),
        "unread": chat.unread_count(conversation.id, "admin"),
        "lastMessage": chat.preview(chat.last_message(conversation.id)),
        "lastMessageAt": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
    }


def _get(conversation_id):
    return db.session.get(LiveConversation, conversation_id)


@admin_live_chat_bp.get("/conversations")
@require_permission("livechat")
def list_conversations():
    search = (request.args.get("search") or "").strip().lower()
    query = LiveConversation.query.join(User, User.id == LiveConversation.user_id)
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(func.lower(User.name).like(like), func.lower(User.email).like(like)))
    rows = query.order_by(LiveConversation.last_message_at.desc()).limit(200).all()
    chat.mark_delivered([c.id for c in rows], "user")  # the admin's inbox now has the customers' messages
    return jsonify({"conversations": [_conversation_row(c) for c in rows]})


@admin_live_chat_bp.get("/unread-count")
@require_permission("livechat")
def unread_total():
    total = (
        db.session.query(func.count(LiveMessage.id))
        .filter(LiveMessage.sender_type == "user", LiveMessage.read_at.is_(None), LiveMessage.deleted_at.is_(None))
        .scalar()
    )
    waiting = (
        db.session.query(func.count(func.distinct(LiveMessage.conversation_id)))
        .filter(LiveMessage.sender_type == "user", LiveMessage.read_at.is_(None), LiveMessage.deleted_at.is_(None))
        .scalar()
    )
    return jsonify({"unread": total, "conversations": waiting})


@admin_live_chat_bp.get("/conversations/<int:conversation_id>")
@require_permission("livechat")
def open_conversation(conversation_id):
    conversation = _get(conversation_id)
    if conversation is None:
        return jsonify({"error": "Conversation not found"}), 404
    try:
        since = chat.parse_since(request.args.get("since"))
    except chat.LiveChatError as error:
        return _fail(error)
    chat.mark_delivered([conversation.id], "user")
    return jsonify({
        "conversation": _conversation_row(conversation),
        "messages": [m.to_dict("admin") for m in chat.messages_for(conversation, since)],
        "serverTime": datetime.utcnow().isoformat(),
    })


@admin_live_chat_bp.post("/conversations/<int:conversation_id>/read")
@require_permission("livechat")
def read_conversation(conversation_id):
    conversation = _get(conversation_id)
    if conversation is None:
        return jsonify({"error": "Conversation not found"}), 404
    return jsonify({"updated": chat.mark_read(conversation, "user")})


@admin_live_chat_bp.post("/conversations/<int:conversation_id>/messages")
@require_permission("livechat")
def reply(conversation_id):
    conversation = _get(conversation_id)
    if conversation is None:
        return jsonify({"error": "Conversation not found"}), 404
    try:
        message = chat.send_admin_message(current_admin(), conversation, (request.get_json() or {}).get("body"))
    except chat.LiveChatError as error:
        return _fail(error)
    return jsonify({"message": message.to_dict("admin")}), 201


@admin_live_chat_bp.delete("/messages/<int:message_id>")
@require_permission("livechat")
def delete_message(message_id):
    message = db.session.get(LiveMessage, message_id)
    if message is None:
        return jsonify({"error": "Message not found"}), 404
    chat.delete_message(message, "admin")
    return jsonify({"message": message.to_dict("admin")})


@admin_live_chat_bp.delete("/conversations/<int:conversation_id>")
@require_head_admin
def delete_conversation(conversation_id):
    """Removes the whole conversation and its messages for good. Head Admin only."""
    conversation = _get(conversation_id)
    if conversation is None:
        return jsonify({"error": "Conversation not found"}), 404
    db.session.delete(conversation)
    db.session.commit()
    return jsonify({"message": "Conversation deleted"})
