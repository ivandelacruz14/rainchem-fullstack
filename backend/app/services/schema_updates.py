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
    ("admins", "permissions", "JSON NULL"),
    ("admins", "is_active", "BOOLEAN NOT NULL DEFAULT 1"),
    ("products", "owner_admin_id", "INT NULL"),
]

# Copies reviews that customers already left on whole orders into per-product
# reviews. Only real records are copied, and rows that already exist are skipped.
BACKFILL_PRODUCT_REVIEWS = """
INSERT INTO product_reviews (product_id, order_id, user_id, rating, comment, created_at)
SELECT oi.product_id, o.id, o.user_id, o.review_rating, o.review_comment,
       COALESCE(o.reviewed_at, o.created_at)
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
WHERE o.review_rating IS NOT NULL
  AND o.user_id IS NOT NULL
  AND oi.product_id IS NOT NULL
  AND o.status = 'delivered'
  AND NOT EXISTS (
      SELECT 1 FROM product_reviews pr
      WHERE pr.order_id = o.id AND pr.product_id = oi.product_id
  )
"""

# Photos are stored as base64 text, which does not fit in a plain TEXT column.
LONGTEXT_COLUMNS = [
    ("products", "image_photo"),
    ("users", "avatar_photo"),
]


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

    if "product_reviews" in set(inspect(db.engine).get_table_names()):
        try:
            db.session.execute(text(BACKFILL_PRODUCT_REVIEWS))
            db.session.commit()
        except Exception as error:
            db.session.rollback()
            logger.warning("Could not backfill product reviews: %s", error)

    if db.engine.dialect.name != "mysql":
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
