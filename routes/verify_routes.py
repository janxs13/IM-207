from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from utils.decorators import admin_required
from models.booking import Booking
from models.schedule import Schedule
from models.user import User
from extensions import db

verify_bp = Blueprint("verify", __name__)

@verify_bp.route("/<code>", methods=["GET"])
@jwt_required()
@admin_required
def verify_by_code(code):
    return _do_verify(code)

@verify_bp.route("/ticket/<code>", methods=["GET"])
@jwt_required()
@admin_required
def verify_ticket(code):
    return _do_verify(code)


def _do_verify(code):
    booking = Booking.query.filter_by(booking_code=code.upper()).first()

    # ── Code doesn't exist ──────────────────────────────────────────
    if not booking:
        return jsonify({
            "valid":   False,
            "state":   "not_found",
            "message": "Ticket not found. Please check the booking code and try again."
        }), 200

    # ── Booking exists but not confirmed (pending/cancelled) ────────
    if booking.status != "confirmed":
        return jsonify({
            "valid":   False,
            "state":   "not_confirmed",
            "message": f"Ticket is not valid. Booking status is '{booking.status}' — only confirmed bookings can be verified."
        }), 200

    # ── Already verified twice or more — block ──────────────────────
    verify_count = booking.verify_count or 0
    if verify_count >= 2:
        return jsonify({
            "valid":   False,
            "state":   "already_used",
            "message": (
                f"This reference code '{booking.booking_code}' is invalid because "
                "you can only verify a ticket once. This ticket has already been "
                "scanned and verified at boarding."
            )
        }), 200

    # ── Fetch related records ───────────────────────────────────────
    schedule = Schedule.query.get(booking.schedule_id)
    user     = User.query.get(booking.user_id)
    from models.bus import Bus
    bus = Bus.query.get(schedule.bus_id) if schedule and schedule.bus_id else None

    passenger_name = f"{user.first_name} {user.last_name}".strip() if user else "Unknown"
    fare_per_seat  = schedule.fare if schedule else 0
    pax            = booking.passenger_count or 1

    # ── First verify: valid, increment counter ──────────────────────
    if verify_count == 0:
        booking.verify_count = 1
        db.session.commit()
        state   = "valid_first"
        message = "Ticket is authentic and valid. Passenger may board."

    # ── Second verify: show warning but still display details ────────
    else:  # verify_count == 1
        booking.verify_count = 2
        db.session.commit()
        state   = "valid_warning"
        message = (
            "⚠️ Warning: This ticket has already been verified once. "
            "If this is a second scan at boarding, please check the passenger "
            "before allowing entry."
        )

    return jsonify({
        "valid":   True,
        "state":   state,
        "message": message,
        "verify_count": booking.verify_count,
        "booking": {
            "booking_code":    booking.booking_code,
            "passenger_name":  passenger_name,
            "route":           schedule.route if schedule else "—",
            "seat_number":     booking.seat_number or "—",
            "travel_date":     booking.travel_date or "—",
            "departure_time":  (schedule.departure_time or "—").split("T")[-1] if schedule else "—",
            "amount":          booking.amount or 0,
            "fare_per_seat":   fare_per_seat,
            "passenger_count": pax,
            "bus_name":        bus.name if bus else "—",
            "bus_plate":       bus.plate_number if bus else "—",
            "payment_method":  booking.payment_method or "—",
            "reference_no":    booking.reference_no or "—",
        }
    }), 200
