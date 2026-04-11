from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select

from services.booking_service import create_booking, get_all_bookings, get_user_bookings
from models.booking import Booking
from models.schedule import Schedule
from extensions import db
from utils.decorators import current_user_is_admin

booking_bp = Blueprint("booking", __name__)


class _FlowAbort(Exception):
    __slots__ = ("payload", "http_status")

    def __init__(self, payload, http_status):
        self.payload = payload
        self.http_status = http_status


def _seat_tokens(seat_csv):
    return {x.strip() for x in (seat_csv or "").split(",") if x.strip()}


# ── POST /api/bookings/ ───────────────────────────────────────────
@booking_bp.route("/", methods=["POST"])
@jwt_required()
def book():
    data = request.get_json() or {}
    data["user_id"] = int(get_jwt_identity())
    response, status = create_booking(data)
    return jsonify(response), status


# ── GET /api/bookings/ — admin ────────────────────────────────────
@booking_bp.route("/", methods=["GET"])
@jwt_required()
def all_bookings():
    if not current_user_is_admin():
        return jsonify({"error": "Admin access required"}), 403
    return jsonify(get_all_bookings())


# ── GET /api/bookings/user/<id> ───────────────────────────────────
@booking_bp.route("/user/<int:user_id>", methods=["GET"])
@jwt_required()
def user_bookings(user_id):
    current_user_id = int(get_jwt_identity())
    if current_user_id != user_id and not current_user_is_admin():
        return jsonify({"error": "Access denied"}), 403
    return jsonify(get_user_bookings(user_id))


# ── GET /api/bookings/seats/<schedule_id> ────────────────────────
@booking_bp.route("/seats/<int:schedule_id>", methods=["GET"])
def booked_seats(schedule_id):
    taken = Booking.query.filter(
        Booking.schedule_id == schedule_id,
        Booking.status.in_(["locked", "pending", "confirmed"])
    ).all()
    seat_list = []
    for b in taken:
        if b.seat_number:
            for s in b.seat_number.split(","):
                s = s.strip()
                if s:
                    seat_list.append(s)
    return jsonify({"booked_seats": seat_list})


# ── POST /api/bookings/select-seat ───────────────────────────────
@booking_bp.route("/select-seat", methods=["POST"])
@jwt_required()
def select_seat():
    data = request.get_json() or {}
    booking_id = data.get("booking_id")
    seat = data.get("seat_number")

    if not booking_id or not seat:
        return jsonify({"error": "Missing booking_id or seat_number"}), 400

    try:
        bid = int(booking_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid booking_id"}), 400

    current_user_id = int(get_jwt_identity())
    seats_requested = [s.strip() for s in seat.split(",") if s.strip()]

    try:
        booking = db.session.execute(
            select(Booking).where(Booking.id == bid).with_for_update()
        ).scalar_one_or_none()
        if not booking:
            raise _FlowAbort({"error": "Booking not found"}, 404)
        if int(booking.user_id) != current_user_id:
            raise _FlowAbort({"error": "Access denied"}, 403)

        db.session.execute(
            select(Schedule.id)
            .where(Schedule.id == booking.schedule_id)
            .with_for_update()
        ).scalar_one()

        rivals = db.session.scalars(
            select(Booking).where(
                Booking.schedule_id == booking.schedule_id,
                Booking.status.in_(["locked", "pending", "confirmed"]),
                Booking.id != bid,
            )
        ).all()
        for s in seats_requested:
            for other in rivals:
                if s in _seat_tokens(other.seat_number):
                    raise _FlowAbort(
                        {
                            "error": f"Seat {s} is already taken. Please choose another."
                        },
                        409,
                    )

        booking.seat_number = seat
        booking.status = "pending"
        db.session.commit()
    except _FlowAbort as e:
        db.session.rollback()
        return jsonify(e.payload), e.http_status
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to assign seat. Please try again."}), 500

    try:
        from sockets.seat_socket import emit_seat_update

        for s in seats_requested:
            emit_seat_update(booking.schedule_id, s, "locked")
    except Exception:
        pass

    return (
        jsonify(
            {
                "message": "Seat assigned",
                "seat": seat,
                "booking": {
                    "id": booking.id,
                    "booking_code": booking.booking_code,
                    "seat_number": booking.seat_number,
                    "status": booking.status,
                },
            }
        ),
        200,
    )


# ── POST /api/bookings/cancel/<code> ─────────────────────────────
@booking_bp.route("/cancel/<code>", methods=["POST"])
@jwt_required()
def cancel(code):
    booking = Booking.query.filter_by(booking_code=code.strip().upper()).first()
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    current_user_id = int(get_jwt_identity())
    if booking.user_id != current_user_id and not current_user_is_admin():
        return jsonify({"error": "Access denied"}), 403

    if booking.status == "confirmed":
        return jsonify({"error": "Cannot cancel a confirmed booking"}), 400

    schedule = Schedule.query.get(booking.schedule_id)
    if schedule and booking.passenger_count:
        schedule.seats_available += booking.passenger_count

    seats_cancelled = [s.strip() for s in (booking.seat_number or "").split(",") if s.strip()]
    booking.status = "cancelled"

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to cancel booking. Please try again."}), 500

    try:
        from sockets.seat_socket import emit_seat_update
        for s in seats_cancelled:
            emit_seat_update(booking.schedule_id, s, "available")
    except Exception:
        pass

    return jsonify({"message": "Booking cancelled successfully"})


# ── GET /api/bookings/code/<booking_code> ────────────────────────
@booking_bp.route("/code/<code>", methods=["GET"])
@jwt_required()
def get_by_code(code):
    from services.booking_service import _serialize_booking
    booking = Booking.query.filter_by(booking_code=code.upper()).first()
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    current_user_id = int(get_jwt_identity())
    if booking.user_id != current_user_id and not current_user_is_admin():
        return jsonify({"error": "Access denied"}), 403
    return jsonify({"booking": _serialize_booking(booking)}), 200
