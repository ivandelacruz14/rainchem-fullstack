from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import defer

from app.extensions import db
from app.models import KnowledgeEntry, ChatLog, Product
from app.services.rag import answer_question
from app.utils.auth_decorators import require_user, current_user_id

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")

MAX_QUESTION_LENGTH = 500   # matches the chat_logs.question column
MAX_FEEDBACK_LENGTH = 500


@chat_bp.post("/ask")
@require_user
def ask():
    data = request.get_json() or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Please type a question"}), 400
    question = question[:MAX_QUESTION_LENGTH]

    previous_question = (data.get("previousQuestion") or "").strip()[:MAX_QUESTION_LENGTH] or None

    entries = KnowledgeEntry.query.filter_by(status="approved").all()
    # The chatbot never needs product photos (base64, can be megabytes each).
    products = Product.query.options(defer(Product.image_photo)).filter(Product.category != "Services").all()

    try:
        result = answer_question(
            question, entries, products=products,
            previous_question=previous_question, include_pending=False,
        )
    except Exception:
        current_app.logger.exception("RAG failed to answer a question")
        return jsonify({"error": "The assistant could not answer right now. Please try again."}), 500

    if result["matched_entry"]:
        result["matched_entry"].hits += 1

    log_id = None
    try:
        log = ChatLog(
            question=question,
            answer=result["answer"],
            matched_knowledge_id=result["matched_entry"].id if result["matched_entry"] else None,
            confidence=result["confidence"],
            resolved=result["resolved"],
            source=result["source"],
            user_id=current_user_id(),
        )
        db.session.add(log)
        db.session.commit()
        log_id = log.id
    except Exception:
        # Failing to save the log must never stop the customer from getting an answer.
        db.session.rollback()
        current_app.logger.exception("Could not save chat log")

    return jsonify({
        "logId": log_id,
        "answer": result["answer"],
        "confidence": result["confidence"],
        "resolved": result["resolved"],
        "source": result["source"],
        "canRate": result["can_rate"] and log_id is not None,
        "related": result["related"],
    })


@chat_bp.post("/feedback")
@require_user
def feedback():
    """Saves the customer's 1-5 star rating (and optional comment) for one
    chatbot answer. A customer can only rate their own conversations, and can
    change their rating afterwards."""
    data = request.get_json() or {}

    try:
        log_id = int(data.get("logId"))
        rating = int(data.get("rating"))
    except (TypeError, ValueError):
        return jsonify({"error": "A valid logId and rating are required"}), 400

    if rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be between 1 and 5"}), 400

    log = db.session.get(ChatLog, log_id)
    if not log or log.user_id != current_user_id():
        return jsonify({"error": "Conversation not found"}), 404

    log.rating = rating
    comment = data.get("comment")
    if comment is not None:
        log.feedback = (str(comment).strip()[:MAX_FEEDBACK_LENGTH]) or None
    log.rated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"message": "Thanks for your feedback!", "logId": log.id, "rating": log.rating})


@chat_bp.get("/suggestions")
@require_user
def suggestions():
    top = (
        KnowledgeEntry.query.filter_by(status="approved")
        .order_by(KnowledgeEntry.hits.desc())
        .limit(3)
        .all()
    )
    return jsonify({"suggestions": [{"id": e.id, "question": e.question} for e in top]})


@chat_bp.get("/faq")
def public_faq():
    query = KnowledgeEntry.query.filter_by(status="approved")
    if request.args.get("all") == "true":
        entries = query.order_by(KnowledgeEntry.category, KnowledgeEntry.hits.desc()).all()
    else:
        entries = query.order_by(KnowledgeEntry.hits.desc()).limit(5).all()
    return jsonify({"faqs": [e.to_dict() for e in entries]})
