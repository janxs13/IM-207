import uuid
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, update

from extensions import db
from models.booking import Booking
from models.schedule import Schedule
from models.bus import Bus

logger = logging.getLogger(__name__)


def create_booking(data):
    user_id         = data.get("user_id")
    schedule_id     = data.get("schedule_id")
    travel_date     = data.get("travel_date")
    passenger_count = int(data.get("passenger_count", 1))
    passenger_type  = (data.get("passenger_type") or "regular").lower()
    id_number       = (data.get("id_number") or "").strip()
    id_type         = (data.get("id_type") or "").strip()

    # ── Validate inputs ──────────────────────────────────
    if not all([user_id, schedule_id, travel_date]):
        return {"error": "user_id, schedule_id and travel_date are required"}, 400
    if passenger_count < 1:
        return {"error": "Passenger count must be at least 1"}, 400
    if passenger_count > 10:
        return {"error": "Cannot book more than 10 seats at once"}, 400

    # Validate passenger_type
    valid_types = {"regular", "senior", "pwd", "student"}
    if passenger_type not in valid_types:
        passenger_type = "regular"

    # Senior / PWD require ID
    if passenger_type in ("senior", "pwd") and not id_number:
        return {
            "error": f"ID number is required for {passenger_type.upper()} discount. "
                     f"Please provide your {'OSCA Card' if passenger_type == 'senior' else 'PWD ID'} number."
        }, 400

    try:
        booking_dt = datetime.strptime(str(travel_date), "%Y-%m-%d")
        if booking_dt.date() < datetime.utcnow().date():
            return {"error": "Travel date cannot be in the past"}, 400
    except ValueError:
        return {"error": "Invalid travel_date format. Use YYYY-MM-DD"}, 400

    sid      = int(schedule_id)
    booking  = None
    schedule = None

    try:
        # ── Double-check: count confirmed/locked bookings vs total seats ─
        sched_check = db.session.execute(
            select(Schedule).where(Schedule.id == sid)
        ).scalar_one_or_none()
        if sched_check:
            confirmed_count = db.session.execute(
                select(db.func.sum(Booking.passenger_count)).where(
                    Booking.schedule_id == sid,
                    Booking.status.in_(["locked", "confirmed"]),
                    Booking.deleted_at.is_(None),
                )
            ).scalar() or 0
            bus_cap = sched_check.seats_available + confirmed_count  # total seats
            if confirmed_count + passenger_count > bus_cap:
                db.session.rollback()
                return {"error": "No seats available for this schedule."}, 400

        dec = db.session.execute(
            update(Schedule)
            .where(
                Schedule.id == sid,
                Schedule.is_active.is_(True),
                Schedule.seats_available >= passenger_count,
            )
            .values(seats_available=Schedule.seats_available - passenger_count)
        )
        if dec.rowcount != 1:
            db.session.rollback()
            row = db.session.execute(
                select(Schedule).where(Schedule.id == sid)
            ).scalar_one_or_none()
            if not row:
                return {"error": "Schedule not found"}, 404
            if not row.is_active:
                return {"error": "This schedule is no longer available"}, 400
            return {"error": f"Not enough seats. Only {row.seats_available} available."}, 400

        schedule = db.session.execute(
            select(Schedule).where(Schedule.id == sid)
        ).scalar_one()

        # ── Generate unique booking code ─────────────────
        for _ in range(32):
            booking_code = str(uuid.uuid4())[:8].upper()
            taken = db.session.execute(
                select(Booking.id).where(Booking.booking_code == booking_code)
            ).first()
            if not taken:
                break
        else:
            db.session.rollback()
            return {"error": "Failed to create booking. Please try again."}, 500

        # ── Apply discount (RA 9994 / RA 7277) ───────────
        from services.fare_service import apply_discount_to_fare
        base_fare       = schedule.fare * passenger_count
        fare_result     = apply_discount_to_fare(base_fare, passenger_type)
        final_amount    = fare_result["final_fare"]
        discount_amount = fare_result["discount_amount"]

        booking = Booking(
            user_id         = int(user_id),
            schedule_id     = sid,
            travel_date     = str(travel_date),
            booking_code    = booking_code,
            status          = "pending",
            amount          = final_amount,
            original_amount = base_fare,
            passenger_count = passenger_count,
            passenger_type  = passenger_type,
            discount_type   = fare_result["discount_type"],
            discount_amount = discount_amount,
            id_number       = id_number or None,
            id_type         = id_type or None,
            locked_until    = datetime.utcnow() + timedelta(minutes=10),
        )
        db.session.add(booking)
        db.session.commit()

    except Exception:
        db.session.rollback()
        logger.exception("create_booking failed")
        return {"error": "Failed to create booking. Please try again."}, 500

    bus = Bus.query.get(schedule.bus_id) if schedule.bus_id else None

    return {
        "message": "Booking created",
        "booking": {
            "id":             booking.id,
            "booking_code":   booking.booking_code,
            "route":          schedule.route,
            "departure_time": schedule.departure_time or "",
            "arrival_time":   schedule.arrival_time or "",
            "travel_date":    booking.travel_date,
            "seat_number":    booking.seat_number,
            "amount":         booking.amount,
            "price":          booking.amount,
            "original_amount": booking.original_amount,
            "discount_type":  booking.discount_type,
            "discount_amount": booking.discount_amount,
            "passenger_type": booking.passenger_type,
            "fare_per_seat":  schedule.fare,
            "passenger_count": booking.passenger_count,
            "status":         booking.status,
            "schedule_id":    booking.schedule_id,
            "locked_until":   booking.locked_until.isoformat() + "Z" if booking.locked_until else None,
            "bus_name":       bus.name if bus else None,
            "bus_plate":      bus.plate_number if bus else None,
            "seat_layout":    bus.seat_layout if bus else "4-column",
            "total_seats":    bus.total_seats if bus else 40,
            "bus_image_url":  (f"/static/bus_images/{bus.image_filename}"
                               if bus and bus.image_filename else None),
        },
    }, 201


def cancel_booking(booking_code: str, user_id: int, is_admin: bool = False) -> tuple:
    """
    Cancel a booking with Philippine refund policy:
      24+ hours before departure → 100% refund
      4-24 hours before departure → 75% refund
      <4 hours before departure  → No refund
    """
    from models.user import User

    booking = Booking.query.filter_by(
        booking_code=booking_code.upper()
    ).first()
    if not booking:
        return {"error": "Booking not found"}, 404
    if not is_admin and int(booking.user_id) != int(user_id):
        return {"error": "Access denied"}, 403
    if booking.status == "cancelled":
        return {"error": "Booking is already cancelled"}, 400
    if booking.status == "confirmed" and not is_admin:
        return {"error": "Paid bookings require admin approval to cancel"}, 400

    # ── Compute refund based on departure time ────────────
    schedule = Schedule.query.get(booking.schedule_id)
    refund_amount = 0.0
    refund_status = "no_refund"
    hours_until   = None

    if schedule and schedule.departure_time and "T" in schedule.departure_time:
        try:
            dep_dt      = datetime.strptime(schedule.departure_time[:16], "%Y-%m-%dT%H:%M")
            hours_until = (dep_dt - datetime.now()).total_seconds() / 3600
            if hours_until >= 24:
                refund_amount = booking.amount * 1.00
                refund_status = "full_refund"
            elif hours_until >= 4:
                refund_amount = booking.amount * 0.75
                refund_status = "partial_refund_75pct"
            else:
                refund_amount = 0.0
                refund_status = "no_refund"
        except ValueError:
            pass

    # ── Restore seats ─────────────────────────────────────
    if schedule and booking.passenger_count:
        schedule.seats_available += booking.passenger_count

    seats_cancelled = [s.strip() for s in (booking.seat_number or "").split(",") if s.strip()]
    booking.status = "cancelled"

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return {"error": "Failed to cancel booking. Please try again."}, 500

    # ── Socket update ────────────────────────────────────
    try:
        from sockets.seat_socket import emit_seat_update
        for s in seats_cancelled:
            emit_seat_update(booking.schedule_id, s, "available")
    except Exception:
        pass

    # ── SMS notification ─────────────────────────────────
    try:
        user = User.query.get(booking.user_id)
        if user and user.phone:
            from utils.sms import send_booking_cancelled_sms
            send_booking_cancelled_sms(user.phone, booking_code, schedule.route if schedule else "")
    except Exception:
        pass

    return {
        "message":       "Booking cancelled successfully.",
        "refund_status": refund_status,
        "refund_amount": round(refund_amount, 2),
        "note":          (
            "Full refund" if refund_status == "full_refund"
            else "75% refund (cancelled within 24 hours)"
            if "75" in refund_status
            else "No refund (cancelled within 4 hours of departure)"
        ),
    }, 200


def get_all_bookings():
    bookings = Booking.query.filter(
        Booking.deleted_at.is_(None)
    ).order_by(Booking.created_at.desc()).all()
    return [_serialize_booking(b) for b in bookings]


def get_user_bookings(user_id):
    bookings = (
        Booking.query
        .filter_by(user_id=int(user_id))
        .filter(Booking.deleted_at.is_(None))
        .order_by(Booking.created_at.desc())
        .all()
    )
    return [_serialize_booking(b) for b in bookings]


def _serialize_booking(b):
    from models.user import User
    schedule = Schedule.query.get(b.schedule_id)
    bus      = Bus.query.get(schedule.bus_id) if schedule and schedule.bus_id else None
    user     = User.query.get(b.user_id)
    pax_name = (
        f"{user.first_name or ''} {user.last_name or ''}".strip()
        if user and (user.first_name or user.last_name)
        else (user.email if user else "—")
    )
    return {
        "id":              b.id,
        "booking_code":    b.booking_code,
        "route":           schedule.route if schedule else "—",
        "passenger":       pax_name,
        "email":           user.email if user else "—",
        "phone":           user.phone if user else "—",
        "travel_date":     b.travel_date,
        "time":            (schedule.departure_time or "—").split("T")[-1] if schedule else "—",
        "departure_time":  schedule.departure_time if schedule else "—",
        "arrival_time":    schedule.arrival_time if schedule else "—",
        "seat_number":     b.seat_number or "—",
        "fare":            b.amount,
        "price":           b.amount,
        "amount":          b.amount,
        "original_amount": b.original_amount,
        "discount_type":   b.discount_type,
        "discount_amount": b.discount_amount or 0,
        "passenger_type":  b.passenger_type or "regular",
        "id_number":       b.id_number,
        "id_type":         b.id_type,
        "fare_per_seat":   schedule.fare if schedule else 0,
        "passenger_count": b.passenger_count or 1,
        "status":          b.status,
        "schedule_id":     b.schedule_id,
        "locked_until":    b.locked_until.isoformat() + "Z" if b.locked_until else None,
        "bus_name":        bus.name if bus else None,
        "bus_plate":       bus.plate_number if bus else None,
        "seat_layout":     bus.seat_layout if bus else "4-column",
        "total_seats":     bus.total_seats if bus else 40,
        "bus_image_url":   (f"/static/bus_images/{bus.image_filename}"
                            if bus and bus.image_filename else None),
        "payment_method":  b.payment_method or "—",
        "reference_no":    b.reference_no or "—",
        "trip_status":     schedule.trip_status if schedule else "scheduled",
    }
