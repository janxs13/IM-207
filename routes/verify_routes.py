from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from models.booking import Booking
from models.schedule import Schedule
from models.user import User

verify_bp = Blueprint("verify", __name__)

# GET /api/verify/<code>  — used by admin verify page
# Also supports /api/verify/ticket/<code> for backwards compat
@verify_bp.route("/<code>", methods=["GET"])
@jwt_required()
def verify_by_code(code):
    return _do_verify(code)

@verify_bp.route("/ticket/<code>", methods=["GET"])
@jwt_required()
def verify_ticket(code):
    return _do_verify(code)

def _do_verify(code):
    booking = Booking.query.filter_by(booking_code=code.upper()).first()

    if not booking:
        return jsonify({
            "valid":   False,
            "message": "Ticket not found. Invalid booking code."
        }), 200

    if booking.status != "confirmed":
        return jsonify({
            "valid":   False,
            "message": f"Ticket is not valid. Status: {booking.status}"
        }), 200

    schedule = Schedule.query.get(booking.schedule_id)
    user     = User.query.get(booking.user_id)
    passenger_name = f"{user.first_name} {user.last_name}" if user else "Unknown"

    return jsonify({
        "valid":   True,
        "status":  booking.status,
        "message": "Ticket is authentic and valid.",
        "booking": {
            "booking_code":    booking.booking_code,
            "passenger_name":  passenger_name,
            "route":           schedule.route if schedule else "—",
            "seat_number":     booking.seat_number or "—",
            "travel_date":     booking.travel_date or "—",
            "departure_time":  schedule.departure_time if schedule else "—",
            "amount":          booking.amount or 0
        }
    }), 200
