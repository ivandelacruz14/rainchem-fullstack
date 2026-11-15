from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.extensions import db
from app.models import LiveAttachment, LiveConversation, LiveMessage, Order, User
from app.models.live_chat import STATUSES
from app.routes.live_chat import attachment_response, read_message_request
from app.services import audit, live_chat as chat
from app.utils.auth_decorators import current_admin, require_head_admin, require_permission

admin_live_chat_bp = Blueprint("admin_live_chat", __name__, url_prefix="/api/admin/live-chat")


def _fail(error):
    return jsonify({"error": str(error)}), error.status


def _user_dict(user):
    return {"id": user.id, "name": user.name, "email": user.email, "hasPhoto": bool(user.avatar_photo)} if user else None


def _conversation_row(conversation):
    unread = chat.unread_count(conversation.id, "admin")
    return {
        **chat.conversation_dict(conversation),
        "user": _user_dict(conversation.user),
        "unread": unread,
        "needsAttention": unread > 0 and conversation.status != "resolved",
        "online": chat.is_online(conversation),
        "lastMessage": chat.preview(chat.last_message(conversation.id)),
        "lastMessageAt": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
    }


def _get(conversation_id):
    return db.session.get(LiveConversation, conversation_id)


def _unread_subquery():
    return (
        db.session.query(LiveMessage.conversation_id.label("cid"), func.count(LiveMessage.id).label("n"))
        .filter(LiveMessage.sender_type == "user", LiveMessage.read_at.is_(None), LiveMessage.deleted_at.is_(None))
        .group_by(LiveMessage.conversation_id).subquery()
    )


@admin_live_chat_bp.get("/conversations")
@require_permission("livechat")
def list_conversations():
    """?filter=all|unread|open|pending|resolved  ?sort=latest|oldest|unread  ?search=name or email"""
    search = (request.args.get("search") or "").strip().lower()
    view = request.args.get("filter", "all")
    unread = _unread_subquery()
    query = (
        LiveConversation.query.join(User, User.id == LiveConversation.user_id)
        .outerjoin(unread, unread.c.cid == LiveConversation.id)
    )
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(func.lower(User.name).like(like), func.lower(User.email).like(like)))
    if view == "unread":
        query = query.filter(unread.c.n > 0)
    elif view in STATUSES:
        query = query.filter(LiveConversation.status == view)
    sort = request.args.get("sort", "latest")
    if sort == "oldest":
        query = query.order_by(LiveConversation.last_message_at.asc())
    elif sort == "unread":
        query = query.order_by(func.coalesce(unread.c.n, 0).desc(), LiveConversation.last_message_at.desc())
    else:
        query = query.order_by(LiveConversation.last_message_at.desc())
    rows = query.limit(200).all()
    chat.mark_delivered([c.id for c in rows], "user")  # the admin's inbox now has the customers' messages
    counts = {"all": LiveConversation.query.count()}
    for status in STATUSES:
        counts[status] = LiveConversation.query.filter_by(status=status).count()
    counts["unread"] = db.session.query(func.count(func.distinct(LiveMessage.conversation_id))).filter(
        LiveMessage.sender_type == "user", LiveMessage.read_at.is_(None), LiveMessage.deleted_at.is_(None)).scalar()
    return jsonify({"conversations": [_conversation_row(c) for c in rows], "counts": counts})


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


@admin_live_chat_bp.post("/conversations/start")
@require_permission("livechat")
def start_conversation():
    """Opens the conversation with a customer, or reuses the one that exists. Body: {orderId} or {userId}."""
    data = request.get_json() or {}
    order = db.session.get(Order, data.get("orderId")) if data.get("orderId") else None
    if data.get("orderId") and order is None:
        return jsonify({"error": "Order not found"}), 404
    user = db.session.get(User, order.user_id) if order and order.user_id else (
        db.session.get(User, data.get("userId")) if data.get("userId") else None)
    if user is None:
        return jsonify({"error": "That customer has no account to message"}), 404
    conversation, created = chat.start_for_customer(current_admin(), user, order)
    return jsonify({"conversation": _conversation_row(conversation), "created": created}), 201 if created else 200


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
        "maxUploadMb": chat.max_upload_bytes() / (1024 * 1024),
    })


@admin_live_chat_bp.get("/conversations/<int:conversation_id>/customer")
@require_permission("livechat")
def customer_panel(conversation_id):
    """The customer and their orders, limited to what this admin is allowed to see."""
    conversation, admin = _get(conversation_id), current_admin()
    if conversation is None:
        return jsonify({"error": "Conversation not found"}), 404
    user = conversation.user
    customer = {"id": user.id, "name": user.name, "email": user.email, "hasPhoto": bool(user.avatar_photo),
                "joinedAt": user.created_at.isoformat() if getattr(user, "created_at", None) else None}
    if admin.has_permission("customers"):
        customer.update({"phone": user.phone, "verified": bool(user.verified)})
    orders = []
    if admin.has_permission("orders"):
        for order in Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).limit(10).all():
            data = order.to_dict()
            orders.append({
                "id": order.id, "orderNumber": order.order_number, "status": order.status, "statusLabel": data["statusLabel"],
                "journeyHeadline": data["journey"]["headline"], "paymentMethod": order.payment_method,
                "paymentStatus": order.payment_status, "paymentStatusLabel": data["paymentStatusLabel"],
                "confirmed": order.status not in ("pending_confirmation", "cancelled"),
                "total": float(order.total), "createdAt": order.created_at.isoformat() if order.created_at else None,
                "items": [{"name": i.product_name, "quantity": i.quantity} for i in order.items],
                "linked": order.id == conversation.order_id,
            })
    return jsonify({"customer": customer, "orders": orders, "canSeeOrders": admin.has_permission("orders"),
                    "canOpenOrders": admin.has_permission("manage_orders")})


@admin_live_chat_bp.get("/users/<int:user_id>/photo")
@require_permission("livechat")
def customer_photo(user_id):
    """The customer's profile picture, decoded from the stored data URL, for the inbox."""
    import base64
    user = db.session.get(User, user_id)
    photo = user.avatar_photo if user else None
    if not photo or not photo.startswith("data:image/") or ";base64," not in photo:
        return jsonify({"error": "No photo"}), 404
    header, encoded = photo.split(";base64,", 1)
    mime = header[5:]
    if mime not in chat.IMAGE_TYPES:
        return jsonify({"error": "No photo"}), 404
    from flask import Response
    return Response(base64.b64decode(encoded), mimetype=mime, headers={
        "Cache-Control": "private, max-age=600", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'; sandbox"})


@admin_live_chat_bp.post("/conversations/<int:conversation_id>/read")
@require_permission("livechat")
def read_conversation(conversation_id):
    conversation = _get(conversation_id)
    if conversation is None:
        return jsonify({"error": "Conversation not found"}), 404
    return jsonify({"updated": chat.mark_read(conversation, "user")})


@admin_live_chat_bp.post("/conversations/<int:conversation_id>/status")
@require_permission("livechat")
def change_status(conversation_id):
    conversation = _get(conversation_id)
    if conversation is None:
        return jsonify({"error": "Conversation not found"}), 404
    try:
        chat.set_status(conversation, (request.get_json() or {}).get("status"))
    except chat.LiveChatError as error:
        return _fail(error)
    return jsonify({"conversation": _conversation_row(conversation)})


@admin_live_chat_bp.post("/conversations/<int:conversation_id>/messages")
@require_permission("livechat")
def reply(conversation_id):
    conversation = _get(conversation_id)
    if conversation is None:
        return jsonify({"error": "Conversation not found"}), 404
    try:
        data, image = read_message_request()
        message = chat.send_admin_message(current_admin(), conversation, data.get("body"), image)
    except chat.LiveChatError as error:
        return _fail(error)
    return jsonify({"message": message.to_dict("admin"), "conversation": _conversation_row(conversation)}), 201


@admin_live_chat_bp.get("/attachments/<int:attachment_id>")
@require_permission("livechat")
def get_attachment(attachment_id):
    attachment = db.session.get(LiveAttachment, attachment_id)
    if attachment is None:
        return jsonify({"error": "Image not found"}), 404
    return attachment_response(attachment)


@admin_live_chat_bp.delete("/messages/<int:message_id>")
@require_permission("livechat")
def delete_message(message_id):
    message = db.session.get(LiveMessage, message_id)
    if message is None:
        return jsonify({"error": "Message not found"}), 404
    chat.delete_message(message, "admin", admin=current_admin())
    return jsonify({"message": message.to_dict("admin")})


@admin_live_chat_bp.delete("/conversations/<int:conversation_id>")
@require_head_admin
def delete_conversation(conversation_id):
    """Removes the whole conversation and its messages for good. Head Admin only, and always audited."""
    conversation = _get(conversation_id)
    if conversation is None:
        return jsonify({"error": "Conversation not found"}), 404
    count = LiveMessage.query.filter_by(conversation_id=conversation.id).count()
    audit.record("chat_conversation_deleted", "live_conversation", conversation.id,
                 {"customerId": conversation.user_id, "customer": conversation.user.name, "messages": count},
                 None, None, admin=current_admin())
    db.session.delete(conversation)
    db.session.commit()
    return jsonify({"message": "Conversation deleted"})
