from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

STATEMENTS = [
    "ALTER TABLE users ADD COLUMN age INT NULL",
    "ALTER TABLE users ADD COLUMN gender VARCHAR(20) NULL",
    "ALTER TABLE users ADD COLUMN avatar_photo LONGTEXT NULL",
    "ALTER TABLE products MODIFY COLUMN image_photo LONGTEXT NULL",
    "ALTER TABLE email_verifications ADD COLUMN pending_email VARCHAR(180) NULL",
    "ALTER TABLE chat_logs ADD COLUMN source VARCHAR(20) NULL",
    "ALTER TABLE chat_logs ADD COLUMN rating TINYINT NULL",
    "ALTER TABLE chat_logs ADD COLUMN feedback VARCHAR(500) NULL",
    "ALTER TABLE chat_logs ADD COLUMN rated_at DATETIME NULL",
    "ALTER TABLE orders ADD COLUMN payment_status VARCHAR(20) NOT NULL DEFAULT 'unpaid'",
    "ALTER TABLE orders ADD COLUMN payment_reference VARCHAR(120) NULL",
    "ALTER TABLE orders ADD COLUMN paid_at DATETIME NULL",
    "ALTER TABLE orders ADD COLUMN return_status VARCHAR(20) NOT NULL DEFAULT 'none'",
    "ALTER TABLE orders ADD COLUMN return_reason VARCHAR(500) NULL",
    "ALTER TABLE orders ADD COLUMN return_requested_at DATETIME NULL",
    "ALTER TABLE orders ADD COLUMN return_note VARCHAR(500) NULL",
    "ALTER TABLE orders ADD COLUMN review_rating TINYINT NULL",
    "ALTER TABLE orders ADD COLUMN review_comment VARCHAR(500) NULL",
    "ALTER TABLE orders ADD COLUMN reviewed_at DATETIME NULL",
    "ALTER TABLE admins ADD COLUMN permissions JSON NULL",
    "ALTER TABLE admins ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1",
    "ALTER TABLE products ADD COLUMN owner_admin_id INT NULL",
    "UPDATE orders SET payment_status = 'paid', paid_at = created_at WHERE status = 'delivered' AND payment_method = 'Cash on Delivery'",
]

with app.app_context():
    for stmt in STATEMENTS:
        try:
            db.session.execute(text(stmt))
            db.session.commit()
            print(f"OK: {stmt}")
        except Exception as e:
            db.session.rollback()
            print(f"SKIPPED (likely already applied): {stmt}\n  -> {e}")

print("Migration complete.")