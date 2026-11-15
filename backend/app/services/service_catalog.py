import random
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models import ServiceBooking

MAX_PRICE = Decimal("1000000")


class ServiceInputError(ValueError):
    pass


def availability_for(service, area_name):
    """What a customer should see for one service in one area. Prices come only from the
    stored area records, so a changed browser request cannot change them."""
    area = service.area_named(area_name)
    if area is None:
        return {"area": area_name, "available": False, "price": None, "reason": "Not offered in this area"}
    if not area.is_available:
        return {"area": area.area_name, "available": False, "price": None,
                "reason": "Currently unavailable in this area"}
    return {"area": area.area_name, "available": True, "price": float(area.price), "reason": None}


def parse_price(value):
    try:
        price = Decimal(str(value))
        if not price.is_finite() or price < 0 or price > MAX_PRICE:
            raise InvalidOperation
        return price.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise ServiceInputError("Enter a valid price (0 or more) for each area")


def clean_areas(raw_areas):
    """Validates the area list sent by the admin form. Returns normalised dicts."""
    if not isinstance(raw_areas, list):
        raise ServiceInputError("Areas must be a list")
    cleaned, names = [], set()
    for entry in raw_areas:
        name = str(entry.get("name") or "").strip()
        if len(name) < 2 or len(name) > 120:
            raise ServiceInputError("Each area needs a name of 2 to 120 characters")
        if name.lower() in names:
            raise ServiceInputError(f"The area \"{name}\" is listed twice")
        names.add(name.lower())
        cleaned.append({
            "id": entry.get("id"),
            "name": name,
            "price": parse_price(entry.get("price")),
            "available": bool(entry.get("isAvailable", True)),
            "notes": (str(entry.get("notes") or "").strip()[:255]) or None,
        })
    return cleaned


def apply_areas(service, cleaned):
    """Updates the service's areas in place. Areas referenced by past bookings are never
    deleted, only marked unavailable, so booking history stays intact."""
    from app.models import ServiceArea

    by_id = {a.id: a for a in service.areas}
    by_name = {a.area_name.lower(): a for a in service.areas}
    kept = set()
    for entry in cleaned:
        area = by_id.get(entry["id"]) if entry["id"] is not None else None
        area = area or by_name.get(entry["name"].lower())
        if area is None:
            area = ServiceArea(service_id=service.id)
            service.areas.append(area)
        area.area_name = entry["name"]
        area.price = entry["price"]
        area.is_available = entry["available"]
        area.notes = entry["notes"]
        kept.add(id(area))

    for area in list(service.areas):
        if id(area) in kept:
            continue
        used = area.id and ServiceBooking.query.filter_by(service_area_id=area.id).first()
        if used:
            area.is_available = False
        else:
            service.areas.remove(area)


def generate_booking_number():
    today = datetime.utcnow().strftime("%Y%m%d")
    for attempt in range(40):
        suffix = random.randint(100000, 999999) if attempt >= 20 else random.randint(1000, 9999)
        number = f"SVC-{today}-{suffix}"
        if not db.session.query(ServiceBooking.id).filter_by(booking_number=number).first():
            return number
    raise RuntimeError("Could not generate a unique booking number")
