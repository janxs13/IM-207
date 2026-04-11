import logging
import uuid
from sqlalchemy import select

from models.booking import Booking
from models.payment import Payment
from extensions import db

logger = logging.getLogger(__name__)


class _PayAbort(Exception):
    __slots__ = ("body", "status")

    def __init__(self, body, status):
        self.body = body
        self.status = status


def process_payment(data, payer_user_id, is_admin=False):
    booking_id = data.get("booking_id")
    payment_method = (data.get("payment_method") or "").strip()

    if not booking_id or not payment_method:
        return {"error": "booking_id and payment_method are required"}, 400

    try:
        bid = int(booking_id)
    except (TypeError, ValueError):
        return {"error": "Invalid booking_id"}, 400

    allowed_methods = {"gcash", "paymaya", "paypal", "cash"}
    if payment_method.lower() not in allowed_methods:
        return {
            "error": f"Invalid payment method. Allowed: {', '.join(sorted(allowed_methods))}"
        }, 400

    reference_no = "REF-" + str(uuid.uuid4())[:8].upper()
    booking_code_out = None
    seat_number_out = None
    amount_out = None

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
            raise _PayAbort(
                {"error": "This booking has expired. Please create a new one."}, 400
            )

        amount = float(booking.amount or 0)
        if amount <= 0:
            raise _PayAbort({"error": "Invalid booking amount"}, 400)

        booking_code_out = booking.booking_code
        seat_number_out = booking.seat_number
        amount_out = amount

        booking.status = "confirmed"
        booking.payment_method = payment_method
        booking.reference_no = reference_no
        booking.amount = amount

        db.session.add(
            Payment(
                booking_id=booking.id,
                amount=amount,
                payment_method=payment_method,
                reference_no=reference_no,
                status="completed",
            )
        )
        db.session.commit()
    except _PayAbort as e:
        db.session.rollback()
        return e.body, e.status
    except Exception:
        db.session.rollback()
        logger.exception("process_payment failed")
        return {"error": "Payment processing failed. Please try again."}, 500

    return {
        "message": "Payment successful",
        "payment": {
            "reference_no": reference_no,
            "payment_method": payment_method,
            "amount": amount_out,
            "booking_code": booking_code_out,
            "seat_number": seat_number_out,
        },
    }, 200
