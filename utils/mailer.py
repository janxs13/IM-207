"""
Email utility for BusBook.

Sending behaviour:
  - MAIL_USERNAME is set in .env  →  sends a real email via SMTP
  - MAIL_USERNAME is NOT set      →  prints the email to the console (dev mode)

Usage:
    from utils.mailer import send_password_reset_email, send_contact_confirmation_email
"""
from flask import current_app
from flask_mail import Message
from extensions import mail


def _send(msg):
    """Send a Flask-Mail message. Falls back to console print if mail is suppressed."""
    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        # Development / no-credentials mode: print to terminal
        print("\n" + "=" * 60)
        print(f"[MAIL - console mode]  To: {msg.recipients}")
        print(f"Subject: {msg.subject}")
        print("-" * 60)
        print(msg.body)
        print("=" * 60 + "\n")
    else:
        mail.send(msg)


def send_password_reset_email(recipient_email: str, reset_token: str, expires_minutes: int = 30):
    """
    Send a password-reset token to the user.
    In dev mode (no MAIL_USERNAME), prints to console.
    """
    subject = "BusBook — Password Reset Request"
    body = f"""Hello,

You requested a password reset for your BusBook account.

Your reset token is:

    {reset_token}

This token expires in {expires_minutes} minutes.

To reset your password:
  1. Go to the BusBook forgot-password page
  2. Enter your email address
  3. Enter the token above
  4. Choose a new password

If you did not request a password reset, please ignore this email.
Your account remains secure.

— The BusBook Team
"""
    msg = Message(subject=subject, recipients=[recipient_email], body=body)
    try:
        _send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"[mailer] Failed to send reset email to {recipient_email}: {e}")
        return False


def send_contact_confirmation_email(recipient_email: str, name: str, subject_text: str):
    """
    Send a confirmation email to a passenger who submitted the contact form.
    """
    subject = "BusBook — We received your message"
    body = f"""Hello {name},

Thank you for contacting BusBook!

We received your message about: "{subject_text}"

Our support team will get back to you within 24 hours.

If your inquiry is urgent, please reply to this email directly.

— The BusBook Support Team
"""
    msg = Message(subject=subject, recipients=[recipient_email], body=body)
    try:
        _send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"[mailer] Failed to send confirmation to {recipient_email}: {e}")
        return False


def send_admin_contact_notification(admin_email: str, sender_name: str,
                                     sender_email: str, subject_text: str, message_body: str):
    """
    Notify the admin that a new contact form message arrived.
    """
    subject = f"BusBook Contact — {subject_text}"
    body = f"""New contact form submission:

From:    {sender_name} <{sender_email}>
Subject: {subject_text}

Message:
{message_body}

---
Reply to: {sender_email}
"""
    msg = Message(subject=subject, recipients=[admin_email], body=body, reply_to=sender_email)
    try:
        _send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"[mailer] Failed to send admin notification: {e}")
        return False


def send_admin_reply_to_contact(recipient_email: str, recipient_name: str, subject_text: str, reply_message: str):
    """
    Send an admin-written reply back to a contact form sender.
    """
    support_email = current_app.config.get("MAIL_USERNAME")
    subject = f"Re: {subject_text}"
    body = f"""Hello {recipient_name},

{reply_message}

---
This reply was sent by BusBook Support.
"""
    msg = Message(
        subject=subject,
        recipients=[recipient_email],
        body=body,
        reply_to=support_email if support_email else None
    )
    try:
        _send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"[mailer] Failed to send admin reply to {recipient_email}: {e}")
        return False
