import re
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.auth_service import register_user, login_user
from models.user import User
from extensions import db, limiter
from werkzeug.security import generate_password_hash

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# How long a password-reset token stays valid
RESET_TOKEN_TTL_MINUTES = 30


# ── Register ─────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
def register():
    data = request.get_json() or request.form.to_dict()
    email = (data.get("email") or "").strip()
    if email and not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email format"}), 400
    response, status = register_user(data)
    return jsonify(response), status


# ── Login ─────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    data = request.get_json() or request.form.to_dict()
    response, status = login_user(data)
    return jsonify(response), status


# ── Current user ─────────────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": _user_dict(user)}), 200


# ── Profile edit ─────────────────────────────────────────────────
@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}

    first_name = (data.get("first_name") or "").strip()
    last_name  = (data.get("last_name")  or "").strip()
    phone      = (data.get("phone")      or "").strip()

    if first_name:
        if len(first_name) > 100:
            return jsonify({"error": "First name too long (max 100 characters)"}), 400
        user.first_name = first_name
    if last_name:
        if len(last_name) > 100:
            return jsonify({"error": "Last name too long (max 100 characters)"}), 400
        user.last_name = last_name
    if phone:
        if len(phone) > 20:
            return jsonify({"error": "Phone number too long"}), 400
        user.phone = phone

    if data.get("password"):
        if len(data["password"]) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        if len(data["password"]) > 128:
            return jsonify({"error": "Password too long (max 128 characters)"}), 400
        user.password = generate_password_hash(data["password"])

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update profile. Please try again."}), 500

    return jsonify({"message": "Profile updated successfully", "user": _user_dict(user)}), 200


# ── Forgot password ───────────────────────────────────────────────
@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per hour")
def forgot_password():
    data  = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"error": "Email is required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email format"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        # Generic response — don't reveal whether the email is registered
        return jsonify({
            "message": "If that email is registered, a reset token has been sent."
        }), 200

    # Generate a 6-char uppercase token with a 30-minute TTL
    token   = secrets.token_hex(3).upper()
    expires = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)

    try:
        user.reset_token         = token
        user.reset_token_expires = expires
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error. Please try again."}), 500

    # Send the token via email (prints to console in dev if MAIL_USERNAME not set)
    from utils.mailer import send_password_reset_email
    email_sent = send_password_reset_email(email, token, RESET_TOKEN_TTL_MINUTES)

    response = {
        "message": (
            "A reset token has been sent to your email address. "
            f"It expires in {RESET_TOKEN_TTL_MINUTES} minutes."
        )
    }

    # Never return the token in JSON when real mail is configured (avoids leaking
    # the token if SMTP fails but credentials are set).
    if not _mail_configured():
        response["reset_token"] = token
        response["note"] = (
            "Email not configured — token shown here for development. "
            "Set MAIL_USERNAME and MAIL_PASSWORD in .env to send real emails."
        )
    elif not email_sent:
        response["message"] = (
            "We could not send the reset email. Please try again in a few minutes."
        )

    return jsonify(response), 200


# ── Reset password ────────────────────────────────────────────────
@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("10 per hour")
def reset_password():
    data         = request.get_json() or {}
    email        = (data.get("email")        or "").strip().lower()
    token        = (data.get("token")        or "").strip().upper()
    new_password = (data.get("new_password") or "")

    if not all([email, token, new_password]):
        return jsonify({"error": "email, token, and new_password are required"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if len(new_password) > 128:
        return jsonify({"error": "Password too long"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.is_reset_token_valid(token):
        return jsonify({"error": "Invalid or expired reset token"}), 400

    try:
        user.password            = generate_password_hash(new_password)
        user.reset_token         = None
        user.reset_token_expires = None
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to reset password. Please try again."}), 500

    return jsonify({"message": "Password reset successfully. You can now log in."}), 200


# ── Helper ────────────────────────────────────────────────────────
def _mail_configured():
    """True if MAIL_USERNAME is set in the environment (real email sending)."""
    from flask import current_app
    return bool(current_app.config.get("MAIL_USERNAME"))


def _user_dict(user):
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return {
        "id":         user.id,
        "first_name": user.first_name or "",
        "last_name":  user.last_name  or "",
        "username":   full_name or user.email,
        "email":      user.email,
        "phone":      user.phone or "",
        "role":       user.role
    }
