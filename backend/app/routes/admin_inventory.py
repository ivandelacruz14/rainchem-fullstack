from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.extensions import db
from app.models import AuditLog, InventoryAlert, InventoryMovement, Order, Product
from app.models.inventory import ALERT_CATEGORIES, MOVEMENT_TYPES
from app.services import audit, inventory
from app.utils.auth_decorators import current_admin, require_head_admin, require_permission

admin_inventory_bp = Blueprint("admin_inventory", __name__, url_prefix="/api/admin/inventory")

STATUSES = ("open", "under_review", "resolved")
MANUAL_TYPES = ("received", "adjustment", "write_off")
MAX_PAGE = 100


def _fail(message, status=400):
    return jsonify({"error": message}), status


def _page():
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(MAX_PAGE, max(5, int(request.args.get("per_page", 25))))
    except ValueError:
        page, per_page = 1, 25
    return page, per_page


@admin_inventory_bp.get("/overview")
@require_permission("products")
def overview():
    return jsonify({"products": inventory.stock_overview()})


@admin_inventory_bp.get("/movements")
@require_permission("products")
def movements():
    query = InventoryMovement.query
    if request.args.get("product_id"):
        query = query.filter(InventoryMovement.product_id == int(request.args["product_id"]))
    if request.args.get("order_id"):
        query = query.filter(InventoryMovement.order_id == int(request.args["order_id"]))
    page, per_page = _page()
    total = query.count()
    rows = query.order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({"movements": [m.to_dict() for m in rows], "total": total, "page": page, "perPage": per_page})


@admin_inventory_bp.post("/movements")
@require_head_admin
def add_movement():
    """Stock received, damage or write-off, or a manual adjustment. Head Admin only, always with a reason
    (other admins change stock through a product edit request, which needs approval)."""
    admin = current_admin()
    data = request.get_json() or {}
    movement_type = data.get("type")
    reason = str(data.get("reason") or "").strip()
    if movement_type not in MANUAL_TYPES:
        return _fail("Choose stock received, damaged or written off, or an adjustment")
    if not reason:
        return _fail("A reason is required for every stock movement")
    product = db.session.get(Product, data.get("productId")) if data.get("productId") else None
    if product is None or product.category == "Services":
        return _fail("Choose a product", 404)
    try:
        quantity = int(data.get("quantity"))
    except (TypeError, ValueError):
        return _fail("Enter a whole number of units")
    if quantity == 0:
        return _fail("The quantity cannot be zero")
    if movement_type == "received" and quantity < 0:
        return _fail("Stock received must be a positive number")
    if movement_type == "write_off":
        quantity = -abs(quantity)
    if product.stock + quantity < 0:
        return _fail("That would make the stock negative")
    inventory.record_movement(product, movement_type, quantity, reason[:255], admin)
    audit.record("stock_movement", "product", product.id, {"stock": product.stock - quantity}, {"stock": product.stock}, reason, admin)
    db.session.commit()
    return jsonify({"product": {"id": product.id, "stock": product.stock}}), 201


@admin_inventory_bp.get("/alerts")
@require_permission("products")
def list_alerts():
    if request.args.get("refresh") == "1":
        inventory.run_scan()
    query = InventoryAlert.query
    status = request.args.get("status")
    if status == "unresolved":
        query = query.filter(InventoryAlert.status != "resolved")
    elif status in STATUSES:
        query = query.filter(InventoryAlert.status == status)
    for arg, column in (("category", InventoryAlert.category), ("product_id", InventoryAlert.product_id), ("order_id", InventoryAlert.order_id)):
        value = request.args.get(arg)
        if value not in (None, "", "all"):
            query = query.filter(column == (value if arg == "category" else int(value)))
    if request.args.get("from"):
        query = query.filter(InventoryAlert.detected_at >= datetime.fromisoformat(request.args["from"]))
    if request.args.get("to"):
        query = query.filter(InventoryAlert.detected_at < datetime.fromisoformat(request.args["to"]).replace(hour=23, minute=59, second=59))
    page, per_page = _page()
    total = query.count()
    rows = query.order_by(InventoryAlert.detected_at.desc(), InventoryAlert.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    counts = dict(db.session.query(InventoryAlert.status, func.count(InventoryAlert.id)).group_by(InventoryAlert.status).all())
    return jsonify({
        "alerts": [a.to_dict() for a in rows], "total": total, "page": page, "perPage": per_page,
        "counts": {s: counts.get(s, 0) for s in STATUSES},
        "categories": [{"key": k, "label": v} for k, v in ALERT_CATEGORIES.items()],
    })


@admin_inventory_bp.get("/alerts/count")
@require_permission("products")
def alert_count():
    return jsonify({"open": InventoryAlert.query.filter(InventoryAlert.status != "resolved").count()})


@admin_inventory_bp.post("/scan")
@require_permission("products")
def scan():
    created = inventory.run_scan()
    return jsonify({"created": len(created), "open": InventoryAlert.query.filter(InventoryAlert.status != "resolved").count()})


@admin_inventory_bp.get("/alerts/<int:alert_id>")
@require_permission("products")
def alert_detail(alert_id):
    alert = db.session.get(InventoryAlert, alert_id)
    if alert is None:
        return _fail("Alert not found", 404)
    query = InventoryMovement.query
    if alert.order_id and not alert.product_id:
        query = query.filter(InventoryMovement.order_id == alert.order_id)
    elif alert.product_id:
        query = query.filter(InventoryMovement.product_id == alert.product_id)
        if alert.order_id:
            query = query.filter(InventoryMovement.order_id == alert.order_id)
    else:
        query = query.filter(False)
    movements = query.order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.desc()).limit(30).all()
    order = db.session.get(Order, alert.order_id) if alert.order_id else None
    audits = AuditLog.query.filter(AuditLog.entity_type == "inventory_alert", AuditLog.entity_id == str(alert.id)).order_by(AuditLog.id).all()
    return jsonify({
        "alert": alert.to_dict(),
        "stillApplies": inventory.still_applies(alert),
        "movements": [m.to_dict() for m in movements],
        "order": {"id": order.id, "orderNumber": order.order_number, "status": order.status, "paymentStatus": order.payment_status,
                  "paymentReference": order.payment_reference, "total": float(order.total)} if order else None,
        "history": [a.to_dict() for a in audits],
    })


def _alert_or_404(alert_id):
    alert = db.session.get(InventoryAlert, alert_id)
    return alert


@admin_inventory_bp.post("/alerts/<int:alert_id>/review")
@require_permission("products")
def start_review(alert_id):
    alert, admin = _alert_or_404(alert_id), current_admin()
    if alert is None:
        return _fail("Alert not found", 404)
    if alert.status == "resolved":
        return _fail("This alert is already resolved", 409)
    alert.status, alert.assigned_admin_id, alert.assigned_name = "under_review", admin.id, admin.name
    audit.record("alert_review_started", "inventory_alert", alert.id, None, {"assignedTo": admin.name}, None, admin)
    db.session.commit()
    return jsonify({"alert": alert.to_dict()})


@admin_inventory_bp.post("/alerts/<int:alert_id>/note")
@require_permission("products")
def add_note(alert_id):
    alert, admin = _alert_or_404(alert_id), current_admin()
    if alert is None:
        return _fail("Alert not found", 404)
    note = str((request.get_json() or {}).get("note") or "").strip()
    if not note:
        return _fail("Write a note first")
    stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    alert.resolution_note = ((alert.resolution_note + "\n") if alert.resolution_note else "") + f"[{stamp} {admin.name}] {note[:500]}"
    audit.record("alert_note", "inventory_alert", alert.id, None, {"note": note[:500]}, None, admin)
    db.session.commit()
    return jsonify({"alert": alert.to_dict()})


@admin_inventory_bp.post("/alerts/<int:alert_id>/resolve")
@require_permission("products")
def resolve(alert_id):
    """Closes the alert with a note. This never changes stock or any other record."""
    alert, admin = _alert_or_404(alert_id), current_admin()
    if alert is None:
        return _fail("Alert not found", 404)
    if alert.status == "resolved":
        return _fail("This alert is already resolved", 409)
    note = str((request.get_json() or {}).get("note") or "").strip()
    if not note:
        return _fail("Write a resolution note explaining what you found")
    stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    alert.resolution_note = ((alert.resolution_note + "\n") if alert.resolution_note else "") + f"[{stamp} {admin.name}] {note[:500]}"
    alert.status, alert.resolved_at, alert.resolved_by = "resolved", datetime.utcnow(), admin.name
    audit.record("alert_resolved", "inventory_alert", alert.id, {"status": "open"}, {"status": "resolved"}, note, admin)
    db.session.commit()
    return jsonify({"alert": alert.to_dict()})


@admin_inventory_bp.post("/alerts/<int:alert_id>/correct")
@require_head_admin
def correct(alert_id):
    """The authorised way to fix a stock discrepancy, after investigating. Two choices:
    align_to_history sets the recorded stock to the expected figure; accept_recorded adds an
    adjustment so the history matches the recorded stock. Both need a reason and are audited."""
    alert, admin = _alert_or_404(alert_id), current_admin()
    if alert is None:
        return _fail("Alert not found", 404)
    if alert.status == "resolved":
        return _fail("This alert is already resolved", 409)
    if alert.category != "stock_mismatch" or alert.product_id is None:
        return _fail("Only stock discrepancies can be corrected here. Resolve other alerts with a note.")
    data = request.get_json() or {}
    mode, reason = data.get("mode"), str(data.get("reason") or "").strip()
    if mode not in ("align_to_history", "accept_recorded"):
        return _fail("Choose how to correct the stock")
    if not reason:
        return _fail("A reason is required for a correction")
    product = db.session.get(Product, alert.product_id)
    if product is None:
        return _fail("The product no longer exists", 404)
    expected = inventory.expected_stock().get(product.id, 0)
    recorded = product.stock
    if expected == recorded:
        return _fail("The stock already matches its history, so there is nothing to correct", 409)

    if mode == "align_to_history":
        # the history is right: put the recorded stock back in line with it. The audit log below keeps
        # the original value, the corrected value, the reason, who did it and when.
        with inventory.stock_context("adjustment", record=False, admin=admin):
            product.stock = expected
        new_value = product.stock
    else:
        # the recorded stock is right: add the missing adjustment to the history without touching the stock
        db.session.add(InventoryMovement(
            product_id=product.id, product_name=product.name, movement_type="adjustment",
            quantity_change=recorded - expected, reason=f"Correction (recorded stock accepted): {reason}"[:255],
            actor_admin_id=admin.id, actor_name=admin.name,
        ))
        new_value = recorded
    audit.record("stock_correction", "product", product.id, {"recordedStock": recorded, "expectedStock": expected},
                 {"recordedStock": new_value, "mode": mode}, reason, admin)
    alert.status, alert.resolved_at, alert.resolved_by = "resolved", datetime.utcnow(), admin.name
    alert.resolution_note = ((alert.resolution_note + "\n") if alert.resolution_note else "") + \
        f"[{datetime.utcnow():%Y-%m-%d %H:%M} {admin.name}] Corrected ({mode.replace('_', ' ')}): {reason[:400]}"
    db.session.commit()
    return jsonify({"alert": alert.to_dict(), "stock": product.stock, "expected": inventory.expected_stock().get(product.id, 0)})


@admin_inventory_bp.get("/audit")
@require_permission("products")
def audit_trail():
    page, per_page = _page()
    query = AuditLog.query.filter(AuditLog.entity_type.in_(("product", "inventory_alert")))
    total = query.count()
    rows = query.order_by(AuditLog.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({"entries": [r.to_dict() for r in rows], "total": total, "page": page, "perPage": per_page})
