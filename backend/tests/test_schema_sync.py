from datetime import datetime

from sqlalchemy import inspect, text

from app.extensions import db
from app.services.schema_updates import add_missing_model_columns


def test_old_services_table_missing_a_column_is_repaired(app):
    """Reproduces the Render error: `services` existed without `updated_at`."""
    db.drop_all()
    db.session.execute(text(
        "CREATE TABLE services (id INTEGER PRIMARY KEY, name VARCHAR(150) NOT NULL, category VARCHAR(80), "
        "description TEXT NOT NULL, requirements TEXT, is_active BOOLEAN NOT NULL, owner_admin_id INTEGER, created_at DATETIME)"
    ))
    db.session.commit()
    db.create_all()  # leaves the old table alone, like on the deployed database

    from app.models import Service
    db.session.add(Service(name="Oil Change", description="d"))
    try:
        db.session.commit()
        failed = False
    except Exception:
        db.session.rollback()
        failed = True
    assert failed, "the old table should reproduce the missing-column error"

    add_missing_model_columns(db, app.logger)

    assert "updated_at" in {c["name"] for c in inspect(db.engine).get_columns("services")}
    db.session.add(Service(name="Oil Change", description="d", requirements="r"))
    db.session.commit()
    assert Service.query.one().name == "Oil Change"


def test_running_it_twice_changes_nothing(app):
    before = {t: {c["name"] for c in inspect(db.engine).get_columns(t)} for t in inspect(db.engine).get_table_names()}
    add_missing_model_columns(db, app.logger)
    add_missing_model_columns(db, app.logger)
    after = {t: {c["name"] for c in inspect(db.engine).get_columns(t)} for t in inspect(db.engine).get_table_names()}
    assert before == after


def test_missing_boolean_column_gets_a_safe_default(app):
    db.drop_all()
    db.session.execute(text("CREATE TABLE services (id INTEGER PRIMARY KEY, name VARCHAR(150) NOT NULL, description TEXT NOT NULL)"))
    db.session.execute(text("INSERT INTO services (name, description) VALUES ('Old row', 'kept')"))
    db.session.commit()
    add_missing_model_columns(db, app.logger)
    row = db.session.execute(text("SELECT name, is_active FROM services")).one()
    assert row[0] == "Old row" and row[1] == 1  # existing data kept, and the service stays switched on


def test_old_distributor_accounts_are_switched_off_and_their_items_released(app):
    from app.models import Admin
    from app.services.schema_updates import retire_distributors

    db.drop_all()
    db.create_all()
    db.session.add_all([
        Admin(name="Head", email="h@example.com", role="Head Admin", password_hash="x"),
        Admin(name="Old", email="d@example.com", role="Distributor", permissions=["products"], password_hash="x"),
    ])
    # A deployed database still has the old owner column on services.
    db.session.execute(text("DROP TABLE services"))
    db.session.execute(text(
        "CREATE TABLE services (id INTEGER PRIMARY KEY, name VARCHAR(150) NOT NULL, description TEXT NOT NULL, owner_admin_id INTEGER)"
    ))
    db.session.execute(text("INSERT INTO services (name, description, owner_admin_id) VALUES ('Oil change', 'd', 2)"))
    db.session.commit()

    retire_distributors(db, app.logger)
    retire_distributors(db, app.logger)   # running it again changes nothing

    assert Admin.query.filter_by(email="d@example.com").one().is_active is False   # switched off, not deleted
    assert Admin.query.filter_by(email="h@example.com").one().is_active is True
    assert db.session.execute(text("SELECT owner_admin_id FROM services")).scalar() is None
