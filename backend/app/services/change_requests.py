import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from flask import current_app
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import Admin, ApprovalOtp, ChangeRequest, Product
from app.services import product_changes as changes
from app.services.email_service import send_email

KIND_LABELS = {
    "product_create": "Add product",
    "product_update": "Edit product",
    "product_delete": "Delete product",
}
FIELD_LABELS = {
    "name": "Name", "category": "Category", "price": "Price", "stock": "Stock",
    "short_desc": "Short description", "description": "Description",
    "specs": "Specifications", "benefits": "Benefits", "usage_steps": "Usage steps",
}
OTP_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_COOLDOWN_SECONDS = 30


class ApprovalError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def submit(admin, kind, product, payload):
    """Stores a validated change for the Head Admin to review."""
    image = (payload or {}).pop("imagePhoto", None)
    request_row = ChangeRequest(
        kind=kind, status="pending", product_id=product.id if product else None,
        target_name=(product.name if product else payload["values"]["name"]),
        payload=payload, image_photo=image,
        requested_by=admin.id, requester_name=admin.name, requester_role=admin.role,
    )
    db.session.add(request_row)
    db.session.commit()
    _notify_heads(request_row)
    return request_row


def _notify_heads(request_row):
    try:
        heads = [a for a in Admin.query.filter_by(is_active=True).all() if a.is_head]
        for head in heads:
            send_email(
                head.email, f"Approval needed: {KIND_LABELS[request_row.kind]}",
                f"{request_row.requester_name} ({request_row.requester_role}) asked to "
                f"{KIND_LABELS[request_row.kind].lower()}: {request_row.target_name}.\n\n"
                "Open Admin > Approvals to review it. Nothing changes until you approve.",
            )
    except Exception:
        db.session.rollback()


def _show(value):
    if value is None or value == "":
        return "-"
    if isinstance(value, list):
        return "; ".join(str(v) for v in value) or "-"
    text = str(value)
    return text if len(text) <= 300 else text[:300] + "..."


def changes_for(request_row):
    """Readable list of what the request would change, compared with the product as it is now."""
    payload = request_row.payload or {}
    values = payload.get("values", {})
    product = db.session.get(Product, request_row.product_id) if request_row.product_id else None

    if request_row.kind == "product_delete":
        if not product:
            return []
        return [{"field": "Product", "from": f"{product.name} (stock {product.stock}, PHP {product.price})", "to": "Deleted"}]

    rows = []
    for column, new in values.items():
        old = getattr(product, column, None) if product else None
        if request_row.kind == "product_update" and _same(old, new):
            continue
        rows.append({"field": FIELD_LABELS.get(column, column), "from": _show(old) if product else "-", "to": _show(new)})
    if payload.get("ownerSet"):
        new_owner = payload.get("ownerId")
        old_owner = product.owner_admin_id if product else None
        if new_owner != old_owner or (not product and new_owner):
            rows.append({"field": "Assigned to", "from": _owner_name(old_owner) if product else "-", "to": _owner_name(new_owner)})
    if request_row.image_photo:
        rows.append({"field": "Photo", "from": "-", "to": "New photo uploaded"})
    return rows


def _owner_name(admin_id):
    owner = db.session.get(Admin, admin_id) if admin_id else None
    return owner.name if owner else "Head office"


def _same(old, new):
    try:
        if isinstance(new, str) and old is not None and not isinstance(old, str):
            return str(old) == new or float(old) == float(new)
    except (TypeError, ValueError):
        pass
    return old == new


def to_dict(request_row, detail=False):
    data = {
        "id": request_row.id,
        "kind": request_row.kind,
        "kindLabel": KIND_LABELS.get(request_row.kind, request_row.kind),
        "status": request_row.status,
        "productId": request_row.product_id,
        "targetName": request_row.target_name,
        "requestedBy": {"id": request_row.requested_by, "name": request_row.requester_name, "role": request_row.requester_role},
        "createdAt": request_row.created_at.isoformat() if request_row.created_at else None,
        "decidedBy": request_row.decider_name,
        "decidedAt": request_row.decided_at.isoformat() if request_row.decided_at else None,
        "note": request_row.decision_note,
        "changes": changes_for(request_row) if request_row.status == "pending" or detail else [],
        "hasPhoto": bool(request_row.image_photo),
    }
    if detail:
        data["photo"] = request_row.image_photo
    return data


def _hash(salt, code):
    return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()


def _mask(email):
    name, _, domain = email.partition("@")
    return f"{name[:2]}{'*' * max(1, len(name) - 2)}@{domain}"


def _require_pending(request_row):
    if request_row.status != "pending":
        raise ApprovalError(f"This request is already {request_row.status}", 409)


def start_approval(request_row, head, password):
    """Step 1: the Head Admin proves it is them with their password, then a one-time code is emailed."""
    _require_pending(request_row)
    if not check_password_hash(head.password_hash, password or ""):
        raise ApprovalError("Incorrect password", 403)

    recent = (
        ApprovalOtp.query.filter_by(change_request_id=request_row.id, admin_id=head.id)
        .order_by(ApprovalOtp.created_at.desc()).first()
    )
    if recent and recent.created_at > datetime.utcnow() - timedelta(seconds=OTP_COOLDOWN_SECONDS) and not recent.used:
        raise ApprovalError(f"Please wait {OTP_COOLDOWN_SECONDS} seconds before asking for another code", 429)

    ApprovalOtp.query.filter_by(change_request_id=request_row.id, admin_id=head.id, used=False).update({"used": True})
    code = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_hex(8)
    otp = ApprovalOtp(
        change_request_id=request_row.id, admin_id=head.id, salt=salt, code_hash=_hash(salt, code),
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_MINUTES),
    )
    db.session.add(otp)
    db.session.commit()

    sent = send_email(
        head.email, "Your Rainchem approval code",
        f"Your approval code is {code}. It expires in {OTP_MINUTES} minutes.\n\n"
        f"It approves: {KIND_LABELS[request_row.kind]} - {request_row.target_name} "
        f"(requested by {request_row.requester_name}).\n\n"
        "If you did not start this, do not share the code and change your password.",
        user_id=None, sensitive=True,
    )
    if not sent and not current_app.debug:
        otp.used = True
        db.session.commit()
        raise ApprovalError(
            "We could not send the code to your email. Check the email settings on the server (Mailjet), then try again.", 503
        )
    return {"email": _mask(head.email), "expiresInMinutes": OTP_MINUTES}


def confirm_approval(request_row, head, code):
    """Step 2: the emailed code is checked, and only then is the change applied."""
    _require_pending(request_row)
    otp = (
        ApprovalOtp.query.filter_by(change_request_id=request_row.id, admin_id=head.id, used=False)
        .order_by(ApprovalOtp.created_at.desc()).first()
    )
    if otp is None:
        raise ApprovalError("Ask for a new code first", 400)
    if otp.expires_at < datetime.utcnow():
        raise ApprovalError("That code has expired. Ask for a new one.", 400)
    if otp.attempts >= OTP_MAX_ATTEMPTS:
        raise ApprovalError("Too many wrong codes. Ask for a new one.", 429)

    if not hmac.compare_digest(otp.code_hash, _hash(otp.salt, str(code or "").strip())):
        otp.attempts += 1
        db.session.commit()
        left = OTP_MAX_ATTEMPTS - otp.attempts
        raise ApprovalError(
            "Incorrect code. " + (f"{left} tries left." if left else "Ask for a new code."), 400
        )

    try:
        _apply(request_row)
    except changes.ProductChangeError as error:
        db.session.rollback()
        raise ApprovalError(str(error), error.status)

    otp.used = True
    request_row.status = "approved"
    request_row.decided_by, request_row.decider_name = head.id, head.name
    request_row.decided_at = datetime.utcnow()
    db.session.commit()
    _tell_requester(request_row, "approved")
    return request_row


def _apply(request_row):
    payload = request_row.payload or {}
    payload = dict(payload, imagePhoto=request_row.image_photo)
    requester = db.session.get(Admin, request_row.requested_by) if request_row.requested_by else None

    if request_row.kind == "product_create":
        if requester is not None and not requester.is_active:
            raise changes.ProductChangeError("The account that asked for this is disabled", 409)
        product = changes.apply_create(payload)
        db.session.flush()
        request_row.product_id = product.id
        return

    product = db.session.get(Product, request_row.product_id) if request_row.product_id else None
    if product is None:
        raise changes.ProductChangeError("This product no longer exists, so the request cannot be applied. Reject it.", 409)
    if requester is not None and not changes.can_manage(product, requester):
        raise changes.ProductChangeError("The product no longer belongs to the person who asked. Reject this request.", 409)

    if request_row.kind == "product_update":
        changes.apply_update(product, payload)
    elif request_row.kind == "product_delete":
        changes.apply_delete(product)


def reject(request_row, head, note):
    _require_pending(request_row)
    request_row.status = "rejected"
    request_row.decided_by, request_row.decider_name = head.id, head.name
    request_row.decided_at = datetime.utcnow()
    request_row.decision_note = (note or "").strip()[:255] or None
    ApprovalOtp.query.filter_by(change_request_id=request_row.id, used=False).update({"used": True})
    db.session.commit()
    _tell_requester(request_row, "rejected")
    return request_row


def cancel(request_row, admin):
    _require_pending(request_row)
    if request_row.requested_by != admin.id:
        raise ApprovalError("You can only cancel your own requests", 403)
    request_row.status = "cancelled"
    request_row.decided_at = datetime.utcnow()
    ApprovalOtp.query.filter_by(change_request_id=request_row.id, used=False).update({"used": True})
    db.session.commit()
    return request_row


def _tell_requester(request_row, outcome):
    requester = db.session.get(Admin, request_row.requested_by) if request_row.requested_by else None
    if not requester:
        return
    try:
        note = f"\n\nNote from the Head Admin: {request_row.decision_note}" if request_row.decision_note else ""
        send_email(
            requester.email, f"Your request was {outcome}: {request_row.target_name}",
            f"Your request to {KIND_LABELS[request_row.kind].lower()} ({request_row.target_name}) was {outcome}.{note}",
        )
    except Exception:
        db.session.rollback()
