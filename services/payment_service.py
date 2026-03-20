import uuid
from models.booking import Booking
from models.payment import Payment
from extensions import db


def process_payment(data):
    booking_id     = data.get("booking_id")
    payment_method = data.get("payment_method")
    amount         = data.get("amount")

    if not booking_id or not payment_method:
        return {"error": "booking_id and payment_method are required"}, 400

    booking = Booking.query.get(int(booking_id))
    if not booking:
        return {"error": "Booking not found"}, 404

    if booking.status == "confirmed":
        return {"error": "Booking is already paid"}, 400

    if booking.status == "cancelled":
        return {"error": "Cannot pay for a cancelled booking"}, 400

    # Use booking's stored amount if not sent
    if not amount:
        amount = booking.amount
    if not amount:
        return {"error": "Amount is required"}, 400

    reference_no = "REF-" + str(uuid.uuid4())[:8].upper()

    booking.status         = "confirmed"
    booking.payment_method = payment_method
    booking.reference_no   = reference_no
    booking.amount         = float(amount)

    payment = Payment(
        booking_id     = booking.id,
        amount         = float(amount),
        payment_method = payment_method,
        reference_no   = reference_no,
        status         = "completed"
    )
    db.session.add(payment)
    db.session.commit()

    return {
        "message": "Payment successful",
        "payment": {
            "reference_no":   reference_no,
            "payment_method": payment_method,
            "amount":         booking.amount,
            "booking_code":   booking.booking_code
        }
    }, 200
