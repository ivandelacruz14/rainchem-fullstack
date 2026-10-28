from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import LiveMessage, Order, User
from app.models.live_chat import TOPICS
from app.services import live_chat as chat
from app.utils.auth_decorators import current_user_id, require_user

live_chat_bp = Blueprint("live_chat", __name__, url_prefix="/api/live-chat")


def _fail(error):
    body = {"error": str(error)}
    if error.code:
        body["code"] = error.code
    return jsonify(body), error.status


def _user():
    return db.session.get(User, current_user_id())


def _snapshot(conversation, messages):
    return {
        "conversation": chat.conversation_dict(conversation) if conversation else None,
        "messages": [m.to_dict("user") for m in messages],
        "unread": chat.unread_count(conversation.id, "user") if conversation else 0,
        "serverTime": datetime.utcnow().isoformat(),
        "topics": [{"key": k, "label": v} for k, v in TOPICS.items()],
    }


@live_chat_bp.get("")
@require_user
def get_chat():
    """The signed-in customer's own conversation. There is no conversation id in the URL, so
    nobody can ask for someone else's."""
    user = _user()
    try:
        since = chat.parse_since(request.args.get("since"))
    except chat.LiveChatError as error:
        return _fail(error)
    conversation = chat.conversation_for(user.id)
    if conversation is None:
        return jsonify(_snapshot(None, []))
    chat.mark_delivered([conversation.id], "admin")   # their app now has the admin's messages
    return jsonify(_snapshot(conversation, chat.messages_for(conversation, since)))


@live_chat_bp.get("/unread")
@require_user
def unread():
    """For the badge on the chat button. The admin's latest message counts as delivered."""
    conversation = chat.conversation_for(current_user_id())
    if conversation is None:
        return jsonify({"unread": 0, "latest": None})
    chat.mark_delivered([conversation.id], "admin")
    return jsonify({
        "unread": chat.unread_count(conversation.id, "user"),
        "latest": chat.preview(chat.last_message(conversation.id)),
    })


@live_chat_bp.post("/messages")
@require_user
def send_message():
    data = request.get_json() or {}
    try:
        conversation, message = chat.send_user_message(_user(), data.get("body"), data.get("topic"), data.get("orderId"))
    except chat.LiveChatError as error:
        return _fail(error)
    return jsonify({"message": message.to_dict("user"), "conversation": chat.conversation_dict(conversation)}), 201


@live_chat_bp.post("/from-ai")
@require_user
def send_from_ai():
    """Passes the customer's recent AI questions to the admin as one message."""
    data = request.get_json() or {}
    try:
        conversation, message, already = chat.send_ai_context(_user(), data.get("logIds"), data.get("topic") or "ai")
    except chat.LiveChatError as error:
        return _fail(error)
    return jsonify({
        "message": message.to_dict("user"), "conversation": chat.conversation_dict(conversation), "alreadySent": already,
    }), 200 if already else 201


@live_chat_bp.post("/read")
@require_user
def mark_read():
    conversation = chat.conversation_for(current_user_id())
    if conversation is None:
        return jsonify({"updated": 0})
    return jsonify({"updated": chat.mark_read(conversation, "admin")})


@live_chat_bp.delete("/messages/<int:message_id>")
@require_user
def delete_message(message_id):
    message = db.session.get(LiveMessage, message_id)
    conversation = chat.conversation_for(current_user_id())
    if message is None or conversation is None or message.conversation_id != conversation.id:
        return jsonify({"error": "Message not found"}), 404
    try:
        chat.delete_message(message, "user")
    except chat.LiveChatError as error:
        return _fail(error)
    return jsonify({"message": message.to_dict("user")})


@live_chat_bp.get("/orders")
@require_user
def my_orders_for_chat():
    """The customer's own recent orders, so they can say which order they need help with."""
    rows = Order.query.filter_by(user_id=current_user_id()).order_by(Order.created_at.desc()).limit(20).all()
    return jsonify({"orders": [{"id": o.id, "orderNumber": o.order_number, "statusLabel": o.to_dict()["statusLabel"]} for o in rows]})
