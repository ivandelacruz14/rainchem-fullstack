import re

from flask import Blueprint, request, jsonify

from app.extensions import db
from app.models.setting import set_setting
from app.services import paymongo, payment_flow
from app.utils.auth_decorators import require_admin

admin_settings_bp = Blueprint("admin_settings", __name__, url_prefix="/api/admin/settings")

MAX_QR_CHARS = 2_000_000


def _payload():
    return {
        "gcash": payment_flow.gcash_details(),
        "gcashConfigured": payment_flow.gcash_configured(),
        "cardAvailable": payment_flow.card_available(),
        "cardDemoMode": paymongo.demo_mode(),
    }


@admin_settings_bp.get("/payment")
@require_admin
def get_payment_settings():
    return jsonify(_payload())


@admin_settings_bp.put("/payment")
@require_admin
def update_payment_settings():
    data = request.get_json() or {}
    gcash = data.get("gcash") or {}

    number = re.sub(r"[^\d+ ]", "", str(gcash.get("number") or "")).strip()[:20]
    name = str(gcash.get("accountName") or "").strip()[:100]
    link = str(gcash.get("link") or "").strip()[:500]
    note = str(gcash.get("note") or "").strip()[:300]
    qr = gcash.get("qr")

    if link and not re.match(r"^https?://", link, re.I):
        return jsonify({"error": "The GCash link must start with http:// or https://"}), 400
    if qr:
        if not isinstance(qr, str) or not qr.startswith("data:image/") or len(qr) > MAX_QR_CHARS:
            return jsonify({"error": "The QR code must be an image under 1.5 MB"}), 400

    set_setting("gcash_number", number)
    set_setting("gcash_name", name)
    set_setting("gcash_link", link)
    set_setting("gcash_note", note)
    if qr is not None:          # None = leave as is, "" = remove, data URL = replace
        set_setting("gcash_qr", qr)
    db.session.commit()
    return jsonify(_payload())
