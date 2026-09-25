from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.models import User, EmailVerification, PasswordReset
from app.services.auth_utils import (
    validate_password, is_valid_email, is_valid_phone,
    generate_verification_code, generate_reset_token,
)
from app.services.email_service import send_email
from app.services.google_auth import verify_google_token
from app.utils.auth_decorators import create_user_token, require_user, current_user_id

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""

    errors = []
    if not name:
        errors.append("Please enter your full name")
    if not is_valid_email(email):
        errors.append("Please enter a valid email address")

    existing_user = User.query.filter_by(email=email).first()
    if existing_user and existing_user.verified:
        errors.append("An account with this email already exists")
    if not is_valid_phone(phone):
        errors.append("Please enter a valid contact number")

    password_errors = validate_password(password)
    if password_errors:
        errors.append("Password requirements not met: " + ", ".join(password_errors))

    if errors:
        return jsonify({"errors": errors}), 400

    if existing_user and not existing_user.verified:
        user = existing_user
        user.name = name
        user.phone = phone
        user.password_hash = generate_password_hash(password)
        db.session.commit()
    else:
        user = User(
            name=name, email=email, phone=phone,
            password_hash=generate_password_hash(password), verified=False,
        )
        db.session.add(user)
        db.session.commit()

    code = generate_verification_code()
    verification = EmailVerification(
        user_id=user.id, code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    db.session.add(verification)
    db.session.commit()

    send_email(
        email, "Verify your Rainchem account",
        f"Hi {name},\n\nYour verification code is {code}. It expires in 10 minutes.",
        user_id=user.id,
    )

    return jsonify({"message": "Account created. Check your email for a verification code.", "email": email})


@auth_bp.post("/verify-email")
def verify_email():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Account not found"}), 404

    verification = (
        EmailVerification.query.filter_by(user_id=user.id, code=code)
        .order_by(EmailVerification.id.desc())
        .first()
    )
    if not verification or verification.expires_at < datetime.utcnow():
        return jsonify({"error": "Incorrect or expired code"}), 400

    user.verified = True
    db.session.delete(verification)
    db.session.commit()

    token = create_user_token(user)
    return jsonify({"token": token, "user": user.to_dict()})


@auth_bp.post("/resend-code")
def resend_code():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Account not found"}), 404

    code = generate_verification_code()
    db.session.add(EmailVerification(
        user_id=user.id, code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    ))
    db.session.commit()

    send_email(email, "Your new Rainchem verification code",
               f"Your verification code is {code}. It expires in 10 minutes.", user_id=user.id)
    return jsonify({"message": "A new code has been sent"})


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Incorrect email or password"}), 401

    if not user.verified:
        return jsonify({"error": "Account not verified", "needsVerification": True, "email": email}), 403

    token = create_user_token(user)
    return jsonify({"token": token, "user": user.to_dict()})


@auth_bp.post("/google")
def google_login():
    data = request.get_json() or {}
    id_token_value = data.get("token")
    if not id_token_value:
        return jsonify({"error": "Missing Google token"}), 400

    try:
        payload = verify_google_token(id_token_value)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        return jsonify({"error": "Could not verify Google sign-in"}), 400

    user = User.query.filter_by(google_id=payload["google_id"]).first()
    if not user:
        user = User.query.filter_by(email=payload["email"]).first()

    if user:
        user.google_id = payload["google_id"]
        if payload.get("email_verified"):
            user.verified = True
    else:
        user = User(
            name=payload["name"], email=payload["email"],
            google_id=payload["google_id"], verified=payload.get("email_verified", True),
        )
        db.session.add(user)

    db.session.commit()
    token = create_user_token(user)
    return jsonify({"token": token, "user": user.to_dict()})


@auth_bp.post("/forgot-password")
def forgot_password():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    user = User.query.filter_by(email=email).first()

    generic_response = jsonify({
        "message": "If an account with that email exists, a reset link has been sent."
    })

    if not user:
        return generic_response

    token = generate_reset_token()
    db.session.add(PasswordReset(
        user_id=user.id, token=token,
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    ))
    db.session.commit()

    reset_link = f"{current_app.config['FRONTEND_URL']}/reset-password?token={token}"
    send_email(
        email, "Reset your Rainchem password",
        f"Hi {user.name},\n\nUse the link below to reset your password. "
        f"It expires in 30 minutes.\n\n{reset_link}\n\n"
        "If you did not request this, you can ignore this email.",
        user_id=user.id,
    )
    return generic_response


@auth_bp.post("/reset-password")
def reset_password():
    data = request.get_json() or {}
    token = data.get("token") or ""
    new_password = data.get("password") or ""

    reset_request = PasswordReset.query.filter_by(token=token, used=False).first()
    if not reset_request or reset_request.expires_at < datetime.utcnow():
        return jsonify({"error": "This reset link is invalid or has expired"}), 400

    password_errors = validate_password(new_password)
    if password_errors:
        return jsonify({"errors": password_errors}), 400

    user = User.query.get(reset_request.user_id)
    user.password_hash = generate_password_hash(new_password)
    reset_request.used = True
    db.session.commit()

    send_email(user.email, "Your Rainchem password was changed",
               "Your password was just changed. If this wasn't you, contact support immediately.",
               user_id=user.id)
    return jsonify({"message": "Password updated. You can now log in."})


@auth_bp.get("/me")
@require_user
def me():
    user = User.query.get(current_user_id())
    return jsonify({"user": user.to_dict()})


@auth_bp.put("/me/address")
@require_user
def update_address():
    user = User.query.get(current_user_id())
    data = request.get_json() or {}
    user.address_line1 = data.get("line1", user.address_line1)
    user.address_city = data.get("city", user.address_city)
    user.address_province = data.get("province", user.address_province)
    user.address_region = data.get("region", user.address_region)
    user.address_zip = data.get("zip", user.address_zip)
    db.session.commit()
    return jsonify({"user": user.to_dict()})


@auth_bp.put("/me/profile")
@require_user
def update_profile():
    user = User.query.get(current_user_id())
    data = request.get_json() or {}

    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    age = data.get("age")
    gender = (data.get("gender") or "").strip()

    if not name:
        return jsonify({"error": "Name cannot be empty"}), 400
    if not is_valid_phone(phone):
        return jsonify({"error": "Please enter a valid contact number"}), 400

    user.name = name
    user.phone = phone
    user.age = int(age) if age not in (None, "") else None
    user.gender = gender or None
    db.session.commit()
    return jsonify({"user": user.to_dict()})


@auth_bp.post("/me/email/request-change")
@require_user
def request_email_change():
    user = User.query.get(current_user_id())
    data = request.get_json() or {}
    new_email = (data.get("newEmail") or "").strip().lower()

    if not is_valid_email(new_email):
        return jsonify({"error": "Please enter a valid email address"}), 400
    if User.query.filter_by(email=new_email).first():
        return jsonify({"error": "That email is already in use"}), 400

    code = generate_verification_code()
    db.session.add(EmailVerification(
        user_id=user.id, code=code, pending_email=new_email,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    ))
    db.session.commit()

    send_email(new_email, "Confirm your new Rainchem email",
               f"Your confirmation code is {code}. It expires in 10 minutes.",
               user_id=user.id)
    return jsonify({"message": "A confirmation code was sent to your new email address"})


@auth_bp.post("/me/email/confirm-change")
@require_user
def confirm_email_change():
    user = User.query.get(current_user_id())
    data = request.get_json() or {}
    code = (data.get("code") or "").strip()

    verification = (
        EmailVerification.query.filter_by(user_id=user.id, code=code)
        .filter(EmailVerification.pending_email.isnot(None))
        .order_by(EmailVerification.id.desc())
        .first()
    )
    if not verification or verification.expires_at < datetime.utcnow():
        return jsonify({"error": "Incorrect or expired code"}), 400

    user.email = verification.pending_email
    db.session.delete(verification)
    db.session.commit()
    return jsonify({"user": user.to_dict(), "message": "Email address updated"})


@auth_bp.put("/me/avatar")
@require_user
def update_avatar():
    user = User.query.get(current_user_id())
    data = request.get_json() or {}
    photo = data.get("avatarPhoto")
    if not photo:
        return jsonify({"error": "No image provided"}), 400
    user.avatar_photo = photo
    db.session.commit()
    return jsonify({"user": user.to_dict()})


@auth_bp.put("/me/password")
@require_user
def change_password():
    user = User.query.get(current_user_id())
    data = request.get_json() or {}
    current_password = data.get("currentPassword") or ""
    new_password = data.get("newPassword") or ""

    if not check_password_hash(user.password_hash, current_password):
        return jsonify({"error": "Current password is incorrect"}), 400

    password_errors = validate_password(new_password)
    if password_errors:
        return jsonify({"error": "Password requirements not met: " + ", ".join(password_errors)}), 400

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({"message": "Password updated"})