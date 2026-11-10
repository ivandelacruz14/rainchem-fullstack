from flask import Blueprint, Response, jsonify, request

from app.extensions import db
from app.models import Admin, AuditLog, Order, OrderItem, Product, SalesRecord
from app.services import audit, sales_analytics as dates, sales_import, sales_ledger as ledger
from app.utils.auth_decorators import current_admin, require_head_admin, require_permission

admin_sales_records_bp = Blueprint("admin_sales_records", __name__, url_prefix="/api/admin/sales-records")

EXPORT_LIMIT = 50000


def _bad(error):
    return jsonify({"error": str(error)}), 400


@admin_sales_records_bp.get("")
@require_permission("analytics")
def list_records():
    try:
        query = ledger.filtered_query(request.args)
        page, per_page = ledger.page_of(request.args)
    except (dates.ReportError, ValueError) as error:
        return _bad(error)
    totals = ledger.totals_for(query)
    rows = ledger.sorted_query(query, request.args).offset((page - 1) * per_page).limit(per_page).all()
    products = Product.query.filter(Product.category != "Services").order_by(Product.name).all()
    categories = sorted({c for (c,) in db.session.query(SalesRecord.category).distinct() if c})
    return jsonify({
        "records": [r.to_dict() for r in rows], "total": totals["rows"], "page": page, "perPage": per_page,
        "pages": max(1, -(-totals["rows"] // per_page)), "totals": totals,
        "filters": {"products": [{"id": p.id, "name": p.name} for p in products], "categories": categories},
    })


@admin_sales_records_bp.get("/summary")
@require_permission("analytics")
def summary():
    try:
        start, end = dates.resolve_range(request.args.get("from"), request.args.get("to"))
        return jsonify(ledger.build_summary(start, end, request.args.get("granularity", "daily")))
    except dates.ReportError as error:
        return _bad(error)


@admin_sales_records_bp.get("/export.csv")
@require_permission("analytics")
def export_csv():
    """The filtered rows as a CSV that opens in Excel. Every export is written to the audit log."""
    try:
        query = ledger.filtered_query(request.args)
    except (dates.ReportError, ValueError) as error:
        return _bad(error)
    rows = ledger.sorted_query(query, request.args).limit(EXPORT_LIMIT).all()
    audit.record("sales_export", "sales_records", "csv", None, {"rows": len(rows), "filters": {k: v for k, v in request.args.items() if v}}, None)
    db.session.commit()
    stamp = dates.local_today().isoformat()
    return Response(
        ledger.to_csv(rows), mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="rainchem-sales-records-{stamp}.csv"', "Cache-Control": "no-store"},
    )


@admin_sales_records_bp.get("/<int:record_id>")
@require_permission("analytics")
def detail(record_id):
    record = db.session.get(SalesRecord, record_id)
    if record is None:
        return jsonify({"error": "Record not found"}), 404
    order = db.session.get(Order, record.order_id)
    siblings = SalesRecord.query.filter_by(order_id=record.order_id).order_by(SalesRecord.id).all()
    history = AuditLog.query.filter_by(entity_type="sales_record", entity_id=str(record.id)).order_by(AuditLog.id).all()
    return jsonify({
        "record": record.to_dict(),
        "order": {
            "id": order.id, "orderNumber": order.order_number, "status": order.status, "paymentMethod": order.payment_method,
            "paymentStatus": order.payment_status, "paymentReference": order.payment_reference,
            "subtotal": float(order.subtotal), "shippingFee": float(order.shipping_fee), "total": float(order.total),
            "createdAt": order.created_at.isoformat() if order.created_at else None,
            "paidAt": order.paid_at.isoformat() if order.paid_at else None,
        } if order else None,
        "lines": [r.to_dict() for r in siblings],
        "corrections": [h.to_dict() for h in history],
    })


@admin_sales_records_bp.post("/<int:record_id>/correction")
@require_head_admin
def correct(record_id):
    """Only descriptive fields can be corrected (SKU, category, notes). Amounts always come from the order.
    A reason is required and every correction is kept in the audit log with the old and new value."""
    record, admin = db.session.get(SalesRecord, record_id), current_admin()
    if record is None:
        return jsonify({"error": "Record not found"}), 404
    data = request.get_json() or {}
    field, reason = data.get("field"), str(data.get("reason") or "").strip()
    if field not in ledger.OVERRIDABLE:
        return _bad("Only the SKU, category and notes can be corrected. Amounts come from the order.")
    if not reason:
        return _bad("A reason is required for every correction")
    value = str(data.get("value") or "").strip()
    limit = {"sku": 40, "category": 80, "notes": 500}[field]
    if len(value) > limit:
        return _bad(f"The {field} can be at most {limit} characters")
    old = getattr(record, field)
    record.overrides = {**(record.overrides or {}), field: value or None}
    setattr(record, field, value or None)
    audit.record("sales_record_correction", "sales_record", record.id, {field: old}, {field: value or None}, reason, admin)
    db.session.commit()
    return jsonify({"record": record.to_dict()})


@admin_sales_records_bp.post("/reconcile")
@require_head_admin
def reconcile():
    """Rebuilds every record from its order. Use it if something looks out of step; it is safe to repeat."""
    count = ledger.sync_all()
    audit.record("sales_reconcile", "sales_records", "all", None, {"orders": count}, None, current_admin())
    db.session.commit()
    return jsonify({"orders": count, "records": SalesRecord.query.count()})


def _upload():
    upload = request.files.get("file")
    if upload is None or not (upload.filename or "").lower().endswith(".xlsx"):
        return None
    return upload


@admin_sales_records_bp.post("/import/preview")
@require_head_admin
def import_preview():
    """Checks an Excel file and says what would be imported. Nothing is saved."""
    upload = _upload()
    if upload is None:
        return _bad("Choose an .xlsx file.")
    try:
        summary, _ = sales_import.analyse(upload.read(sales_import.MAX_BYTES + 1))
    except sales_import.ImportFileError as error:
        return _bad(str(error))
    return jsonify(summary)


@admin_sales_records_bp.post("/import")
@require_head_admin
def import_commit():
    """Saves the valid rows of an Excel file as one batch. The form field confirm=yes is required."""
    upload = _upload()
    if upload is None:
        return _bad("Choose an .xlsx file.")
    if request.form.get("confirm") != "yes":
        return _bad("Check the preview first, then confirm the import.")
    try:
        batch, summary = sales_import.commit(upload.read(sales_import.MAX_BYTES + 1), current_admin(), upload.filename)
    except sales_import.ImportFileError as error:
        return _bad(str(error))
    return jsonify({"batch": batch, **summary}), 201


@admin_sales_records_bp.get("/imports")
@require_permission("analytics")
def list_imports():
    return jsonify({"batches": sales_import.list_batches()})


@admin_sales_records_bp.delete("/imports/<batch>")
@require_head_admin
def remove_import(batch):
    """Removes every row of one import batch. Real orders are never touched."""
    removed = sales_import.delete_batch(batch[:40], current_admin())
    if not removed:
        return jsonify({"error": "That import was not found"}), 404
    return jsonify({"removed": removed})
