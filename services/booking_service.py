import uuid
from datetime import datetime, timedelta
from extensions import db
from models.booking import Booking
from models.schedule import Schedule
from models.bus import Bus


def create_booking(data):
    user_id         = data.get("user_id")
    schedule_id     = data.get("schedule_id")
    travel_date     = data.get("travel_date")
    passenger_count = int(data.get("passenger_count", 1))

    if not all([user_id, schedule_id, travel_date]):
        return {"error": "user_id, schedule_id and travel_date are required"}, 400
    if passenger_count < 1:
        return {"error": "Passenger count must be at least 1"}, 400

    try:
        booking_dt = datetime.strptime(str(travel_date), "%Y-%m-%d")
        if booking_dt.date() < datetime.utcnow().date():
            return {"error": "Travel date cannot be in the past"}, 400
    except ValueError:
        return {"error": "Invalid travel_date format. Use YYYY-MM-DD"}, 400

    schedule = Schedule.query.get(int(schedule_id))
    if not schedule:
        return {"error": "Schedule not found"}, 404
    if schedule.seats_available < passenger_count:
        return {"error": f"Not enough seats. Only {schedule.seats_available} available."}, 400

    booking_code = str(uuid.uuid4())[:8].upper()
    booking = Booking(
        user_id         = int(user_id),
        schedule_id     = int(schedule_id),
        travel_date     = str(travel_date),
        booking_code    = booking_code,
        status          = "pending",
        amount          = schedule.fare * passenger_count,
        passenger_count = passenger_count,
        locked_until    = datetime.utcnow() + timedelta(hours=2)
    )
    schedule.seats_available -= passenger_count
    db.session.add(booking)
    db.session.commit()

    bus = Bus.query.get(schedule.bus_id) if schedule.bus_id else None

    return {
        "message": "Booking created",
        "booking": {
            "id":              booking.id,
            "booking_code":    booking.booking_code,
            "route":           schedule.route,
            "departure_time":  (schedule.departure_time or "").split("T")[-1] if schedule.departure_time else "",
            "travel_date":     booking.travel_date,
            "seat_number":     booking.seat_number,
            "amount":          booking.amount,
            "price":           booking.amount,
            "fare_per_seat":   schedule.fare,
            "passenger_count": booking.passenger_count,
            "status":          booking.status,
            "schedule_id":     booking.schedule_id,
            "bus_name":        bus.name if bus else None,
            "bus_plate":       bus.plate_number if bus else None,
            "seat_layout":     bus.seat_layout if bus else "4-column",
            "total_seats":     bus.total_seats if bus else 40,
        }
    }, 201


def get_all_bookings():
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return [_serialize_booking(b) for b in bookings]


def get_user_bookings(user_id):
    bookings = Booking.query.filter_by(user_id=int(user_id)).order_by(Booking.created_at.desc()).all()
    return [_serialize_booking(b) for b in bookings]


def _serialize_booking(b):
    schedule = Schedule.query.get(b.schedule_id)
    bus      = Bus.query.get(schedule.bus_id) if schedule and schedule.bus_id else None
    return {
        "id":              b.id,
        "booking_code":    b.booking_code,
        "route":           schedule.route           if schedule else "—",
        "travel_date":     b.travel_date,
        "time":            (schedule.departure_time or "—").split("T")[-1] if schedule else "—",
        "departure_time":  (schedule.departure_time or "—").split("T")[-1] if schedule else "—",
        "arrival_time":    schedule.arrival_time    if schedule else "—",
        "seat_number":     b.seat_number or "—",
        "fare":            b.amount,
        "price":           b.amount,
        "amount":          b.amount,
        "fare_per_seat":   schedule.fare            if schedule else 0,
        "passenger_count": b.passenger_count or 1,
        "status":          b.status,
        "schedule_id":     b.schedule_id,
        "bus_name":        bus.name         if bus else None,
        "bus_plate":       bus.plate_number if bus else None,
        "seat_layout":     bus.seat_layout  if bus else "4-column",
        "total_seats":     bus.total_seats  if bus else 40,
        "payment_method":  b.payment_method or "—",
        "reference_no":    b.reference_no   or "—",
    }
