"""Philippine address rules. Each choice must belong to the one above it: a barangay must be in the chosen city,
a city in the chosen province (or region, for cities that are not in a province), and so on. Nothing here guesses."""
import csv
import os

from app.extensions import db
from app.models import PhLocation

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "psgc_ph.csv")
BATCH = 2000


class AddressError(Exception):
    pass


def load_reference():
    """Loads the PSGC file once. Safe to call again: it does nothing when the table already has rows."""
    if PhLocation.query.first() is not None:
        return 0
    rows = []
    with open(DATA_FILE, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({"code": r["code"], "name": r["name"], "level": r["level"],
                         "parent_code": r["parent_code"] or None, "zip_code": None})
    for i in range(0, len(rows), BATCH):
        db.session.bulk_insert_mappings(PhLocation, rows[i:i + BATCH])
    db.session.commit()
    return len(rows)


def get_place(code):
    return db.session.get(PhLocation, code) if code else None


def children(parent_code=None):
    if not parent_code:
        return PhLocation.query.filter_by(level="Reg").order_by(PhLocation.name).all()
    return PhLocation.query.filter_by(parent_code=parent_code).order_by(PhLocation.level, PhLocation.name).all()


def validate_chain(region_code, province_code, city_code, barangay_code):
    region = get_place(region_code)
    if not region or region.level != "Reg":
        raise AddressError("Choose a valid region")
    province = None
    if province_code:
        province = get_place(province_code)
        if not province or province.level != "Prov" or province.parent_code != region.code:
            raise AddressError("The province does not belong to the chosen region")
    city = get_place(city_code)
    allowed_parent = province.code if province else region.code
    if not city or city.level not in ("City", "Mun") or city.parent_code != allowed_parent:
        raise AddressError("The city or municipality does not belong to the chosen province or region")
    barangay = get_place(barangay_code)
    if not barangay or barangay.level not in ("Bgy", "SubMun") or barangay.parent_code != city.code:
        raise AddressError("The barangay does not belong to the chosen city or municipality")
    return region, province, city, barangay


def postal_code_for(barangay):
    """The official postal code, if one has been loaded. None means none is known yet."""
    return barangay.zip_code if barangay and barangay.zip_code else None
