from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models import KnowledgeEntry
from app.services.rag import retrieve, FALLBACK_ANSWER
from app.utils.auth_decorators import require_admin

knowledge_bp = Blueprint("knowledge", __name__, url_prefix="/api/admin/knowledge")


@knowledge_bp.get("")
@require_admin
def list_knowledge():
    status = request.args.get("status")
    query = KnowledgeEntry.query
    if status and status != "All":
        query = query.filter_by(status=status.lower())
    entries = query.order_by(KnowledgeEntry.created_at.desc()).all()
    return jsonify({"entries": [e.to_dict() for e in entries]})


@knowledge_bp.post("")
@require_admin
def create_knowledge():
    data = request.get_json() or {}
    entry = KnowledgeEntry(
        question=data.get("question", ""),
        answer=data.get("answer", ""),
        category=data.get("category", "General"),
        status=data.get("status", "pending"),
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({"entry": entry.to_dict()}), 201


@knowledge_bp.put("/<int:entry_id>")
@require_admin
def update_knowledge(entry_id):
    entry = KnowledgeEntry.query.get_or_404(entry_id)
    data = request.get_json() or {}
    for field in ["question", "answer", "category", "status"]:
        if field in data:
            setattr(entry, field, data[field])
    db.session.commit()
    return jsonify({"entry": entry.to_dict()})


@knowledge_bp.post("/<int:entry_id>/approve")
@require_admin
def approve_knowledge(entry_id):
    entry = KnowledgeEntry.query.get_or_404(entry_id)
    entry.status = "approved"
    db.session.commit()
    return jsonify({"entry": entry.to_dict()})


@knowledge_bp.delete("/<int:entry_id>")
@require_admin
def delete_knowledge(entry_id):
    entry = KnowledgeEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"message": "Knowledge entry deleted"})


@knowledge_bp.post("/test")
@require_admin
def test_ai():
    data = request.get_json() or {}
    question = data.get("question", "")
    include_pending = bool(data.get("includePending"))

    entries = KnowledgeEntry.query.all()
    matched, confidence, candidates = retrieve(question, entries, include_pending)

    return jsonify({
        "answer": matched.answer if matched else FALLBACK_ANSWER,
        "matchedEntry": matched.to_dict() if matched else None,
        "confidence": confidence,
        "candidates": [
            {"question": e.question, "score": round(score * 100)} for e, score in candidates
        ],
    })
