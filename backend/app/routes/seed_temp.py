from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Admin

seed_temp_bp = Blueprint("seed_temp", __name__, url_prefix="/api/seed-temp")

# Panandalian lang ito. Tanggalin agad pagkatapos magamit.
SEED_SECRET = "ivan-rainchem-2026"  # palitan mo ito ng sarili mong random na text


@seed_temp_bp.post("/create-admin")
def create_admin_once():
    secret = request.args.get("secret", "")
    if secret != SEED_SECRET:
        return jsonify({"error": "Not allowed"}), 403

    if Admin.query.filter_by(email="admin@raincheminternational.com").first():
        return jsonify({"message": "Admin already exists"}), 200

    admin = Admin(
        name="System Admin",
        email="admin@raincheminternational.com",
        password_hash=generate_password_hash("Admin123!"),
        role="Super Admin",
    )
    db.session.add(admin)
    db.session.commit()
    return jsonify({"message": "Admin created"}), 201