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
    ("admins", "is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
    ("products", "owner_admin_id", "INT NULL"),
]

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

    backfill_single_product_reviews(db, logger)

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


def backfill_single_product_reviews(db, logger):
    """Orders reviewed before per-product reviews existed carried one rating for the whole
    order. When such an order had exactly one product, that rating is unambiguous, so it is
    copied to the product reviews table. Orders with several products are left alone because
    the rating cannot be attributed to a single product. Safe to run repeatedly."""
    from app.models import Order, ProductReview

    try:
        legacy = Order.query.filter(Order.review_rating.isnot(None), Order.user_id.isnot(None)).all()
        added = 0
        for order in legacy:
            product_ids = {i.product_id for i in order.items}
            if len(order.items) != 1 or None in product_ids:
                continue
            product_id = next(iter(product_ids))
            exists = ProductReview.query.filter_by(order_id=order.id, product_id=product_id).first()
            if exists:
                continue
            db.session.add(ProductReview(
                product_id=product_id, order_id=order.id, user_id=order.user_id,
                rating=order.review_rating, comment=order.review_comment,
                created_at=order.reviewed_at or order.created_at,
            ))
            added += 1
        db.session.commit()
        if added:
            logger.info("Copied %s earlier order reviews to product reviews", added)
    except Exception as error:
        db.session.rollback()
        logger.warning("Could not copy earlier reviews: %s", error)
