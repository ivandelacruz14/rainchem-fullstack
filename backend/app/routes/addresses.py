from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import User, UserAddress
from app.services import locations
from app.services.locations import AddressError
from app.utils.auth_decorators import current_user_id, require_user

addresses_bp = Blueprint("addresses", __name__, url_prefix="/api/addresses")

LABELS = ("Home", "Work", "Temporary", "Other")
TEXT_FIELDS = {"houseNumber": 40, "street": 200, "subdivision": 200, "village": 200, "unit": 60, "landmark": 200, "instructions": 500}


def _error(message, status=400):
    return jsonify({"error": message}), status


def _place(p):
    return {"code": p.code, "name": p.name, "level": p.level}


@addresses_bp.get("/locations")
def list_locations():
    """Regions when no parent is given; otherwise the places directly inside the parent."""
    parent = request.args.get("parent") or None
    return jsonify({"places": [_place(p) for p in locations.children(parent)]})


@addresses_bp.get("/locations/<code>/zip")
def zip_for(code):
    place = locations.get_place(code)
    if not place:
        return _error("Place not found", 404)
    return jsonify({"code": code, "zipCode": locations.postal_code_for(place), "available": place.zip_code is not None})


@addresses_bp.get("")
@require_user
def my_addresses():
    rows = UserAddress.query.filter_by(user_id=current_user_id()).order_by(UserAddress.is_default.desc(), UserAddress.id).all()
    return jsonify({"addresses": [a.to_dict() for a in rows]})


def read_pin(data):
    """The customer's map pin. Both numbers or neither; it must be inside the Philippines."""
    lat, lng = data.get("latitude"), data.get("longitude")
    if lat in (None, "") and lng in (None, ""):
        return None, None
    try:
        lat, lng = round(float(lat), 6), round(float(lng), 6)
    except (TypeError, ValueError):
        raise AddressError("The map pin is not valid. Pin your location again.")
    if not (4.0 <= lat <= 22.0 and 116.0 <= lng <= 127.5):
        raise AddressError("The map pin is outside the Philippines. Pin your location again.")
    return lat, lng


def _read(data, existing=None):
    """Checks every field. Returns the values to store, or raises AddressError."""
    label = (data.get("label") or "Home").strip()
    if label not in LABELS:
        raise AddressError("Choose Home, Work, Temporary, or Other")
    region, province, city, barangay = locations.validate_chain(
        data.get("regionCode"), data.get("provinceCode") or None, data.get("cityCode"), data.get("barangayCode"))
    official_zip = locations.postal_code_for(barangay)
    typed_zip = (data.get("zipCode") or "").strip()
    if official_zip:
        if typed_zip and typed_zip != official_zip:
            raise AddressError(f"The ZIP code for {barangay.name} is {official_zip}")
        zip_code = official_zip
    else:
        if typed_zip and (len(typed_zip) != 4 or not typed_zip.isdigit()):
            raise AddressError("ZIP code must be 4 digits")
        zip_code = typed_zip or None
    latitude, longitude = read_pin(data)
    values = {
        "latitude": latitude, "longitude": longitude,
        "label": label, "region_code": region.code, "region_name": region.name,
        "province_code": province.code if province else None, "province_name": province.name if province else None,
        "city_code": city.code, "city_name": city.name, "barangay_code": barangay.code, "barangay_name": barangay.name,
        "zip_code": zip_code,
    }
    for key, limit in TEXT_FIELDS.items():
        values[key] = (data.get(key) or "").strip()[:limit] or None
    if not values["street"]:
        raise AddressError("Enter the street name")
    values["street"] = values["street"]
    return values


def _apply(address, values):
    for key, value in values.items():
        attr = {"houseNumber": "house_number"}.get(key, key)
        setattr(address, attr, value)


def _make_default(user, address):
    UserAddress.query.filter_by(user_id=user.id).update({"is_default": False})
    address.is_default = True
    # The checkout reads the account's address, so it follows the default.
    user.address_line1 = ", ".join(x for x in [address.unit, " ".join(x for x in [address.house_number, address.street] if x), address.subdivision, address.village, address.landmark] if x)
    user.address_city = address.city_name
    user.address_province = address.province_name or address.region_name
    user.address_region = address.region_name
    user.address_zip = address.zip_code


@addresses_bp.post("")
@require_user
def create_address():
    user = User.query.get(current_user_id())
    if UserAddress.query.filter_by(user_id=user.id).count() >= 10:
        return _error("You can save up to 10 addresses. Delete one first.")
    try:
        values = _read(request.get_json() or {})
    except AddressError as error:
        return _error(str(error))
    address = UserAddress(user_id=user.id)
    _apply(address, values)
    db.session.add(address)
    db.session.flush()
    if request.get_json().get("makeDefault") or UserAddress.query.filter_by(user_id=user.id, is_default=True).count() == 0:
        _make_default(user, address)
    db.session.commit()
    return jsonify({"address": address.to_dict()}), 201


def _mine(address_id):
    return UserAddress.query.filter_by(id=address_id, user_id=current_user_id()).first()


@addresses_bp.put("/<int:address_id>")
@require_user
def update_address(address_id):
    address = _mine(address_id)
    if not address:
        return _error("Address not found", 404)
    try:
        values = _read(request.get_json() or {})
    except AddressError as error:
        return _error(str(error))
    _apply(address, values)
    if address.is_default:
        _make_default(User.query.get(current_user_id()), address)
    db.session.commit()
    return jsonify({"address": address.to_dict()})


@addresses_bp.post("/<int:address_id>/default")
@require_user
def set_default(address_id):
    address = _mine(address_id)
    if not address:
        return _error("Address not found", 404)
    _make_default(User.query.get(current_user_id()), address)
    db.session.commit()
    return jsonify({"address": address.to_dict()})


@addresses_bp.delete("/<int:address_id>")
@require_user
def delete_address(address_id):
    address = _mine(address_id)
    if not address:
        return _error("Address not found", 404)
    was_default = address.is_default
    db.session.delete(address)
    db.session.flush()
    if was_default:
        replacement = UserAddress.query.filter_by(user_id=current_user_id()).order_by(UserAddress.id).first()
        if replacement:
            _make_default(User.query.get(current_user_id()), replacement)
    db.session.commit()
    return jsonify({"message": "Address deleted"})
