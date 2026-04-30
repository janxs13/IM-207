"""
SMS notification utility using Semaphore (https://semaphore.co).
Philippine SMS gateway — ₱0.50/SMS, widely used in PH systems.

Setup:
  1. Register at semaphore.co
  2. Add SEMAPHORE_API_KEY=your_key to .env
  3. Load ₱500 credits (~1000 SMS)

If SEMAPHORE_API_KEY is not set, SMS is skipped silently (non-fatal).
"""
import logging
import urllib.request
import urllib.parse
import json
import os

logger = logging.getLogger(__name__)


def send_sms(phone: str, message: str, sender_name: str = "BUSBOOK") -> bool:
    """
    Send SMS via Semaphore API.
    Phone: Philippine mobile number (09XXXXXXXXX or +639XXXXXXXXX)
    Returns True if sent successfully.
    """
    try:
        from flask import current_app
        api_key = current_app.config.get("SEMAPHORE_API_KEY", "")
    except RuntimeError:
        api_key = os.environ.get("SEMAPHORE_API_KEY", "")

    if not api_key:
        logger.info(f"[SMS-SKIP] No SEMAPHORE_API_KEY — would send to {phone}: {message[:60]}")
        return False

    # Normalize phone number to Philippine format
    phone = phone.strip()
    if phone.startswith("+63"):
        phone = "0" + phone[3:]
    if not phone.startswith("09") or len(phone) != 11:
        logger.warning(f"[SMS] Invalid PH phone number: {phone}")
        return False

    payload = urllib.parse.urlencode({
        "apikey":      api_key,
        "number":      phone,
        "message":     message,
        "sendername":  sender_name,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.semaphore.co/api/v4/messages",
        data    = payload,
        method  = "POST",
        headers = {"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            logger.info(f"[SMS] Sent to {phone}: {result}")
            return True
    except Exception as e:
        logger.warning(f"[SMS] Failed to send to {phone}: {e}")
        return False


def send_booking_confirmation_sms(phone: str, booking_code: str,
                                   route: str, travel_date: str,
                                   seat: str) -> bool:
    """Send booking confirmation SMS to passenger."""
    msg = (
        f"BusBook: CONFIRMED! Ref: {booking_code}. "
        f"Route: {route}. Date: {travel_date}. "
        f"Seat: {seat}. Show QR at terminal. Safe travels!"
    )
    return send_sms(phone, msg)


def send_booking_cancelled_sms(phone: str, booking_code: str, route: str) -> bool:
    """Send cancellation SMS."""
    msg = (
        f"BusBook: Booking {booking_code} for {route} has been CANCELLED. "
        f"If you did not request this, contact support immediately."
    )
    return send_sms(phone, msg)


def send_otp_sms(phone: str, otp: str) -> bool:
    """Send OTP for 2FA."""
    msg = f"BusBook OTP: {otp}. Valid for 5 minutes. Do not share this code."
    return send_sms(phone, msg)
