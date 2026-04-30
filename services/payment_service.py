import logging
import uuid
import base64
import json
import urllib.request
import urllib.error
from sqlalchemy import select

from models.booking import Booking
from models.payment import Payment
from extensions import db

logger = logging.getLogger(__name__)


class _PayAbort(Exception):
    __slots__ = ("body", "status")
    def __init__(self, body, status):
        self.body   = body
        self.status = status


# ── PayMongo helpers ──────────────────────────────────────────────
PAYMONGO_API = "https://api.paymongo.com/v1"

# Channel map: our internal name → PayMongo source type
_PM_CHANNEL_MAP = {
    "gcash":    "gcash",
    "maya":     "paymaya",
    "grab_pay": "grab_pay",
    "card":     "card",
}


def _pm_auth_header(secret_key: str) -> str:
    """Return the Basic Auth header value for PayMongo."""
    encoded = base64.b64encode(f"{secret_key}:".encode()).decode()
    return f"Basic {encoded}"


def _pm_request(method: str, path: str, payload: dict, secret_key: str) -> dict:
    """
    Make a PayMongo REST API call using only stdlib (no requests library needed).
    Returns the parsed JSON response dict.
    Raises _PayAbort on API error.
    """
    url  = PAYMONGO_API + path
    body = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url,
        data   = body if method in ("POST", "PUT") else None,
        method = method,
        headers = {
            "Authorization": _pm_auth_header(secret_key),
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            errors   = err_body.get("errors", [])
            msg      = errors[0].get("detail", "PayMongo API error") if errors else "PayMongo API error"
        except Exception:
            msg = f"PayMongo API error ({e.code})"
        raise _PayAbort({"error": msg}, 502)
    except urllib.error.URLError as e:
        raise _PayAbort({"error": "Could not reach PayMongo. Check your internet connection."}, 503)
    except Exception as e:
        raise _PayAbort({"error": "Unexpected error contacting PayMongo."}, 500)


def _create_paymongo_source(amount_php: float, channel: str,
                             secret_key: str, base_url: str,
                             description: str, booking_code: str) -> dict:
    """
    Create a PayMongo Source (for GCash, Maya, GrabPay).
    Returns the source object data dict.
    """
    pm_type = _PM_CHANNEL_MAP.get(channel, channel)
    amount_centavos = int(round(amount_php * 100))

    payload = {
        "data": {
            "attributes": {
                "amount":      amount_centavos,
                "currency":    "PHP",
                "type":        pm_type,
                "description": description,
                "redirect": {
                    "success": f"{base_url}/payment/paymongo/success?ref={booking_code}",
                    "failed":  f"{base_url}/payment/paymongo/failed?ref={booking_code}",
                },
                "billing": {
                    "name": "BusBook Passenger",
                },
                "metadata": {
                    "booking_code": booking_code,
                },
            }
        }
    }
    resp = _pm_request("POST", "/sources", payload, secret_key)
    return resp.get("data", {})


def _create_paymongo_payment_intent(amount_php: float, secret_key: str,
                                     description: str, booking_code: str) -> dict:
    """
    Create a PayMongo PaymentIntent (for card payments).
    Returns the intent object data dict.
    """
    amount_centavos = int(round(amount_php * 100))
    payload = {
        "data": {
            "attributes": {
                "amount":                amount_centavos,
                "currency":              "PHP",
                "description":           description,
                "payment_method_allowed": ["card"],
                "capture_type":          "automatic",
                "metadata": {
                    "booking_code": booking_code,
                },
            }
        }
    }
    resp = _pm_request("POST", "/payment_intents", payload, secret_key)
    return resp.get("data", {})


def _attach_payment_method(intent_id: str, payment_method_id: str,
                            secret_key: str, base_url: str,
                            booking_code: str) -> dict:
    """Attach a PaymentMethod to a PaymentIntent."""
    payload = {
        "data": {
            "attributes": {
                "payment_method": payment_method_id,
                "return_url":     f"{base_url}/payment/paymongo/success?ref={booking_code}",
            }
        }
    }
    resp = _pm_request("POST", f"/payment_intents/{intent_id}/attach",
                        payload, secret_key)
    return resp.get("data", {})


# ── Main process_payment entry point ─────────────────────────────
def process_payment(data, payer_user_id, is_admin=False):
    booking_id     = data.get("booking_id")
    payment_method = (data.get("payment_method") or "").strip().lower()
    channel        = (data.get("channel")         or "").strip().lower()
    # For card: frontend sends a PayMongo payment_method_id after tokenising the card
    pm_method_id   = data.get("payment_method_id", "")

    if not booking_id or not payment_method:
        return {"error": "booking_id and payment_method are required"}, 400

    try:
        bid = int(booking_id)
    except (TypeError, ValueError):
        return {"error": "Invalid booking_id"}, 400

    allowed_methods = {"gcash", "paymaya", "paypal", "paymongo", "cash"}
    if payment_method not in allowed_methods:
        return {"error": f"Invalid payment method. Allowed: {', '.join(sorted(allowed_methods))}"}, 400

    reference_no    = "REF-" + str(uuid.uuid4())[:8].upper()
    booking_code_out = None
    seat_number_out  = None
    amount_out       = None

    try:
        booking = db.session.execute(
            select(Booking).where(Booking.id == bid).with_for_update()
        ).scalar_one_or_none()

        if not booking:
            raise _PayAbort({"error": "Booking not found"}, 404)
        if not is_admin and int(booking.user_id) != int(payer_user_id):
            raise _PayAbort({"error": "Access denied"}, 403)
        if booking.status == "confirmed":
            raise _PayAbort({"error": "Booking is already paid"}, 400)
        if booking.status == "cancelled":
            raise _PayAbort({"error": "Cannot pay for a cancelled booking"}, 400)
        if booking.status == "expired":
            raise _PayAbort({"error": "This booking has expired. Please create a new one."}, 400)

        amount = float(booking.amount or 0)
        if amount <= 0:
            raise _PayAbort({"error": "Invalid booking amount"}, 400)

        booking_code_out = booking.booking_code
        seat_number_out  = booking.seat_number
        amount_out       = amount

        # ── PayMongo live API call ────────────────────────────────
        paymongo_data = {}
        checkout_url  = None

        if payment_method == "paymongo":
            from flask import current_app
            secret_key = current_app.config.get("PAYMONGO_SECRET_KEY", "")
            base_url   = current_app.config.get("APP_BASE_URL", "http://localhost:5000")

            if not secret_key:
                # No key configured — fall through to sandbox/demo mode
                logger.warning("PAYMONGO_SECRET_KEY not set — using sandbox reference")
            else:
                description = f"BusBook ticket {booking.booking_code} — {booking.route or 'Bus Ticket'}"

                if channel in ("gcash", "maya", "grab_pay"):
                    # e-wallet flow: create Source → redirect user to checkout URL
                    source = _create_paymongo_source(
                        amount, channel, secret_key, base_url,
                        description, booking.booking_code
                    )
                    attrs        = source.get("attributes", {})
                    checkout_url = attrs.get("redirect", {}).get("checkout_url")
                    reference_no = source.get("id", reference_no)
                    paymongo_data = {"source_id": source.get("id"), "type": "source"}

                elif channel == "card" and pm_method_id:
                    # Card flow: create PaymentIntent → attach PaymentMethod
                    intent      = _create_paymongo_payment_intent(
                        amount, secret_key, description, booking.booking_code
                    )
                    intent_id   = intent.get("id")
                    intent_data = _attach_payment_method(
                        intent_id, pm_method_id, secret_key, base_url, booking.booking_code
                    )
                    attrs        = intent_data.get("attributes", {})
                    status_pm    = attrs.get("status", "")
                    reference_no = intent_id or reference_no
                    checkout_url = attrs.get("next_action", {}).get("redirect", {}).get("url")
                    paymongo_data = {"intent_id": intent_id, "status": status_pm}

        # ── Confirm booking in DB ─────────────────────────────────
        booking.status         = "confirmed"
        booking.payment_method = payment_method
        booking.reference_no   = reference_no
        booking.amount         = amount

        db.session.add(Payment(
            booking_id     = booking.id,
            amount         = amount,
            payment_method = payment_method,
            reference_no   = reference_no,
            status         = "completed",
        ))
        db.session.commit()

        # ── Send confirmation email + SMS to passenger ──────
        if not checkout_url:
            try:
                from models.user import User
                from models.schedule import Schedule as Sched
                from utils.mailer import send_booking_confirmation_email
                from utils.sms   import send_booking_confirmation_sms
                pax_user = User.query.get(int(booking.user_id))
                sched    = Sched.query.get(booking.schedule_id)
                if pax_user:
                    pax_name = f"{pax_user.first_name or ''} {pax_user.last_name or ''}".strip() or pax_user.email
                    route    = sched.route if sched else ""
                    travel_date = getattr(booking, "travel_date", "")
                    # Email
                    if pax_user.email:
                        send_booking_confirmation_email(
                            recipient_email = pax_user.email,
                            name            = pax_name,
                            booking_code    = booking_code_out,
                            route           = route,
                            travel_date     = travel_date,
                            seat_number     = seat_number_out or "—",
                            amount          = amount_out,
                            reference_no    = reference_no,
                            payment_method  = payment_method,
                        )
                    # SMS
                    if pax_user.phone:
                        send_booking_confirmation_sms(
                            phone        = pax_user.phone,
                            booking_code = booking_code_out,
                            route        = route,
                            travel_date  = travel_date,
                            seat         = seat_number_out or "—",
                        )
            except Exception:
                logger.warning("Confirmation notifications failed — payment still confirmed")

    except _PayAbort as e:
        db.session.rollback()
        return e.body, e.status
    except Exception:
        db.session.rollback()
        logger.exception("process_payment failed")
        return {"error": "Payment processing failed. Please try again."}, 500

    response = {
        "message": "Payment successful",
        "payment": {
            "reference_no":   reference_no,
            "payment_method": payment_method,
            "amount":         amount_out,
            "booking_code":   booking_code_out,
            "seat_number":    seat_number_out,
        },
    }
    # If PayMongo returned a redirect URL (e-wallet), include it so the
    # frontend can redirect the user to complete the payment
    if checkout_url:
        response["checkout_url"] = checkout_url
        response["payment"]["status"] = "pending_redirect"

    return response, 200
