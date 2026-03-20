from models.booking import Booking
from models.user import User
from models.schedule import Schedule
from models.bus import Bus
from extensions import db


def get_dashboard_stats():
    total_users     = User.query.count()
    total_bookings  = Booking.query.count()
    confirmed       = Booking.query.filter_by(status="confirmed").count()
    cancelled       = Booking.query.filter_by(status="cancelled").count()
    pending         = Booking.query.filter_by(status="pending").count()
    total_revenue   = db.session.query(db.func.sum(Booking.amount)).filter_by(status="confirmed").scalar() or 0
    total_buses     = Bus.query.count()
    total_schedules = Schedule.query.filter_by(is_active=True).count()

    return {
        "total_users":     total_users,
        "total_bookings":  total_bookings,
        "confirmed":       confirmed,
        "cancelled":       cancelled,
        "pending":         pending,
        "total_revenue":   float(total_revenue),
        "total_buses":     total_buses,
        "total_schedules": total_schedules
    }


def get_all_users():
    users = User.query.all()
    result = []
    for u in users:
        booking_count = Booking.query.filter_by(user_id=u.id).count()
        # Build display name — support both first_name/last_name and username fields
        username = f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email
        result.append({
            "id":            u.id,
            "username":      username,
            "first_name":    u.first_name or "",
            "last_name":     u.last_name or "",
            "email":         u.email,
            "phone":         u.phone or "—",
            "role":          u.role,
            "booking_count": booking_count
        })
    return result


def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return {"error": "User not found"}, 404
    if user.role == "admin":
        return {"error": "Cannot delete an admin account"}, 403
    Booking.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    return {"message": "User deleted"}, 200


def get_all_buses():
    buses = Bus.query.all()
    return [{
        "id":           b.id,
        "bus_name":     b.name,       # expose as bus_name so frontend sees it
        "name":         b.name,
        "plate_number": b.plate_number,
        "total_seats":  b.total_seats,
        "seat_layout":  b.seat_layout,
        "is_active":    True          # Bus model has no is_active yet — default True
    } for b in buses]


def create_bus(data):
    # Accept both "name" and "bus_name"
    name         = data.get("name") or data.get("bus_name")
    plate_number = data.get("plate_number")
    total_seats  = data.get("total_seats", 40)
    seat_layout  = data.get("seat_layout", "4-column")

    if not name or not plate_number:
        return {"error": "Bus name and plate number are required"}, 400

    if int(total_seats) < 1:
        return {"error": "Total seats must be at least 1"}, 400

    existing = Bus.query.filter_by(plate_number=plate_number.strip()).first()
    if existing:
        return {"error": f"Plate number '{plate_number}' is already registered"}, 400

    bus = Bus(
        name=name.strip(),
        plate_number=plate_number.strip(),
        total_seats=int(total_seats),
        seat_layout=seat_layout
    )
    db.session.add(bus)
    db.session.commit()
    return {"message": "Bus added successfully", "id": bus.id}, 201


def delete_bus(bus_id):
    bus = Bus.query.get(bus_id)
    if not bus:
        return {"error": "Bus not found"}, 404
    db.session.delete(bus)
    db.session.commit()
    return {"message": "Bus deleted"}, 200
