from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import ChangeRequest
from app.services import change_requests as service
from app.utils.auth_decorators import current_admin, require_admin, require_head_admin

admin_approvals_bp = Blueprint("admin_approvals", __name__, url_prefix="/api/admin/approvals")

STATUSES = ("pending", "approved", "rejected", "cancelled")


def _visible(request_row, admin):
    return admin.is_head or request_row.requested_by == admin.id


def _get(request_id, admin):
    row = db.session.get(ChangeRequest, request_id)
    if row is None or not _visible(row, admin):
        return None
    return row


def _fail(error):
    return jsonify({"error": str(error)}), error.status


@admin_approvals_bp.get("")
@require_admin
def list_requests():
    """A Head Admin sees every request. Everyone else sees only their own."""
    admin = current_admin()
    query = ChangeRequest.query
    if not admin.is_head:
        query = query.filter(ChangeRequest.requested_by == admin.id)
    status = request.args.get("status")
    if status in STATUSES:
        query = query.filter(ChangeRequest.status == status)
    rows = query.order_by(ChangeRequest.created_at.desc()).limit(200).all()
    return jsonify({"requests": [service.to_dict(r) for r in rows]})


@admin_approvals_bp.get("/pending-count")
@require_admin
def pending_count():
    admin = current_admin()
    query = ChangeRequest.query.filter_by(status="pending")
    if not admin.is_head:
        query = query.filter(ChangeRequest.requested_by == admin.id)
    return jsonify({"count": query.count()})


@admin_approvals_bp.get("/<int:request_id>")
@require_admin
def get_request(request_id):
    row = _get(request_id, current_admin())
    if row is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"request": service.to_dict(row, detail=True)})


@admin_approvals_bp.post("/<int:request_id>/approve/start")
@require_head_admin
def start_approval(request_id):
    """Step 1 of approving: confirm the Head Admin's password, then email a one-time code."""
    row = db.session.get(ChangeRequest, request_id)
    if row is None:
        return jsonify({"error": "Not found"}), 404
    try:
        info = service.start_approval(row, current_admin(), (request.get_json() or {}).get("password"))
    except service.ApprovalError as error:
        return _fail(error)
    return jsonify(info)


@admin_approvals_bp.post("/<int:request_id>/approve/confirm")
@require_head_admin
def confirm_approval(request_id):
    """Step 2: the emailed code. The change is applied only if the code is right."""
    row = db.session.get(ChangeRequest, request_id)
    if row is None:
        return jsonify({"error": "Not found"}), 404
    try:
        service.confirm_approval(row, current_admin(), (request.get_json() or {}).get("code"))
    except service.ApprovalError as error:
        return _fail(error)
    return jsonify({"request": service.to_dict(row, detail=True)})


@admin_approvals_bp.post("/<int:request_id>/reject")
@require_head_admin
def reject_request(request_id):
    row = db.session.get(ChangeRequest, request_id)
    if row is None:
        return jsonify({"error": "Not found"}), 404
    try:
        service.reject(row, current_admin(), (request.get_json() or {}).get("note"))
    except service.ApprovalError as error:
        return _fail(error)
    return jsonify({"request": service.to_dict(row)})


@admin_approvals_bp.post("/<int:request_id>/cancel")
@require_admin
def cancel_request(request_id):
    admin = current_admin()
    row = _get(request_id, admin)
    if row is None:
        return jsonify({"error": "Not found"}), 404
    try:
        service.cancel(row, admin)
    except service.ApprovalError as error:
        return _fail(error)
    return jsonify({"request": service.to_dict(row)})
