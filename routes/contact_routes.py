"""
Contact form API.

POST /api/contact/       — submit a message (passenger-facing)
GET  /api/contact/       — list all messages (admin only)
PUT  /api/contact/<id>/read  — mark a message as read (admin only)
DELETE /api/contact/<id>     — delete a message (admin only)
"""
import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from utils.decorators import admin_required
from models.contact_message import ContactMessage
from extensions import db, limiter

contact_bp = Blueprint("contact", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── POST /api/contact/ — submit form ─────────────────────────────
@contact_bp.route("/", methods=["POST"])
@limiter.limit("5 per minute")
def submit():
    data    = request.get_json() or {}
    name    = (data.get("name")    or "").strip()
    email   = (data.get("email")   or "").strip()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    # Validate
    if not all([name, email, subject, message]):
        return jsonify({"error": "All fields are required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Invalid email format"}), 400
    if len(name) > 100:
        return jsonify({"error": "Name too long (max 100 characters)"}), 400
    if len(subject) > 200:
        return jsonify({"error": "Subject too long (max 200 characters)"}), 400
    if len(message) > 2000:
        return jsonify({"error": "Message too long (max 2000 characters)"}), 400

    # Save to database
    msg = ContactMessage(
        name    = name,
        email   = email,
        subject = subject,
        message = message
    )
    db.session.add(msg)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to save your message. Please try again."}), 500

    # Send emails (non-blocking — failures don't break the response)
    _send_contact_emails(name, email, subject, message)

    return jsonify({
        "message": "Thank you! Your message has been received. We'll get back to you soon."
    }), 200


# ── GET /api/contact/ — admin: list all messages ─────────────────
@contact_bp.route("/", methods=["GET"])
@jwt_required()
@admin_required
def list_messages():
    unread_only = request.args.get("unread") == "true"
    query = ContactMessage.query
    if unread_only:
        query = query.filter_by(is_read=False)
    messages = query.order_by(ContactMessage.created_at.desc()).all()
    return jsonify({
        "messages": [m.to_dict() for m in messages],
        "total":    len(messages),
        "unread":   ContactMessage.query.filter_by(is_read=False).count()
    })


# ── PUT /api/contact/<id>/read — admin: mark as read ─────────────
@contact_bp.route("/<int:msg_id>/read", methods=["PUT"])
@jwt_required()
@admin_required
def mark_read(msg_id):
    msg = ContactMessage.query.get(msg_id)
    if not msg:
        return jsonify({"error": "Message not found"}), 404
    msg.is_read = True
    db.session.commit()
    return jsonify({"message": "Marked as read"}), 200


# ── DELETE /api/contact/<id> — admin: delete message ─────────────
@contact_bp.route("/<int:msg_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_message(msg_id):
    msg = ContactMessage.query.get(msg_id)
    if not msg:
        return jsonify({"error": "Message not found"}), 404
    db.session.delete(msg)
    db.session.commit()
    return jsonify({"message": "Message deleted"}), 200


# ── Internal helper ───────────────────────────────────────────────
def _send_contact_emails(name, email, subject, message):
    """
    Send:
      1. A confirmation email to the passenger
      2. A notification email to admin (if MAIL_DEFAULT_SENDER is set)
    Errors are silently logged — never crash the response.
    """
    try:
        from utils.mailer import send_contact_confirmation_email, send_admin_contact_notification
        from flask import current_app

        # Confirmation to the passenger
        send_contact_confirmation_email(email, name, subject)

        # Notification to admin (uses MAIL_USERNAME as admin address)
        admin_email = current_app.config.get("MAIL_USERNAME")
        if admin_email:
            send_admin_contact_notification(admin_email, name, email, subject, message)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[contact] Email error: {e}")
