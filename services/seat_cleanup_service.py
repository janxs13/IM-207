from datetime import datetime
from models.booking import Booking
from models.schedule import Schedule
from extensions import db
from sockets.seat_socket import emit_seat_update


def release_expired_seats():
    expired = Booking.query.filter(
        Booking.status == "locked",
        Booking.locked_until < datetime.utcnow()
    ).all()

    for booking in expired:
        booking.status = "expired"
        # Release the seat count back to schedule
        schedule = Schedule.query.get(booking.schedule_id)
        if schedule:
            schedule.seats_available += 1
        # Broadcast seat is available again
        if booking.seat_number:
            emit_seat_update(booking.schedule_id, booking.seat_number, "available")

    if expired:
        db.session.commit()
