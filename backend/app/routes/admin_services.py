from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Service, ServiceBooking, User
from app.models.service import BOOKING_STATUSES
from app.services.email_service import send_email
from app.services.service_catalog import ServiceInputError, apply_areas, clean_areas
from app.utils.auth_decorators import require_permission

admin_services_bp = Blueprint("admin_services", __name__, url_prefix="/api/admin/services")

TRANSITIONS = {
    "requested": {"confirmed", "cancelled"},
    "confirmed": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def _read_basics(data, creating):
    values = {}
    if creating or "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise ServiceInputError("Service name is required")
        values["name"] = name[:150]
    if creating or "description" in data:
        description = str(data.get("description") or "").strip()
        if not description:
            raise ServiceInputError("A description is required")
        values["description"] = description
    if "category" in data:
        values["category"] = (str(data.get("category") or "").strip()[:80]) or None
    if "requirements" in data:
        values["requirements"] = (str(data.get("requirements") or "").strip()) or None
    if "isActive" in data:
        values["is_active"] = bool(data["isActive"])
    return values


@admin_services_bp.get("")
@require_permission("services")
def list_services():
    services = Service.query.order_by(Service.name).all()
    return jsonify({"services": [s.to_dict(admin_view=True) for s in services]})


@admin_services_bp.post("")
@require_permission("services")
def create_service():
    data = request.get_json() or {}
    try:
        values = _read_basics(data, creating=True)
        areas = clean_areas(data.get("areas") or [])
    except ServiceInputError as error:
        return jsonify({"error": str(error)}), 400

    service = Service(is_active=values.pop("is_active", True), **values)
    db.session.add(service)
    db.session.flush()
    apply_areas(service, areas)
    db.session.commit()
    return jsonify({"service": service.to_dict(admin_view=True)}), 201


@admin_services_bp.put("/<int:service_id>")
@require_permission("services")
def update_service(service_id):
    service = Service.query.get_or_404(service_id)

    data = request.get_json() or {}
    try:
        values = _read_basics(data, creating=False)
        areas = clean_areas(data["areas"]) if "areas" in data else None
    except ServiceInputError as error:
        return jsonify({"error": str(error)}), 400

    for column, value in values.items():
        setattr(service, column, value)
    if areas is not None:
        apply_areas(service, areas)
    db.session.commit()
    return jsonify({"service": service.to_dict(admin_view=True)})


@admin_services_bp.delete("/<int:service_id>")
@require_permission("services")
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    if ServiceBooking.query.filter_by(service_id=service.id).first():
        return jsonify({
            "error": "This service has bookings and cannot be deleted. Switch it off instead to keep the history."
        }), 409
    db.session.delete(service)
    db.session.commit()
    return jsonify({"message": "Service deleted"})


@admin_services_bp.get("/bookings")
@require_permission("services")
def list_bookings():
    query = ServiceBooking.query.join(Service, Service.id == ServiceBooking.service_id)
    status = request.args.get("status")
    if status in BOOKING_STATUSES:
        query = query.filter(ServiceBooking.status == status)
    rows = query.order_by(ServiceBooking.created_at.desc()).limit(300).all()
    return jsonify({"bookings": [b.to_dict(admin_view=True) for b in rows]})


@admin_services_bp.post("/bookings/<int:booking_id>/status")
@require_permission("services")
def update_booking_status(booking_id):
    booking = ServiceBooking.query.get_or_404(booking_id)

    new_status = (request.get_json() or {}).get("status")
    if new_status not in BOOKING_STATUSES:
        return jsonify({"error": "Invalid status"}), 400
    if new_status not in TRANSITIONS[booking.status]:
        return jsonify({"error": f"A {booking.status} booking cannot be changed to {new_status}"}), 400

    booking.status = new_status
    db.session.commit()

    email = booking.customer_email or (db.session.get(User, booking.user_id).email)
    if email and new_status in ("confirmed", "cancelled", "completed"):
        send_email(
            email, f"Service request {new_status} - {booking.booking_number}",
            f"Hi {booking.customer_name},\n\nYour request for {booking.service_name} in {booking.area_name} "
            f"({booking.booking_number}) is now {new_status}.",
            user_id=booking.user_id,
        )
    return jsonify({"booking": booking.to_dict(admin_view=True)})
