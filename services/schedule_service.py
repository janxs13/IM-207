from models.schedule import Schedule
from models.bus import Bus
from extensions import db


def create_schedule(data):
    route           = data.get("route")
    departure_time  = data.get("departure_time")
    arrival_time    = data.get("arrival_time", "")
    fare            = data.get("fare")
    seats_available = data.get("seats_available", 40)
    bus_id          = data.get("bus_id") or None

    if not all([route, departure_time, fare]):
        return {"error": "route, departure_time, and fare are required"}, 400

    # If bus_id given, pull total_seats from that bus
    if bus_id:
        bus = Bus.query.get(int(bus_id))
        if bus and not data.get("seats_available"):
            seats_available = bus.total_seats

    schedule = Schedule(
        route=route.strip(),
        departure_time=departure_time,
        arrival_time=arrival_time,
        fare=float(fare),
        seats_available=int(seats_available),
        bus_id=int(bus_id) if bus_id else None
    )
    db.session.add(schedule)
    db.session.commit()
    return {"message": "Schedule created", "id": schedule.id}, 201


def get_schedules():
    schedules = Schedule.query.filter_by(is_active=True).all()
    result = []
    for s in schedules:
        bus = Bus.query.get(s.bus_id) if s.bus_id else None
        result.append({
            "id":              s.id,
            "route":           s.route,
            "departure_time":  s.departure_time,
            "arrival_time":    s.arrival_time,
            "fare":            s.fare,
            "price":           s.fare,          # alias — some frontend uses "price"
            "seats_available": s.seats_available,
            "available_seats": s.seats_available, # alias
            "is_active":       s.is_active,
            "bus_id":          s.bus_id,
            "bus_name":        bus.name if bus else None,
            "total_seats":     bus.total_seats if bus else 40
        })
    return result


def delete_schedule(schedule_id):
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return {"error": "Schedule not found"}, 404
    db.session.delete(schedule)
    db.session.commit()
    return {"message": "Schedule deleted"}, 200
