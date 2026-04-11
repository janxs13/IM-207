from models.schedule import Schedule
from models.bus import Bus
from extensions import db


def create_schedule(data):
    route           = (data.get("route") or "").strip()
    departure_time  = data.get("departure_time")
    arrival_time    = data.get("arrival_time", "")
    fare            = data.get("fare")
    seats_available = data.get("seats_available", 40)
    bus_id          = data.get("bus_id") or None

    if not all([route, departure_time, fare]):
        return {"error": "route, departure_time, and fare are required"}, 400
    if float(fare) < 0:
        return {"error": "Fare cannot be negative"}, 400
    if len(route) > 200:
        return {"error": "Route name too long (max 200 characters)"}, 400

    # Pull seat count from bus if not explicitly provided
    if bus_id:
        bus = Bus.query.get(int(bus_id))
        if not bus:
            return {"error": "Bus not found"}, 404
        if not bus.is_active:
            return {"error": "Cannot assign an inactive bus to a schedule"}, 400
        if not data.get("seats_available"):
            seats_available = bus.total_seats

    schedule = Schedule(
        route           = route,
        departure_time  = departure_time,
        arrival_time    = arrival_time,
        fare            = float(fare),
        seats_available = int(seats_available),
        bus_id          = int(bus_id) if bus_id else None,
        is_active       = True
    )
    db.session.add(schedule)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return {"error": "Failed to create schedule. Please try again."}, 500
    return {"message": "Schedule created", "id": schedule.id}, 201


def get_schedules():
    schedules = Schedule.query.filter_by(is_active=True).all()
    result = []
    for s in schedules:
        bus = Bus.query.get(s.bus_id) if s.bus_id else None
        result.append({
            "id":              s.id,
            "route":           s.route,
            "departure_time":  (s.departure_time or "").split("T")[-1] if s.departure_time else "",
            "arrival_time":    s.arrival_time or "",
            "fare":            s.fare,
            "price":           s.fare,
            "seats_available": s.seats_available,
            "available_seats": s.seats_available,
            "is_active":       s.is_active,
            "bus_id":          s.bus_id,
            "bus_name":        bus.name         if bus else None,
            "bus_plate":       bus.plate_number if bus else None,
            "seat_layout":     bus.seat_layout  if bus else "4-column",
            "total_seats":     bus.total_seats  if bus else 40
        })
    return result


def delete_schedule(schedule_id):
    from models.booking import Booking
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return {"error": "Schedule not found"}, 404

    # Prevent deletion if active (non-expired/non-cancelled) bookings exist
    active_bookings = Booking.query.filter(
        Booking.schedule_id == schedule_id,
        Booking.status.in_(["pending", "confirmed"]),
        Booking.deleted_at.is_(None)
    ).count()
    if active_bookings > 0:
        return {
            "error": f"Cannot delete: {active_bookings} active booking(s) on this schedule. Cancel them first."
        }, 400

    db.session.delete(schedule)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return {"error": "Failed to delete schedule"}, 500
    return {"message": "Schedule deleted"}, 200
