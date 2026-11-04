"""Customer <-> admin live chat.

Real time is done with short polling (the app asks for changes every few seconds). That works on
Render with the current gunicorn setup, with no WebSocket server or extra dependency.

Message status:
  sent       stored on the server
  delivered  the other side's app fetched it
  read       the other side opened the conversation
Deleting a message erases its text and leaves a marker both sides can see."""
import hashlib
import secrets
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import func

from app.extensions import db
from app.models import ChatLog, LiveAttachment, LiveConversation, LiveMessage, Order, User
from app.models.live_chat import STATUS_LABELS, STATUSES, TOPICS
from app.services import audit

MAX_BODY = 2000
RATE_LIMIT_MESSAGES = 20          # per customer, per minute
HISTORY_LIMIT = 100
MAX_CONTEXT_LOGS = 3
ONLINE_SECONDS = 45
PRESENCE_WRITE_SECONDS = 10
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


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


def clean_body(raw, allow_empty=False):
    body = str(raw or "").strip()
    if not body and not allow_empty:
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


def detect_image(data):
    """The real type of an image, judged from its bytes and not from its name or declared type.
    Returns a mime type, or raises. Only JPEG, PNG and WEBP with a complete structure are accepted."""
    if data[:3] == b"\xff\xd8\xff" and data.rstrip(b"\x00").endswith(b"\xff\xd9"):
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[-12:] == b"\x00\x00\x00\x00IEND\xaeB`\x82":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and int.from_bytes(data[4:8], "little") + 8 == len(data):
        return "image/webp"
    raise LiveChatError("That file is not a valid JPG, PNG or WEBP image")


def max_upload_bytes():
    return int(float(current_app.config.get("CHAT_UPLOAD_MAX_MB", 3)) * 1024 * 1024)


def read_upload(file_storage):
    """Reads an uploaded file within the size limit and checks that it really is a supported image."""
    limit = max_upload_bytes()
    data = file_storage.stream.read(limit + 1)
    if not data:
        raise LiveChatError("That file is empty")
    if len(data) > limit:
        raise LiveChatError(f"The image is too large. The limit is {limit / (1024 * 1024):g} MB.", 413)
    return data, detect_image(data)


def _attach(message, data, mime):
    db.session.add(LiveAttachment(
        message=message, conversation_id=message.conversation_id, stored_name=f"{secrets.token_hex(16)}.{IMAGE_TYPES[mime]}",
        mime=mime, size=len(data), sha256=hashlib.sha256(data).hexdigest(), data=data,
    ))


def _new_message(conversation, sender_type, name, body, image, admin_id=None):
    data = mime = None
    if image is not None:
        data, mime = image
    elif not body:
        raise LiveChatError("Type a message first")
    now = datetime.utcnow()
    message = LiveMessage(
        conversation_id=conversation.id, sender_type=sender_type, sender_admin_id=admin_id, sender_name=name,
        kind="image" if data else "text", body=body, created_at=now, updated_at=now,
    )
    db.session.add(message)
    db.session.flush()
    if data:
        _attach(message, data, mime)
    _touch(conversation, now)
    return message


def send_user_message(user, body, topic=None, order_id=None, image=None):
    check_eligible(user)
    body = clean_body(body, allow_empty=image is not None)
    _check_rate(user)
    conversation = ensure_conversation(user, topic, order_id)
    conversation.status, conversation.resolved_at = "open", None      # a new customer message needs attention
    message = _new_message(conversation, "user", user.name, body, image)
    db.session.commit()
    return conversation, message


def send_admin_message(admin, conversation, body, image=None):
    body = clean_body(body, allow_empty=image is not None)
    conversation.status, conversation.resolved_at = "pending", None   # now waiting for the customer
    message = _new_message(conversation, "admin", admin.name, body, image, admin_id=admin.id)
    db.session.commit()
    return message


def set_status(conversation, status):
    if status not in STATUSES:
        raise LiveChatError("Choose open, pending or resolved")
    conversation.status = status
    conversation.resolved_at = datetime.utcnow() if status == "resolved" else None
    db.session.commit()


def touch_presence(conversation):
    """Records that the customer's app just asked for messages. Online means "asked within the last minute"."""
    now = datetime.utcnow()
    last = conversation.user_last_seen_at
    if last is None or (now - last).total_seconds() >= PRESENCE_WRITE_SECONDS:
        conversation.user_last_seen_at = now
        db.session.commit()


def is_online(conversation):
    seen = conversation.user_last_seen_at
    return bool(seen and (datetime.utcnow() - seen).total_seconds() <= ONLINE_SECONDS)


def start_for_customer(admin, user, order=None):
    """An admin opens (or reuses) the conversation with a customer, optionally about one order."""
    conversation = conversation_for(user.id)
    created = conversation is None
    if created:
        conversation = LiveConversation(user_id=user.id, topic="order" if order else "other", status="pending")
        db.session.add(conversation)
    if order is not None:
        conversation.order_id = order.id
        conversation.topic = "order"
    db.session.commit()
    return conversation, created


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


def delete_message(message, actor_type, admin=None):
    """A sender may remove their own message; an admin may remove any. The text is erased
    for good and both sides see "This message was deleted"."""
    if message.deleted_at:
        return message
    if actor_type == "user" and message.sender_type != "user":
        raise LiveChatError("You can only delete your own messages", 403)
    now = datetime.utcnow()
    # The text is erased, but the fact of the deletion is kept: who, when, what kind of message, and a
    # fingerprint of the content, so nothing disappears without a trace.
    attachment = message.attachment
    audit.record(
        "chat_message_deleted", "live_message", message.id,
        {"conversationId": message.conversation_id, "sender": message.sender_type, "kind": message.kind,
         "sentAt": message.created_at.isoformat() if message.created_at else None,
         "textSha256": hashlib.sha256((message.body or "").encode("utf-8")).hexdigest() if message.body else None,
         "imageSha256": attachment.sha256 if attachment else None},
        {"deletedBy": actor_type}, None, admin=admin, actor_name=None if admin else f"Customer: {message.sender_name}",
    )
    if attachment is not None:
        db.session.delete(attachment)
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
    if message.deleted_at:
        text = "This message was deleted"
    elif message.kind == "image":
        text = "Photo" + (f": {message.body}" if message.body else "")
    else:
        text = message.body or ""
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
        "status": conversation.status or "open",
        "statusLabel": STATUS_LABELS.get(conversation.status or "open"),
        "createdAt": conversation.created_at.isoformat() if conversation.created_at else None,
    }
