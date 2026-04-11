"""
Shared route decorators.
Usage:
    from utils.decorators import admin_required, current_user_is_admin

    @admin_bp.route("/something")
    @jwt_required()
    @admin_required
    def something():
        ...
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity


def current_user_is_admin() -> bool:
    """True if the JWT identity maps to a user row with role admin (DB source of truth)."""
    from models.user import User

    uid = get_jwt_identity()
    if uid is None:
        return False
    try:
        user = User.query.get(int(uid))
    except (TypeError, ValueError):
        return False
    return bool(user and (user.role or "").strip().lower() == "admin")


def admin_required(fn):
    """Decorator: reject callers whose database role is not admin (403)."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user_is_admin():
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)

    return wrapper
