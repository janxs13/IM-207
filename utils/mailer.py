"""
BusBook mailer utility.
Sends transactional emails via Flask-Mail.
All sends are non-fatal — if mail fails, the transaction still completes.
"""
import logging
from flask import current_app

logger = logging.getLogger(__name__)


def _get_mail():
    from extensions import mail
    return mail


def send_booking_confirmation_email(
    recipient_email, name, booking_code, route,
    travel_date, seat_number, amount, reference_no, payment_method
):
    """Send a booking confirmation email with ticket details."""
    try:
        from flask_mail import Message
        mail = _get_mail()

        subject = f"BusBook — Booking Confirmed! [{booking_code}]"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; background: #f8f9fa; margin: 0; padding: 0; }}
    .wrap {{ max-width: 560px; margin: 32px auto; background: #fff;
             border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,.08); }}
    .header {{ background: linear-gradient(135deg,#f4a261,#e76f51); padding: 28px 32px; text-align: center; }}
    .header h1 {{ color: #fff; margin: 0; font-size: 24px; }}
    .header p  {{ color: rgba(255,255,255,.85); margin: 6px 0 0; font-size: 14px; }}
    .body   {{ padding: 28px 32px; }}
    .row    {{ display: flex; justify-content: space-between; padding: 10px 0;
               border-bottom: 1px solid #e2e8f0; font-size: 14px; }}
    .row:last-child {{ border: none; }}
    .lbl    {{ color: #94a3b8; }}
    .val    {{ font-weight: 700; color: #1e293b; }}
    .code   {{ background: #fff7ed; border: 2px dashed #f4a261; border-radius: 10px;
               text-align: center; padding: 18px; margin: 20px 0; }}
    .code h2 {{ margin: 0; font-size: 28px; letter-spacing: 4px; color: #e76f51; }}
    .code p  {{ margin: 4px 0 0; font-size: 12px; color: #94a3b8; }}
    .btn    {{ display: block; background: #f4a261; color: #fff; text-decoration: none;
               border-radius: 10px; padding: 12px 24px; text-align: center;
               font-weight: 700; font-size: 15px; margin: 20px 0 0; }}
    .footer {{ background: #f8f9fa; padding: 16px 32px; text-align: center;
               font-size: 11px; color: #94a3b8; }}
  </style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>Booking Confirmed!</h1>
    <p>Your BusBook e-ticket is ready</p>
  </div>
  <div class="body">
    <p>Hi <strong>{name}</strong>,</p>
    <p>Your booking has been confirmed and your payment has been received.
       Show the QR code on your ticket at the terminal gate for boarding.</p>

    <div class="code">
      <h2>{booking_code}</h2>
      <p>Booking Reference Code</p>
    </div>

    <div class="row"><span class="lbl">Route</span><span class="val">{route}</span></div>
    <div class="row"><span class="lbl">Travel Date</span><span class="val">{travel_date}</span></div>
    <div class="row"><span class="lbl">Seat Number</span><span class="val">{seat_number}</span></div>
    <div class="row"><span class="lbl">Amount Paid</span><span class="val">&#8369;{float(amount):.2f}</span></div>
    <div class="row"><span class="lbl">Payment Method</span><span class="val">{payment_method.title()}</span></div>
    <div class="row"><span class="lbl">Reference No.</span><span class="val">{reference_no}</span></div>

    <a href="{current_app.config.get('APP_BASE_URL','http://localhost:5000')}/ticket?code={booking_code}"
       class="btn">View & Download E-Ticket</a>

    <p style="font-size:12px;color:#94a3b8;margin-top:16px;">
      Please arrive at least 30 minutes before departure.
      Bring a valid government-issued ID for boarding verification.
    </p>
  </div>
  <div class="footer">
    BusBook Bus Ticketing System &nbsp;|&nbsp; This is an automated message, please do not reply.
  </div>
</div>
</body>
</html>"""

        text_body = (
            f"BusBook — Booking Confirmed!\n\n"
            f"Hi {name},\n\n"
            f"Your booking is confirmed.\n\n"
            f"Booking Code:   {booking_code}\n"
            f"Route:          {route}\n"
            f"Travel Date:    {travel_date}\n"
            f"Seat:           {seat_number}\n"
            f"Amount Paid:    PHP {float(amount):.2f}\n"
            f"Payment:        {payment_method}\n"
            f"Reference No.:  {reference_no}\n\n"
            f"Please arrive 30 minutes before departure and bring a valid ID.\n\n"
            f"BusBook Bus Ticketing System"
        )

        msg = Message(
            subject    = subject,
            recipients = [recipient_email],
            body       = text_body,
            html       = html_body,
        )
        mail.send(msg)
        logger.info(f"Confirmation email sent to {recipient_email} for {booking_code}")
        return True

    except Exception as e:
        logger.warning(f"Email send failed for {recipient_email}: {e}")
        return False


def send_password_reset_email(recipient_email, reset_token, name=""):
    """Send a password-reset email."""
    try:
        from flask_mail import Message
        mail = _get_mail()
        base_url = current_app.config.get("APP_BASE_URL", "http://localhost:5000")
        reset_url = f"{base_url}/reset-password?token={reset_token}"

        subject  = "BusBook — Password Reset Request"
        text_body = (
            f"Hi {name or 'there'},\n\n"
            f"You requested a password reset for your BusBook account.\n\n"
            f"Click the link below (valid for 30 minutes):\n{reset_url}\n\n"
            f"If you didn't request this, ignore this email."
        )
        html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;">
  <div style="background:linear-gradient(135deg,#f4a261,#e76f51);padding:24px;border-radius:12px 12px 0 0;text-align:center;">
    <h2 style="color:#fff;margin:0;">Password Reset</h2>
  </div>
  <div style="background:#fff;padding:24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;">
    <p>Hi <strong>{name or 'there'}</strong>,</p>
    <p>Click the button below to reset your password. This link expires in <strong>30 minutes</strong>.</p>
    <a href="{reset_url}"
       style="display:block;background:#f4a261;color:#fff;text-decoration:none;border-radius:8px;padding:12px;text-align:center;font-weight:700;margin:20px 0;">
      Reset Password
    </a>
    <p style="font-size:12px;color:#94a3b8;">If you didn't request this, you can safely ignore this email.</p>
  </div>
</div>"""

        msg = Message(subject=subject, recipients=[recipient_email],
                      body=text_body, html=html_body)
        mail.send(msg)
        return True
    except Exception as e:
        logger.warning(f"Password reset email failed: {e}")
        return False
