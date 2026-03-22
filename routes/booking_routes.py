from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from services.booking_service import create_booking, get_all_bookings, get_user_bookings
from models.booking import Booking
from models.schedule import Schedule
from extensions import db

booking_bp = Blueprint("booking", __name__)

# POST /api/bookings/ — create a new booking
@booking_bp.route("/", methods=["POST"])
@jwt_required()
def book():
    data = request.get_json()
    # Inject user_id from JWT if not sent (security: always trust JWT)
    data["user_id"] = int(get_jwt_identity())
    response, status = create_booking(data)
    return jsonify(response), status

# GET /api/bookings/ — all bookings (admin only)
@booking_bp.route("/", methods=["GET"])
@jwt_required()
def all_bookings():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    return jsonify(get_all_bookings())

# GET /api/bookings/user/<id> — user booking history
@booking_bp.route("/user/<int:user_id>", methods=["GET"])
@jwt_required()
def user_bookings(user_id):
    current_user_id = int(get_jwt_identity())
    claims = get_jwt()
    if current_user_id != user_id and claims.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403
    return jsonify(get_user_bookings(user_id))

# GET /api/bookings/seats/<schedule_id> — booked seats for seat map
@booking_bp.route("/seats/<int:schedule_id>", methods=["GET"])
def booked_seats(schedule_id):
    taken = Booking.query.filter(
        Booking.schedule_id == schedule_id,
        Booking.status.in_(["locked", "pending", "confirmed"])
    ).all()

    # Flatten comma-separated seat strings into a list of individual seat IDs
    seat_list = []
    for b in taken:
        if b.seat_number:
            for s in b.seat_number.split(','):
                s = s.strip()
                if s:
                    seat_list.append(s)

    return jsonify({"booked_seats": seat_list})

# POST /api/bookings/select-seat — assign a seat to a booking
@booking_bp.route("/select-seat", methods=["POST"])
@jwt_required()
def select_seat():
    data       = request.get_json()
    booking_id = data.get("booking_id")
    seat       = data.get("seat_number")

    if not booking_id or not seat:
        return jsonify({"error": "Missing booking_id or seat_number"}), 400

    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    # Verify ownership
    current_user_id = int(get_jwt_identity())
    if booking.user_id != current_user_id:
        return jsonify({"error": "Access denied"}), 403

    # Check seat conflict
    conflict = Booking.query.filter(
        Booking.schedule_id == booking.schedule_id,
        Booking.seat_number == seat,
        Booking.status.in_(["locked", "pending", "confirmed"]),
        Booking.id != booking_id
    ).first()
    if conflict:
        return jsonify({"error": "Seat already taken, please choose another"}), 409

    # seat_number may be single "A1" or comma-separated "A1, A2, A3"
    booking.seat_number = seat
    booking.status = "pending"
    db.session.commit()

    # Emit real-time update for each seat
    try:
        from sockets.seat_socket import emit_seat_update
        for s in seat.split(','):
            s = s.strip()
            if s:
                emit_seat_update(booking.schedule_id, s, "locked")
    except Exception:
        pass

    return jsonify({
        "message": "Seat assigned",
        "seat":    seat,
        "booking": {
            "id":           booking.id,
            "booking_code": booking.booking_code,
            "seat_number":  booking.seat_number,
            "status":       booking.status
        }
    }), 200

# POST /api/bookings/cancel/<code>
@booking_bp.route("/cancel/<code>", methods=["POST"])
@jwt_required()
def cancel(code):
    booking = Booking.query.filter_by(booking_code=code).first()
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    current_user_id = int(get_jwt_identity())
    claims = get_jwt()
    if booking.user_id != current_user_id and claims.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403

    if booking.status == "confirmed":
        return jsonify({"error": "Cannot cancel a confirmed booking"}), 400

    # Release seat back
    schedule = Schedule.query.get(booking.schedule_id)
    if schedule and booking.passenger_count:
        schedule.seats_available += booking.passenger_count

    booking.status = "cancelled"
    db.session.commit()

    try:
        from sockets.seat_socket import emit_seat_update
        if booking.seat_number:
            emit_seat_update(booking.schedule_id, booking.seat_number, "available")
    except Exception:
        pass

    return jsonify({"message": "Booking cancelled successfully"})

# GET /api/bookings/code/<booking_code> — fetch full booking by code (for ticket page)
@booking_bp.route("/code/<code>", methods=["GET"])
@jwt_required()
def get_by_code(code):
    from services.booking_service import _serialize_booking
    booking = Booking.query.filter_by(booking_code=code.upper()).first()
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    current_user_id = int(get_jwt_identity())
    claims = get_jwt()
    if booking.user_id != current_user_id and claims.get("role") != "admin":
        return jsonify({"error": "Access denied"}), 403
    return jsonify({"booking": _serialize_booking(booking)}), 200
