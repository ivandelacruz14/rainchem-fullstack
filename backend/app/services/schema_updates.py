from sqlalchemy import inspect, text

COLUMNS = [
    ("users", "age", "INT NULL"),
    ("users", "gender", "VARCHAR(20) NULL"),
    ("users", "avatar_photo", "LONGTEXT NULL"),
    ("email_verifications", "pending_email", "VARCHAR(180) NULL"),
    ("chat_logs", "source", "VARCHAR(20) NULL"),
    ("chat_logs", "rating", "TINYINT NULL"),
    ("chat_logs", "feedback", "VARCHAR(500) NULL"),
    ("chat_logs", "rated_at", "DATETIME NULL"),
    ("orders", "payment_status", "VARCHAR(20) NOT NULL DEFAULT 'unpaid'"),
    ("orders", "payment_reference", "VARCHAR(120) NULL"),
    ("orders", "payment_proof", "LONGTEXT NULL"),
    ("orders", "payment_submitted_at", "DATETIME NULL"),
    ("orders", "paid_at", "DATETIME NULL"),
    ("orders", "return_status", "VARCHAR(20) NOT NULL DEFAULT 'none'"),
    ("orders", "return_reason", "VARCHAR(500) NULL"),
    ("orders", "return_requested_at", "DATETIME NULL"),
    ("orders", "return_note", "VARCHAR(500) NULL"),
    ("orders", "review_rating", "TINYINT NULL"),
    ("orders", "review_comment", "VARCHAR(500) NULL"),
    ("orders", "reviewed_at", "DATETIME NULL"),
]

# Photos are stored as base64 text, which does not fit in a plain TEXT column.
LONGTEXT_COLUMNS = [
    ("products", "image_photo"),
    ("users", "avatar_photo"),
]


DEFAULT_SERVICES = [
    {
        "name": "Oil Change Service (Labor + Disposal)", "category": "Services", "price": 150, "stock": 999,
        "rating": 4.9, "reviews": 410, "image_glyph": "service-oil",
        "short_desc": "Professional oil change service at our partner service bays.",
        "description": "Book a professional oil change at any Rainchem partner shop. Price covers labor and proper used-oil disposal.",
        "specs": ["Duration: ~20-30 mins", "Includes labor and eco disposal"],
        "benefits": ["Certified technicians at every partner bay"],
        "usage_steps": ["Bring your order confirmation and plate number"],
    },
    {
        "name": "Radiator Flush & RadCool Service", "category": "Services", "price": 250, "stock": 999,
        "rating": 4.8, "reviews": 152, "image_glyph": "service-coolant",
        "short_desc": "Full radiator flush and RadCool refill service.",
        "description": "We drain your old coolant, flush the system, and refill with RAIMOL RadCool to manufacturer-recommended levels.",
        "specs": ["Duration: ~30-45 mins", "Includes flush and 1L RadCool"],
        "benefits": ["Removes old, degraded coolant and built-up scale"],
        "usage_steps": ["Best done every 12 months or 10,000 km"],
    },
]


def seed_default_services(db, logger):
    """The checkout asks "add a service?" using products in the Services
    category. If the database has none (for example it was created without the
    sample catalog) add the two default services, exactly once, so the prompt
    has something to show. An admin can edit or delete them afterwards."""
    from app.models import Product
    from app.models.setting import get_setting, set_setting

    if get_setting("services_seeded", ""):
        return
    try:
        if Product.query.filter_by(category="Services").count() == 0:
            for item in DEFAULT_SERVICES:
                db.session.add(Product(**item))
            logger.info("Added default services to the catalog")
        set_setting("services_seeded", "1")
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        logger.warning("Could not seed default services: %s", error)


def ensure_schema(db, logger):
    """Adds any missing tables/columns so a deployed database never falls behind the code."""
    try:
        db.create_all()  # only creates tables that do not exist yet (e.g. settings)
    except Exception as error:
        db.session.rollback()
        logger.warning("create_all failed: %s", error)

    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    for table, column, ddl in COLUMNS:
        if table not in tables:
            continue
        existing = {c["name"] for c in inspect(db.engine).get_columns(table)}
        if column in existing:
            continue
        try:
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
            if table == "orders" and column == "payment_status":
                db.session.execute(text(
                    "UPDATE orders SET payment_status = 'paid', paid_at = created_at "
                    "WHERE status = 'delivered' AND payment_method = 'Cash on Delivery'"
                ))
            db.session.commit()
            logger.info("Added column %s.%s", table, column)
        except Exception as error:
            db.session.rollback()
            logger.warning("Could not add %s.%s (maybe another worker did): %s", table, column, error)

    if db.engine.dialect.name != "mysql":
        seed_default_services(db, logger)
        return

    for table, column in LONGTEXT_COLUMNS:
        if table not in tables:
            continue
        info = {c["name"]: c for c in inspect(db.engine).get_columns(table)}
        if column not in info:
            continue
        if str(info[column]["type"]).upper().startswith("LONGTEXT"):
            continue
        try:
            db.session.execute(text(f"ALTER TABLE {table} MODIFY COLUMN {column} LONGTEXT NULL"))
            db.session.commit()
            logger.info("Widened %s.%s to LONGTEXT", table, column)
        except Exception as error:
            db.session.rollback()
            logger.warning("Could not widen %s.%s: %s", table, column, error)

    seed_default_services(db, logger)
