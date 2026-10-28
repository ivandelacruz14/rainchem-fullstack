"""Customer <-> admin live chat.

Real time is done with short polling (the app asks for changes every few seconds). That works on
Render with the current gunicorn setup, with no WebSocket server or extra dependency.

Message status:
  sent       stored on the server
  delivered  the other side's app fetched it
  read       the other side opened the conversation
Deleting a message erases its text and leaves a marker both sides can see."""
from datetime import datetime, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models import ChatLog, LiveConversation, LiveMessage, Order, User
from app.models.live_chat import TOPICS

MAX_BODY = 2000
RATE_LIMIT_MESSAGES = 20          # per customer, per minute
HISTORY_LIMIT = 100
MAX_CONTEXT_LOGS = 3


class LiveChatError(Exception):
    def __init__(self, message, status=400, code=None):
        super().__init__(message)
        self.status = status
        self.code = code


def check_eligible(user):
    """Who may start or continue a chat: a signed-in customer whose email is verified."""
    if user is None:
        raise LiveChatError("Please log in to chat with our team", 401)
    if not user.verified:
        raise LiveChatError("Please verify your email address before chatting with our team", 403, "not_verified")


def conversation_for(user_id):
    return LiveConversation.query.filter_by(user_id=user_id).first()


def clean_body(raw):
    body = str(raw or "").strip()
    if not body:
        raise LiveChatError("Type a message first")
    if len(body) > MAX_BODY:
        raise LiveChatError(f"Messages can be at most {MAX_BODY} characters")
    return body


def _resolve_topic(topic, order_id, user):
    topic = topic if topic in TOPICS else None
    order = None
    if order_id not in (None, ""):
        try:
            order = db.session.get(Order, int(order_id))
        except (TypeError, ValueError):
            order = None
        if order is None or order.user_id != user.id:
            raise LiveChatError("That order was not found in your account")
        topic = topic or "order"
    return topic, order


def ensure_conversation(user, topic=None, order_id=None):
    """Reuses the customer's existing conversation instead of opening a new one."""
    topic, order = _resolve_topic(topic, order_id, user)
    conversation = conversation_for(user.id)
    if conversation is None:
        conversation = LiveConversation(user_id=user.id, topic=topic or "other")
        db.session.add(conversation)
        db.session.flush()
    elif topic:
        conversation.topic = topic
    if order is not None:
        conversation.order_id = order.id
    return conversation


def _touch(conversation, now):
    conversation.last_message_at = now


def _check_rate(user):
    since = datetime.utcnow() - timedelta(minutes=1)
    recent = (
        db.session.query(func.count(LiveMessage.id))
        .join(LiveConversation, LiveConversation.id == LiveMessage.conversation_id)
        .filter(LiveConversation.user_id == user.id, LiveMessage.sender_type == "user", LiveMessage.created_at >= since)
        .scalar()
    )
    if recent >= RATE_LIMIT_MESSAGES:
        raise LiveChatError("You are sending messages too fast. Please wait a moment.", 429)


def send_user_message(user, body, topic=None, order_id=None):
    check_eligible(user)
    body = clean_body(body)
    _check_rate(user)
    conversation = ensure_conversation(user, topic, order_id)
    now = datetime.utcnow()
    message = LiveMessage(
        conversation_id=conversation.id, sender_type="user", sender_name=user.name, body=body,
        created_at=now, updated_at=now,
    )
    db.session.add(message)
    _touch(conversation, now)
    db.session.commit()
    return conversation, message


def send_admin_message(admin, conversation, body):
    body = clean_body(body)
    now = datetime.utcnow()
    message = LiveMessage(
        conversation_id=conversation.id, sender_type="admin", sender_admin_id=admin.id,
        sender_name=admin.name, body=body, created_at=now, updated_at=now,
    )
    db.session.add(message)
    _touch(conversation, now)
    db.session.commit()
    return message


def mark_delivered(conversation_ids, sender_type):
    """The reader's app has fetched messages that `sender_type` sent."""
    if not conversation_ids:
        return 0
    now = datetime.utcnow()
    count = LiveMessage.query.filter(
        LiveMessage.conversation_id.in_(list(conversation_ids)), LiveMessage.sender_type == sender_type,
        LiveMessage.delivered_at.is_(None), LiveMessage.deleted_at.is_(None),
    ).update({"delivered_at": now, "updated_at": now}, synchronize_session=False)
    db.session.commit()
    return count


def mark_read(conversation, sender_type):
    """The reader opened the conversation, so everything `sender_type` sent is now read."""
    now = datetime.utcnow()
    rows = LiveMessage.query.filter(
        LiveMessage.conversation_id == conversation.id, LiveMessage.sender_type == sender_type,
        LiveMessage.read_at.is_(None), LiveMessage.deleted_at.is_(None),
    )
    count = rows.update({"read_at": now, "updated_at": now}, synchronize_session=False)
    LiveMessage.query.filter(
        LiveMessage.conversation_id == conversation.id, LiveMessage.sender_type == sender_type,
        LiveMessage.delivered_at.is_(None), LiveMessage.deleted_at.is_(None),
    ).update({"delivered_at": now}, synchronize_session=False)
    db.session.commit()
    return count


def delete_message(message, actor_type):
    """A sender may remove their own message; an admin may remove any. The text is erased
    for good and both sides see "This message was deleted"."""
    if message.deleted_at:
        return message
    if actor_type == "user" and message.sender_type != "user":
        raise LiveChatError("You can only delete your own messages", 403)
    now = datetime.utcnow()
    message.body = ""
    message.meta = None
    message.deleted_at = now
    message.deleted_by = actor_type
    message.updated_at = now
    db.session.commit()
    return message


def parse_since(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", ""))
    except ValueError:
        raise LiveChatError("Invalid time")


def messages_for(conversation, since=None):
    """The latest messages, or only those created or changed since `since` (inclusive).
    The caller keeps the newest `updatedAt` it saw and passes it back next time."""
    query = LiveMessage.query.filter_by(conversation_id=conversation.id)
    if since is not None:
        return query.filter(LiveMessage.updated_at >= since).order_by(LiveMessage.id).all()
    rows = query.order_by(LiveMessage.id.desc()).limit(HISTORY_LIMIT).all()
    return list(reversed(rows))


def unread_count(conversation_id, reader):
    """How many messages from the other side this reader has not opened yet."""
    other = "admin" if reader == "user" else "user"
    return (
        db.session.query(func.count(LiveMessage.id))
        .filter(
            LiveMessage.conversation_id == conversation_id, LiveMessage.sender_type == other,
            LiveMessage.read_at.is_(None), LiveMessage.deleted_at.is_(None),
        )
        .scalar()
    )


def preview(message):
    if message is None:
        return None
    text = "This message was deleted" if message.deleted_at else (message.body or "")
    return {
        "text": text if len(text) <= 120 else text[:117] + "...",
        "from": message.sender_type,
        "deleted": message.deleted_at is not None,
        "at": message.created_at.isoformat() if message.created_at else None,
    }


def last_message(conversation_id):
    return (
        LiveMessage.query.filter_by(conversation_id=conversation_id)
        .order_by(LiveMessage.id.desc()).first()
    )


def send_ai_context(user, log_ids, topic="ai"):
    """Hands the customer's recent AI questions to the admin so they need not repeat them.
    Only the customer's own chat logs are accepted; text comes from the stored logs."""
    check_eligible(user)
    ids = []
    for value in (log_ids or [])[:MAX_CONTEXT_LOGS]:
        try:
            ids.append(int(value))
        except (TypeError, ValueError):
            raise LiveChatError("Invalid chat reference")
    logs = ChatLog.query.filter(ChatLog.id.in_(ids), ChatLog.user_id == user.id).order_by(ChatLog.id).all() if ids else []
    if not logs:
        raise LiveChatError("There is no AI conversation to send")

    conversation = ensure_conversation(user, topic or "ai")
    wanted = [log.id for log in logs]
    for existing in (
        LiveMessage.query.filter_by(conversation_id=conversation.id, kind="context", sender_type="user")
        .filter(LiveMessage.deleted_at.is_(None)).order_by(LiveMessage.id.desc()).limit(5).all()
    ):
        if (existing.meta or {}).get("logIds") == wanted:
            return conversation, existing, True

    lines = ["I asked the AI assistant and need a person to help:"]
    for log in logs:
        lines.append(f"Q: {log.question}")
        lines.append(f"AI answer: {log.answer[:300]}" + (f" (confidence {log.confidence}%)" if log.confidence else ""))
    now = datetime.utcnow()
    message = LiveMessage(
        conversation_id=conversation.id, sender_type="user", sender_name=user.name, kind="context",
        body="\n".join(lines)[:MAX_BODY], meta={"logIds": wanted}, created_at=now, updated_at=now,
    )
    db.session.add(message)
    for log in logs:
        log.handed_off_at = now
    _touch(conversation, now)
    db.session.commit()
    return conversation, message, False


def conversation_dict(conversation):
    order = conversation.order
    return {
        "id": conversation.id,
        "topic": conversation.topic,
        "topicLabel": TOPICS.get(conversation.topic, "Something else"),
        "orderId": conversation.order_id,
        "orderNumber": order.order_number if order else None,
        "createdAt": conversation.created_at.isoformat() if conversation.created_at else None,
    }
