from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.extensions import db
from app.models import Product, ProductDocument, RecommendationLog
from app.models.product_document import DOC_TYPES, FACT_KEYS
from app.services import audit, recommender
from app.utils.auth_decorators import current_admin, require_head_admin, require_permission

admin_product_docs_bp = Blueprint("admin_product_docs", __name__, url_prefix="/api/admin/product-docs")

MAX_CONTENT = 20000


def _bad(message, status=400):
    return jsonify({"error": message}), status


def _clean_facts(raw):
    """Specifications as short lists of text, only the known keys."""
    facts = {}
    for key in FACT_KEYS:
        values = (raw or {}).get(key) or []
        if isinstance(values, str):
            values = [v for v in values.replace(";", ",").split(",")]
        if not isinstance(values, list):
            raise ValueError(f"{key} must be a list")
        cleaned = [str(v).strip()[:80] for v in values if str(v).strip()]
        if cleaned:
            facts[key] = list(dict.fromkeys(cleaned))[:30]
    return facts


def _read(data, creating):
    values = {}
    if creating or "title" in data:
        title = str(data.get("title") or "").strip()
        if not title:
            raise ValueError("A title is required")
        values["title"] = title[:200]
    if creating or "content" in data:
        content = str(data.get("content") or "").strip()
        if not content:
            raise ValueError("The document text is required")
        if len(content) > MAX_CONTENT:
            raise ValueError(f"The document text can be at most {MAX_CONTENT} characters")
        values["content"] = content
    if creating or "docType" in data:
        if data.get("docType", "technical_data_sheet") not in DOC_TYPES:
            raise ValueError("Choose a document type")
        values["doc_type"] = data.get("docType", "technical_data_sheet")
    if creating or "productId" in data:
        product = db.session.get(Product, data.get("productId")) if data.get("productId") else None
        if product is None or product.category == "Services":
            raise ValueError("Choose the product this document is about")
        values["product_id"] = product.id
    for key, column, limit in (("version", "version", 40), ("source", "source", 255)):
        if key in data:
            values[column] = (str(data.get(key) or "").strip()[:limit]) or None
    if "facts" in data:
        values["facts"] = _clean_facts(data.get("facts"))
    return values


@admin_product_docs_bp.get("")
@require_permission("chatbot")
def list_docs():
    query = ProductDocument.query
    if request.args.get("product_id"):
        query = query.filter(ProductDocument.product_id == int(request.args["product_id"]))
    state = request.args.get("state")
    if state == "usable":
        query = query.filter_by(verified=True, authorized=True)
    elif state == "unverified":
        query = query.filter(db.or_(ProductDocument.verified.is_(False), ProductDocument.authorized.is_(False)))
    rows = query.order_by(ProductDocument.updated_at.desc()).all()
    products = Product.query.filter(Product.category != "Services").order_by(Product.name).all()
    return jsonify({
        "documents": [d.to_dict(with_content=False) for d in rows],
        "products": [{"id": p.id, "name": p.name} for p in products],
        "types": [{"key": k, "label": v} for k, v in DOC_TYPES.items()],
    })


@admin_product_docs_bp.get("/<int:doc_id>")
@require_permission("chatbot")
def get_doc(doc_id):
    doc = db.session.get(ProductDocument, doc_id)
    return (jsonify({"document": doc.to_dict()}) if doc else _bad("Document not found", 404))


@admin_product_docs_bp.post("")
@require_permission("chatbot")
def create_doc():
    admin = current_admin()
    try:
        values = _read(request.get_json() or {}, creating=True)
    except ValueError as error:
        return _bad(str(error))
    doc = ProductDocument(created_by=admin.name, verified=False, authorized=False, **values)
    db.session.add(doc)
    audit.record("product_doc_created", "product_document", "new", None, {"title": doc.title, "productId": doc.product_id}, None, admin)
    db.session.commit()
    return jsonify({"document": doc.to_dict()}), 201


@admin_product_docs_bp.post("/from-listing")
@require_permission("chatbot")
def from_listing():
    """Copies a product's listing into a draft document, which still has to be verified before it is used."""
    admin = current_admin()
    product = db.session.get(Product, (request.get_json() or {}).get("productId"))
    if product is None or product.category == "Services":
        return _bad("Choose a product", 404)
    lines = [product.name, f"Category: {product.category}", product.short_desc or "", product.description or ""]
    for title, items in (("Specifications", product.specs), ("Benefits", product.benefits), ("How to use", product.usage_steps)):
        if items:
            lines += ["", title + ":"] + [f"- {i}" for i in items]
    doc = ProductDocument(
        product_id=product.id, title=f"{product.name} - product listing", doc_type="product_listing",
        source="Copied from the product listing", content="\n".join(l for l in lines if l is not None).strip(),
        facts={}, created_by=admin.name,
    )
    db.session.add(doc)
    db.session.commit()
    return jsonify({"document": doc.to_dict()}), 201


@admin_product_docs_bp.put("/<int:doc_id>")
@require_permission("chatbot")
def update_doc(doc_id):
    admin, doc = current_admin(), db.session.get(ProductDocument, doc_id)
    if doc is None:
        return _bad("Document not found", 404)
    try:
        values = _read(request.get_json() or {}, creating=False)
    except ValueError as error:
        return _bad(str(error))
    was_usable = doc.usable
    for column, value in values.items():
        setattr(doc, column, value)
    if values:  # a changed document has to be checked again before the assistant may use it
        doc.verified = doc.authorized = False
        doc.verified_by = doc.verified_at = None
        if was_usable:
            audit.record("product_doc_withdrawn", "product_document", doc.id, {"verified": True}, {"verified": False}, "Edited after verification", admin)
    db.session.commit()
    return jsonify({"document": doc.to_dict()})


@admin_product_docs_bp.post("/<int:doc_id>/verify")
@require_head_admin
def verify_doc(doc_id):
    """Only a Head Admin can make a document usable by the assistant."""
    admin, doc = current_admin(), db.session.get(ProductDocument, doc_id)
    if doc is None:
        return _bad("Document not found", 404)
    data = request.get_json(silent=True) or {}
    doc.verified, doc.authorized = True, data.get("authorized", True) is not False
    doc.verified_by, doc.verified_at = admin.name, datetime.utcnow()
    audit.record("product_doc_verified", "product_document", doc.id, {"verified": False}, {"verified": True, "authorized": doc.authorized}, None, admin)
    db.session.commit()
    return jsonify({"document": doc.to_dict()})


@admin_product_docs_bp.post("/<int:doc_id>/unverify")
@require_head_admin
def unverify_doc(doc_id):
    admin, doc = current_admin(), db.session.get(ProductDocument, doc_id)
    if doc is None:
        return _bad("Document not found", 404)
    doc.verified = doc.authorized = False
    doc.verified_by = doc.verified_at = None
    audit.record("product_doc_withdrawn", "product_document", doc.id, {"verified": True}, {"verified": False}, str((request.get_json(silent=True) or {}).get("reason") or "")[:300] or None, admin)
    db.session.commit()
    return jsonify({"document": doc.to_dict()})


@admin_product_docs_bp.delete("/<int:doc_id>")
@require_permission("chatbot")
def delete_doc(doc_id):
    admin, doc = current_admin(), db.session.get(ProductDocument, doc_id)
    if doc is None:
        return _bad("Document not found", 404)
    audit.record("product_doc_deleted", "product_document", doc.id, {"title": doc.title, "verified": doc.verified}, None, None, admin)
    db.session.delete(doc)
    db.session.commit()
    return jsonify({"message": "Document deleted"})


@admin_product_docs_bp.post("/test")
@require_permission("chatbot")
def try_recommender():
    """Lets an admin see exactly what the assistant would answer, without saving anything."""
    data = request.get_json() or {}
    message = str(data.get("message") or "").strip()[:500]
    if not message:
        return _bad("Type a requirement to try")
    context = data.get("context") if isinstance(data.get("context"), dict) else None
    return jsonify(recommender.recommend(message, context, log=False))


@admin_product_docs_bp.get("/stats")
@require_permission("chatbot")
def stats():
    total = RecommendationLog.query.count()
    by_status = dict(db.session.query(RecommendationLog.status, func.count(RecommendationLog.id)).group_by(RecommendationLog.status).all())
    return jsonify({
        "total": total, "byStatus": by_status,
        "usableDocuments": ProductDocument.query.filter_by(verified=True, authorized=True).count(),
        "allDocuments": ProductDocument.query.count(),
        "averageMs": int(db.session.query(func.avg(RecommendationLog.elapsed_ms)).scalar() or 0),
    })
