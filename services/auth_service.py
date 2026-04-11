import re
from models.user import User
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def register_user(data):
    try:
        first_name = (data.get("first_name") or "").strip()
        last_name  = (data.get("last_name")  or "").strip()
        email      = (data.get("email")      or "").strip().lower()
        phone      = (data.get("phone")      or "").strip()
        password   = data.get("password")    or ""

        if not all([first_name, last_name, email, phone, password]):
            return {"error": "All fields are required"}, 400
        if not EMAIL_RE.match(email):
            return {"error": "Invalid email format"}, 400
        if len(password) < 6:
            return {"error": "Password must be at least 6 characters"}, 400
        if len(password) > 128:
            return {"error": "Password too long"}, 400
        if len(first_name) > 100 or len(last_name) > 100:
            return {"error": "Name too long (max 100 characters each)"}, 400
        if User.query.filter_by(email=email).first():
            return {"error": "Email is already registered"}, 400

        new_user = User(
            first_name = first_name,
            last_name  = last_name,
            email      = email,
            phone      = phone,
            password   = generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        return {"message": "Account created successfully! You can now log in."}, 201

    except Exception as e:
        db.session.rollback()
        return {"error": "Registration failed. Please try again."}, 500


def login_user(data):
    try:
        email    = (data.get("email")    or "").strip().lower()
        password = (data.get("password") or "")

        if not email or not password:
            return {"error": "Email and password are required"}, 400

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            # Generic message — don't reveal which field is wrong
            return {"error": "Invalid email or password"}, 401

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role, "email": user.email}
        )
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

        return {
            "message":      "Login successful",
            "access_token": access_token,
            "user": {
                "id":         user.id,
                "first_name": user.first_name or "",
                "last_name":  user.last_name  or "",
                "username":   full_name or user.email,
                "email":      user.email,
                "phone":      user.phone or "",
                "role":       user.role
            }
        }, 200

    except Exception:
        return {"error": "Login failed. Please try again."}, 500
