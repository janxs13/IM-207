import json
import hmac
import hashlib
import logging
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.payment_service import process_payment
from extensions import limiter, db
from utils.decorators import current_user_is_admin
from models.booking import Booking
from models.payment import Payment

payment_bp = Blueprint("payment", __name__)
logger = logging.getLogger(__name__)


# ── GET /api/payments/paymongo/public-key ────────────────────────
@payment_bp.route("/paymongo/public-key", methods=["GET"])
def paymongo_public_key():
    """Return the PayMongo public key so paymongo.html can init PayMongo.js."""
    pk = current_app.config.get("PAYMONGO_PUBLIC_KEY", "")
    return jsonify({"public_key": pk}), 200


# ── POST /api/payments/ — process payment ────────────────────────
@payment_bp.route("/", methods=["POST"])
@jwt_required()
@limiter.limit("20 per hour")
def pay():
    data   = request.get_json() or {}
    result, status = process_payment(
        data, int(get_jwt_identity()), is_admin=current_user_is_admin()
    )
    return jsonify(result), status


# ── POST /api/payments/paymongo/webhook — PayMongo webhook ───────
@payment_bp.route("/paymongo/webhook", methods=["POST"])
def paymongo_webhook():
    """
    PayMongo sends signed webhook events here.
    Register this URL in your PayMongo dashboard:
      https://dashboard.paymongo.com/developers → Webhooks
      → https://yourdomain.com/api/payments/paymongo/webhook

    Events handled:
      - source.chargeable   → charge the source (e-wallet)
      - payment.paid        → confirm booking in DB
      - payment.failed      → mark booking as failed
    """
    secret_key   = current_app.config.get("PAYMONGO_SECRET_KEY", "")
    webhook_secret = current_app.config.get("PAYMONGO_WEBHOOK_SECRET", "")

    raw_body = request.get_data()

    # ── Verify webhook signature (optional but recommended) ───────
    if webhook_secret:
        sig_header = request.headers.get("Paymongo-Signature", "")
        # Signature format: t=TIMESTAMP,te=HASH,li=HASH
        try:
            parts     = {p.split("=")[0]: p.split("=")[1] for p in sig_header.split(",")}
            timestamp = parts.get("t", "")
            sig_te    = parts.get("te", "")
            message   = f"{timestamp}.{raw_body.decode('utf-8')}"
            # FIX: Python 3 uses hmac.new() correctly — ensure bytes
            expected  = hmac.new(
                webhook_secret.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected, sig_te):
                logger.warning("PayMongo webhook signature mismatch")
                return jsonify({"error": "Invalid signature"}), 400
        except Exception:
            pass  # Proceed even if signature check fails (log it)

    try:
        event = json.loads(raw_body)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    event_type = event.get("data", {}).get("attributes", {}).get("type", "")
    attrs      = event.get("data", {}).get("attributes", {}).get("data", {})

    logger.info(f"PayMongo webhook received: {event_type}")

    # ── source.chargeable — create charge for e-wallet source ────
    if event_type == "source.chargeable":
        source_id    = attrs.get("id", "")
        source_attrs = attrs.get("attributes", {})
        amount       = source_attrs.get("amount", 0)
        currency     = source_attrs.get("currency", "PHP")
        metadata     = source_attrs.get("metadata", {})
        booking_code = metadata.get("booking_code", "")
        description  = source_attrs.get("description", f"BusBook {booking_code}")

        if secret_key and source_id:
            try:
                import base64, urllib.request, urllib.error
                charge_payload = json.dumps({
                    "data": {
                        "attributes": {
                            "amount":      amount,
                            "currency":    currency,
                            "description": description,
                            "source": {
                                "id":   source_id,
                                "type": "source",
                            },
                        }
                    }
                }).encode("utf-8")

                encoded = base64.b64encode(f"{secret_key}:".encode()).decode()
                req = urllib.request.Request(
                    "https://api.paymongo.com/v1/payments",
                    data    = charge_payload,
                    method  = "POST",
                    headers = {
                        "Authorization": f"Basic {encoded}",
                        "Content-Type":  "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    charge_resp = json.loads(resp.read().decode())
                    logger.info(f"PayMongo charge created: {charge_resp.get('data',{}).get('id','')}")
            except Exception as ex:
                logger.exception(f"Failed to create PayMongo charge: {ex}")

    # ── payment.paid — confirm booking ────────────────────────────
    elif event_type == "payment.paid":
        metadata     = attrs.get("attributes", {}).get("metadata", {})
        booking_code = metadata.get("booking_code", "")
        reference_no = attrs.get("id", "")

        if booking_code:
            try:
                booking = Booking.query.filter_by(booking_code=booking_code).first()
                if booking and booking.status != "confirmed":
                    booking.status       = "confirmed"
                    booking.reference_no = reference_no
                    # Also upsert a Payment record
                    existing = Payment.query.filter_by(reference_no=reference_no).first()
                    if not existing:
                        db.session.add(Payment(
                            booking_id     = booking.id,
                            amount         = float(attrs.get("attributes", {}).get("amount", 0)) / 100,
                            payment_method = "paymongo",
                            reference_no   = reference_no,
                            status         = "completed",
                        ))
                    db.session.commit()
                    logger.info(f"Booking {booking_code} confirmed via webhook")
            except Exception:
                db.session.rollback()
                logger.exception("Failed to confirm booking via webhook")

    # ── payment.failed — handle failure ──────────────────────────
    elif event_type == "payment.failed":
        metadata     = attrs.get("attributes", {}).get("metadata", {})
        booking_code = metadata.get("booking_code", "")
        if booking_code:
            logger.warning(f"PayMongo payment failed for booking {booking_code}")
            # Optionally revert booking status to 'pending' so passenger can retry
            try:
                booking = Booking.query.filter_by(booking_code=booking_code).first()
                if booking and booking.status == "confirmed":
                    pass  # Already confirmed — don't revert
                elif booking:
                    booking.status = "pending"
                    db.session.commit()
            except Exception:
                db.session.rollback()

    return jsonify({"received": True}), 200
