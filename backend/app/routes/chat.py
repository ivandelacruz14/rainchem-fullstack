from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import KnowledgeEntry, ChatLog
from app.services.rag import answer_question
from app.utils.auth_decorators import require_user, current_user_id

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.post("/ask")
@require_user
def ask():
    data = request.get_json() or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Please type a question"}), 400

    entries = KnowledgeEntry.query.filter_by(status="approved").all()
    result = answer_question(question, entries, include_pending=False)

    if result["matched_entry"]:
        result["matched_entry"].hits += 1

    log = ChatLog(
        question=question,
        answer=result["answer"],
        matched_knowledge_id=result["matched_entry"].id if result["matched_entry"] else None,
        confidence=result["confidence"],
        resolved=result["resolved"],
        user_id=current_user_id(),
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "answer": result["answer"],
        "confidence": result["confidence"],
        "resolved": result["resolved"],
    })


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
    """Used by the homepage FAQ teaser section, no login required since
    it's just displaying already-approved public knowledge."""
    top = (
        KnowledgeEntry.query.filter_by(status="approved")
        .order_by(KnowledgeEntry.hits.desc())
        .limit(5)
        .all()
    )
    return jsonify({"faqs": [e.to_dict() for e in top]})
