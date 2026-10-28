"""
Creates the demo admin and customer accounts with properly hashed
passwords. Run this once after applying database/schema.sql:

    python seed.py
"""

from werkzeug.security import generate_password_hash
from app import create_app
from app.extensions import db
from app.models import Admin, User

app = create_app()

with app.app_context():
    has_head = any(a.is_head for a in Admin.query.all())
    if has_head:
        print("An admin account already exists, so no default admin was created.")
    else:
        db.session.add(Admin(
            name="System Admin",
            email="admin@raincheminternational.com",
            password_hash=generate_password_hash("Admin123!"),
            role="Head Admin",
        ))
        print("Created admin account: admin@raincheminternational.com / Admin123!  (change the email and password right away in Admin > My Account)")

    if not User.query.filter_by(email="rider@example.com").first():
        db.session.add(User(
            name="Ricardo Domingo",
            email="rider@example.com",
            password_hash=generate_password_hash("Rider123!"),
            phone="0917 555 0142",
            verified=True,
            address_line1="45 Del Pilar St.",
            address_city="Quezon City",
            address_province="Metro Manila",
            address_region="NCR",
            address_zip="1100",
        ))
        print("Created demo customer: rider@example.com / Rider123!")

    db.session.commit()
    print("Seeding complete.")
