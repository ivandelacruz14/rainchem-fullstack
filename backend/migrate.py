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