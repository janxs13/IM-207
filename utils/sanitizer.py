"""
Input sanitization and validation utilities.
Used across all routes to prevent XSS and injection attacks.
"""
import re
import html


def sanitize_text(value: str, max_len: int = 200) -> str:
    """Strip HTML tags and limit length."""
    if not value:
        return ""
    cleaned = html.escape(str(value).strip())
    # Remove any remaining HTML-like patterns
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    return cleaned[:max_len]


def validate_ph_phone(phone: str) -> bool:
    """Validate Philippine mobile number: 09XXXXXXXXX or +639XXXXXXXXX"""
    if not phone:
        return False
    return bool(re.match(r'^(09|\+639)\d{9}$', phone.strip()))


def validate_password_strength(password: str) -> tuple:
    """
    Returns (is_valid: bool, message: str).
    Requires: 8+ chars, 1 uppercase, 1 number.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number."
    if len(password) > 128:
        return False, "Password is too long (max 128 characters)."
    return True, "OK"


def validate_plate_number(plate: str) -> bool:
    """Philippine plate format: ABC-1234 or ABC1234"""
    if not plate:
        return False
    return bool(re.match(r'^[A-Z]{3}-?\d{3,4}$', plate.strip().upper()))


def validate_email(email: str) -> bool:
    """Basic email format check."""
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', (email or "").strip()))


def sanitize_booking_code(code: str) -> str:
    """Sanitize booking code — only allow alphanumeric and dashes."""
    return re.sub(r'[^A-Z0-9\-]', '', (code or "").strip().upper())[:20]
