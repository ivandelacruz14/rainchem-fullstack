from datetime import datetime

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db
from app.utils.auth_decorators import require_permission

admin_diagnostics_bp = Blueprint("admin_diagnostics", __name__, url_prefix="/api/admin/diagnostics")


@admin_diagnostics_bp.get("/health")
@require_permission("diagnostics")
def health():
    """Server and database health. Returns no customer, payment, or security data."""
    try:
        db.session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # noqa: BLE001
        database = "unreachable"
    return jsonify({"status": "ok" if database == "ok" else "degraded", "database": database,
                    "serverTime": datetime.utcnow().isoformat()})
