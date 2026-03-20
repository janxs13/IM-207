import secrets
from flask import Blueprint, request, jsonify
from services.auth_service import register_user, login_user
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from extensions import db
from werkzeug.security import generate_password_hash

auth_bp = Blueprint("auth", __name__)

# ── Register / Login ─────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or request.form.to_dict()
    response, status = register_user(data)
    return jsonify(response), status

@auth_bp.route("/login", methods=["POST"])
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
    if data.get("first_name"): user.first_name = data["first_name"].strip()
    if data.get("last_name"):  user.last_name  = data["last_name"].strip()
    if data.get("phone"):      user.phone      = data["phone"].strip()
    if data.get("password"):
        if len(data["password"]) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        user.password = generate_password_hash(data["password"])

    db.session.commit()
    return jsonify({"message": "Profile updated successfully", "user": _user_dict(user)}), 200

# ── Forgot / Reset password ──────────────────────────────────────
@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data  = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        # Generic response — don't leak whether email exists
        return jsonify({"message": "If that email is registered, a reset token has been generated."}), 200

    token = secrets.token_hex(3).upper()   # 6-char e.g. "A3F9C2"
    try:
        user.reset_token = token
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error. Please run: python migrate_db.py"}), 500

    return jsonify({
        "message":     "Reset token generated.",
        "reset_token": token,    # shown on screen; swap for email in production
        "email":       email
    }), 200

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data         = request.get_json() or {}
    email        = (data.get("email") or "").strip().lower()
    token        = (data.get("token") or "").strip().upper()
    new_password = data.get("new_password") or ""

    if not all([email, token, new_password]):
        return jsonify({"error": "email, token, and new_password are required"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Invalid email or token"}), 400

    try:
        stored = getattr(user, "reset_token", None)
    except Exception:
        stored = None

    if not stored or stored != token:
        return jsonify({"error": "Invalid or expired reset token"}), 400

    user.password    = generate_password_hash(new_password)
    user.reset_token = None
    db.session.commit()
    return jsonify({"message": "Password reset successfully. You can now log in."}), 200

def _user_dict(user):
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return {
        "id":         user.id,
        "first_name": user.first_name or "",
        "last_name":  user.last_name or "",
        "username":   full_name or user.email,
        "email":      user.email,
        "phone":      user.phone or "",
        "role":       user.role
    }
