from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Service, ServiceArea, ServiceBooking
from app.models.service import BOOKING_STATUSES
from app.services.auth_utils import is_valid_phone
from app.utils.auth_decorators import (
    require_user, require_permission, current_user_id, current_admin,
)

services_bp = Blueprint("services", __name__, url_prefix="/api/services")
admin_services_bp = Blueprint("admin_services", __name__, url_prefix="/api/admin/services")


def _money(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return None
    if amount < 0 or amount > Decimal("9999999"):
        return None
    return amount


def _can_edit(admin, service):
    return admin.is_head or service.owner_admin_id == admin.id


@services_bp.get("")
def list_public_services():
    services = Service.query.filter_by(is_active=True).order_by(Service.name).all()
    visible = [s for s in services if any(a.is_available for a in s.areas)]
    area_names = sorted({a.area_name for s in visible for a in s.areas if a.is_available})
    return jsonify({
        "services": [s.to_dict(include_unavailable=True) for s in services],
        "areas": area_names,
    })


@services_bp.post("/<int:service_id>/bookings")
@require_user
def create_booking(service_id):
    data = request.get_json() or {}
    service = Service.query.get_or_404(service_id)
    if not service.is_active:
        return jsonify({"error": "This service is not available right now"}), 400

    area = None
    try:
        area_id = int(data.get("areaId"))
        area = ServiceArea.query.filter_by(id=area_id, service_id=service.id).first()
    except (TypeError, ValueError):
        pass
    if area is None:
        return jsonify({"error": "Please choose a service area"}), 400
    if not area.is_available:
        return jsonify({"error": f"{service.name} is not available in {area.area_name}"}), 400

    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    address = (data.get("address") or "").strip()
    notes = (data.get("notes") or "").strip()
    if not name or not address:
        return jsonify({"error": "Please enter your name and service address"}), 400
    if not is_valid_phone(phone):
        return jsonify({"error": "Please enter a valid contact number"}), 400
    if len(address) > 255 or len(notes) > 500:
        return jsonify({"error": "Address or notes are too long"}), 400

    preferred = None
    if data.get("preferredDate"):
        try:
            preferred = date.fromisoformat(str(data["preferredDate"]))
        except ValueError:
            return jsonify({"error": "Please enter a valid preferred date"}), 400
        if preferred < date.today():
            return jsonify({"error": "The preferred date cannot be in the past"}), 400

    # Price and names come from the database, never from the request.
    booking = ServiceBooking(
        user_id=current_user_id(), service_id=service.id, area_id=area.id,
        service_name=service.name, area_name=area.area_name, price=area.price,
        contact_name=name, contact_phone=phone, address=address,
        preferred_date=preferred, notes=notes or None, status="requested",
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify({"booking": booking.to_dict()}), 201


@services_bp.get("/bookings/mine")
@require_user
def my_bookings():
    bookings = (
        ServiceBooking.query.filter_by(user_id=current_user_id())
        .order_by(ServiceBooking.created_at.desc()).all()
    )
    return jsonify({"bookings": [b.to_dict() for b in bookings]})


@admin_services_bp.get("")
@require_permission("manage_services")
def list_admin_services():
    admin = current_admin()
    query = Service.query
    if not admin.is_head:
        query = query.filter_by(owner_admin_id=admin.id)
    return jsonify({"services": [s.to_dict() for s in query.order_by(Service.name).all()]})


@admin_services_bp.post("")
@require_permission("manage_services")
def create_service():
    admin = current_admin()
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    if not name or not description:
        return jsonify({"error": "Name and description are required"}), 400

    service = Service(
        name=name[:160], description=description,
        category=(data.get("category") or "").strip()[:80] or None,
        requirements=(data.get("requirements") or "").strip() or None,
        is_active=bool(data.get("isActive", True)),
        owner_admin_id=None if admin.is_head else admin.id,
    )
    db.session.add(service)
    db.session.commit()
    return jsonify({"service": service.to_dict()}), 201


def _load_editable_service(service_id):
    service = Service.query.get_or_404(service_id)
    if not _can_edit(current_admin(), service):
        return None, (jsonify({"error": "You can only edit services assigned to you"}), 403)
    return service, None


@admin_services_bp.put("/<int:service_id>")
@require_permission("manage_services")
def update_service(service_id):
    service, denied = _load_editable_service(service_id)
    if denied:
        return denied
    data = request.get_json() or {}

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Name cannot be empty"}), 400
        service.name = name[:160]
    if "description" in data:
        description = (data.get("description") or "").strip()
        if not description:
            return jsonify({"error": "Description cannot be empty"}), 400
        service.description = description
    if "category" in data:
        service.category = (data.get("category") or "").strip()[:80] or None
    if "requirements" in data:
        service.requirements = (data.get("requirements") or "").strip() or None
    if "isActive" in data:
        # Services are switched off, never deleted, so booking history stays intact.
        service.is_active = bool(data["isActive"])

    db.session.commit()
    return jsonify({"service": service.to_dict()})


@admin_services_bp.post("/<int:service_id>/areas")
@require_permission("manage_services")
def add_area(service_id):
    service, denied = _load_editable_service(service_id)
    if denied:
        return denied
    data = request.get_json() or {}
    area_name = (data.get("areaName") or "").strip()
    price = _money(data.get("price"))
    if not area_name:
        return jsonify({"error": "Please enter the location or service area"}), 400
    if price is None:
        return jsonify({"error": "Please enter a valid price"}), 400

    area = ServiceArea(
        service_id=service.id, area_name=area_name[:120], price=price,
        is_available=bool(data.get("isAvailable", True)),
        note=(data.get("note") or "").strip()[:255] or None,
    )
    db.session.add(area)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "This service already has that area"}), 409
    return jsonify({"service": service.to_dict()}), 201


@admin_services_bp.put("/<int:service_id>/areas/<int:area_id>")
@require_permission("manage_services")
def update_area(service_id, area_id):
    service, denied = _load_editable_service(service_id)
    if denied:
        return denied
    area = ServiceArea.query.filter_by(id=area_id, service_id=service.id).first_or_404()
    data = request.get_json() or {}

    if "areaName" in data:
        area_name = (data.get("areaName") or "").strip()
        if not area_name:
            return jsonify({"error": "Please enter the location or service area"}), 400
        area.area_name = area_name[:120]
    if "price" in data:
        price = _money(data.get("price"))
        if price is None:
            return jsonify({"error": "Please enter a valid price"}), 400
        area.price = price
    if "isAvailable" in data:
        area.is_available = bool(data["isAvailable"])
    if "note" in data:
        area.note = (data.get("note") or "").strip()[:255] or None

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "This service already has that area"}), 409
    return jsonify({"service": service.to_dict()})


@admin_services_bp.delete("/<int:service_id>/areas/<int:area_id>")
@require_permission("manage_services")
def delete_area(service_id, area_id):
    service, denied = _load_editable_service(service_id)
    if denied:
        return denied
    area = ServiceArea.query.filter_by(id=area_id, service_id=service.id).first_or_404()
    if ServiceBooking.query.filter_by(area_id=area.id).first():
        return jsonify({
            "error": "This area has bookings. Mark it unavailable instead of deleting it.",
        }), 409
    db.session.delete(area)
    db.session.commit()
    return jsonify({"service": service.to_dict()})


@admin_services_bp.get("/bookings")
@require_permission("manage_services")
def list_bookings():
    admin = current_admin()
    query = ServiceBooking.query.join(Service, Service.id == ServiceBooking.service_id)
    if not admin.is_head:
        query = query.filter(Service.owner_admin_id == admin.id)
    bookings = query.order_by(ServiceBooking.created_at.desc()).limit(200).all()
    return jsonify({"bookings": [b.to_dict() for b in bookings]})


@admin_services_bp.post("/bookings/<int:booking_id>/status")
@require_permission("manage_services")
def update_booking_status(booking_id):
    admin = current_admin()
    booking = ServiceBooking.query.get_or_404(booking_id)
    service = db.session.get(Service, booking.service_id)
    if not admin.is_head and (service is None or service.owner_admin_id != admin.id):
        return jsonify({"error": "You can only manage bookings for your own services"}), 403
    status = (request.get_json() or {}).get("status")
    if status not in BOOKING_STATUSES:
        return jsonify({"error": "Invalid status"}), 400
    booking.status = status
    db.session.commit()
    return jsonify({"booking": booking.to_dict()})
