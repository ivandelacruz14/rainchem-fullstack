from datetime import date, datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Service, ServiceBooking, User
from app.services.auth_utils import is_valid_email, is_valid_phone
from app.services.email_service import send_email
from app.services.sales_analytics import local_today
from app.services.service_catalog import availability_for, generate_booking_number
from app.utils.auth_decorators import current_user_id, require_user

services_bp = Blueprint("services", __name__, url_prefix="/api/services")


def _public_services():
    services = Service.query.filter_by(is_active=True).order_by(Service.name).all()
    return [s for s in services if s.areas]


@services_bp.get("")
def list_services():
    """Public. With ?area=Name each service also shows whether it is offered there and at what price."""
    area = (request.args.get("area") or "").strip()
    result = []
    for service in _public_services():
        data = service.to_dict()
        if area:
            data["selected"] = availability_for(service, area)
        result.append(data)
    return jsonify({"services": result})


@services_bp.get("/areas")
def list_areas():
    names = {}
    for service in _public_services():
        for area in service.areas:
            if area.is_available:
                names.setdefault(area.area_name.lower(), area.area_name)
    return jsonify({"areas": sorted(names.values(), key=str.lower)})


@services_bp.post("/bookings")
@require_user
def create_booking():
    data = request.get_json() or {}
    user = db.session.get(User, current_user_id())

    service = db.session.get(Service, data.get("serviceId")) if data.get("serviceId") else None
    if not service or not service.is_active or not service.areas:
        return jsonify({"error": "This service is not available"}), 404

    area_ref = data.get("areaId") if data.get("areaId") else data.get("area")
    area = next((a for a in service.areas if a.id == area_ref), None) if isinstance(area_ref, int) \
        else service.area_named(area_ref)
    if area is None:
        return jsonify({"error": "This service is not offered in the area you selected"}), 400
    if not area.is_available:
        return jsonify({"error": f"This service is currently unavailable in {area.area_name}"}), 400

    name = str(data.get("name") or "").strip()
    phone = str(data.get("phone") or "").strip()
    email = str(data.get("email") or user.email or "").strip().lower()
    address = str(data.get("address") or "").strip()
    notes = str(data.get("notes") or "").strip()

    if not name or len(name) > 150:
        return jsonify({"error": "Please enter your name"}), 400
    if not is_valid_phone(phone):
        return jsonify({"error": "Please enter a valid contact number"}), 400
    if email and not is_valid_email(email):
        return jsonify({"error": "Please enter a valid email address"}), 400
    if not address or len(address) > 255:
        return jsonify({"error": "Please enter the address where the service is needed"}), 400
    if len(notes) > 500:
        return jsonify({"error": "Notes can be at most 500 characters"}), 400

    preferred = None
    if data.get("preferredDate"):
        try:
            preferred = date.fromisoformat(str(data["preferredDate"]))
        except ValueError:
            return jsonify({"error": "Choose a valid preferred date"}), 400
        if preferred < local_today():
            return jsonify({"error": "The preferred date cannot be in the past"}), 400

    booking = ServiceBooking(
        booking_number=generate_booking_number(),
        user_id=user.id,
        service_id=service.id,
        service_area_id=area.id,
        service_name=service.name,
        area_name=area.area_name,
        price=area.price,  # always the stored price for that area, never a value from the request
        customer_name=name, customer_phone=phone, customer_email=email or None,
        address=address, preferred_date=preferred, notes=notes or None,
        status="requested",
    )
    db.session.add(booking)
    db.session.commit()

    if booking.customer_email:
        send_email(
            booking.customer_email, f"Service request received - {booking.booking_number}",
            f"Hi {name},\n\nWe received your request for {service.name} in {area.area_name} "
            f"(PHP {float(area.price):.2f}). Our team will confirm it with you. "
            "Payment is arranged when the service is done.\n\n"
            f"Reference: {booking.booking_number}",
            user_id=user.id,
        )
    return jsonify({"booking": booking.to_dict()}), 201


@services_bp.get("/bookings")
@require_user
def my_bookings():
    rows = (
        ServiceBooking.query.filter_by(user_id=current_user_id())
        .order_by(ServiceBooking.created_at.desc())
        .all()
    )
    return jsonify({"bookings": [b.to_dict() for b in rows]})


@services_bp.post("/bookings/<int:booking_id>/cancel")
@require_user
def cancel_booking(booking_id):
    booking = db.session.get(ServiceBooking, booking_id)
    if not booking or booking.user_id != current_user_id():
        return jsonify({"error": "Not found"}), 404
    if booking.status != "requested":
        return jsonify({"error": "This request can no longer be cancelled"}), 400
    booking.status = "cancelled"
    db.session.commit()
    return jsonify({"booking": booking.to_dict()})
