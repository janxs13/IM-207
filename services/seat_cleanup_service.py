from datetime import datetime
from models.booking import Booking
from models.schedule import Schedule
from extensions import db
from sockets.seat_socket import emit_seat_update


def release_expired_seats():
    """
    Release seats for bookings that have passed their locked_until time
    and are still in 'locked' or 'pending' (unpaid) status.
    Confirmed bookings are never touched.
    """
    now = datetime.utcnow()

    # Catch both 'locked' and 'pending' bookings past their reservation window
    expired = Booking.query.filter(
        Booking.status.in_(["locked", "pending"]),
        Booking.locked_until != None,
        Booking.locked_until < now,
        Booking.deleted_at.is_(None)
    ).all()

    for booking in expired:
        old_status = booking.status
        booking.status = "expired"

        # Restore the correct number of seats back to the schedule
        schedule = Schedule.query.get(booking.schedule_id)
        if schedule:
            pax = booking.passenger_count or 1
            schedule.seats_available += pax

        # Broadcast each seat as available again via SocketIO
        if booking.seat_number:
            for seat in booking.seat_number.split(","):
                seat = seat.strip()
                if seat:
                    try:
                        emit_seat_update(booking.schedule_id, seat, "available")
                    except Exception:
                        pass  # socket not available during startup is fine

    if expired:
        db.session.commit()
        print(f"[cleanup] Released {len(expired)} expired booking(s)")
