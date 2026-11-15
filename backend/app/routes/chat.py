from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import defer

from app.extensions import db
from app.models import KnowledgeEntry, ChatLog, Product
from app.services import handoff, recommender
from app.services.rag import answer_question
from app.utils.auth_decorators import require_user, current_user_id

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")

MAX_QUESTION_LENGTH = 500   # matches the chat_logs.question column
MAX_FEEDBACK_LENGTH = 500


def save_log(question, answer, confidence, resolved, source, matched_entry=None):
    try:
        log = ChatLog(
            question=question, answer=answer[:65000], matched_knowledge_id=matched_entry.id if matched_entry else None,
            confidence=confidence, resolved=resolved, source=source, user_id=current_user_id(),
        )
        db.session.add(log)
        db.session.commit()
        return log.id
    except Exception:
        # Failing to save the log must never stop the customer from getting an answer.
        db.session.rollback()
        current_app.logger.exception("Could not save chat log")
        return None


def recommendation_turn(question, context):
    """The guided product recommendation. Returns a response, or None to let the normal assistant answer."""
    if context and not recommender.looks_like_recommendation_request(question):
        parsed = recommender.parse_requirements(question)
        answering_a_question = bool(parsed) or len(question.split()) <= 6
        if not answering_a_question:
            return None    # a different question: leave the recommendation behind
    try:
        reply = recommender.recommend(question, context)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("The recommender failed")
        return None
    status = reply["status"]
    resolved = status != "insufficient"
    log_id = save_log(question, reply["answer"], reply.get("confidence", 0), resolved, "recommendation")
    human = {"needsHuman": False, "humanReason": None, "humanMessage": None}
    if status == "insufficient":
        human = {"needsHuman": True, "humanReason": "technical_confirmation", "humanMessage": handoff.TECHNICAL_MESSAGE}
    elif handoff.wants_human(question):
        human = {"needsHuman": True, "humanReason": "requested", "humanMessage": handoff.REQUESTED_MESSAGE}
    return jsonify({
        "logId": log_id, "answer": reply["answer"], "confidence": reply.get("confidence", 0), "resolved": resolved,
        "source": "recommendation", "canRate": status == "matches" and log_id is not None, "related": [],
        "recommendation": {k: reply.get(k) for k in ("status", "question", "recommendations", "missing", "notConfirmed", "requirements")},
        "recommendContext": reply["context"],
        **human,
    })


@chat_bp.post("/ask")
@require_user
def ask():
    data = request.get_json() or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Please type a question"}), 400
    question = question[:MAX_QUESTION_LENGTH]

    previous_question = (data.get("previousQuestion") or "").strip()[:MAX_QUESTION_LENGTH] or None

    context = data.get("recommendContext") if isinstance(data.get("recommendContext"), dict) else None
    if context or recommender.looks_like_recommendation_request(question):
        outcome = recommendation_turn(question, context)
        if outcome is not None:
            return outcome

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

    suggestion = handoff.suggest(question, result, current_user_id(), log_id)
    return jsonify({
        "logId": log_id,
        "answer": result["answer"],
        "confidence": result["confidence"],
        "resolved": result["resolved"],
        "source": result["source"],
        "canRate": result["can_rate"] and log_id is not None,
        "related": result["related"],
        **suggestion,
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

    response = {"message": "Thanks for your feedback!", "logId": log.id, "rating": log.rating}
    if rating <= 2:
        response.update({"needsHuman": True, "humanReason": "low_rating", "humanMessage": handoff.LOW_RATING_MESSAGE})
    return jsonify(response)


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
