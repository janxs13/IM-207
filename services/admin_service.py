from models.booking import Booking
from models.user import User
from models.schedule import Schedule
from models.bus import Bus
from extensions import db


def get_dashboard_stats():
    total_users     = User.query.filter_by(role="user").count()
    total_bookings  = Booking.query.filter(Booking.deleted_at.is_(None)).count()
    confirmed       = Booking.query.filter_by(status="confirmed").filter(Booking.deleted_at.is_(None)).count()
    cancelled       = Booking.query.filter_by(status="cancelled").filter(Booking.deleted_at.is_(None)).count()
    pending         = Booking.query.filter_by(status="pending").filter(Booking.deleted_at.is_(None)).count()
    total_revenue   = db.session.query(db.func.sum(Booking.amount)).filter(
        Booking.status == "confirmed", Booking.deleted_at.is_(None)
    ).scalar() or 0
    total_buses     = Bus.query.filter_by(is_active=True).count()
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
    users = User.query.filter_by(role="user").all()
    result = []
    for u in users:
        booking_count = Booking.query.filter(
            Booking.user_id == u.id, Booking.deleted_at.is_(None)
        ).count()
        username = f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email
        result.append({
            "id":            u.id,
            "username":      username,
            "first_name":    u.first_name or "",
            "last_name":     u.last_name  or "",
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

    from models.payment import Payment
    bookings = Booking.query.filter_by(user_id=user_id).all()
    for b in bookings:
        Payment.query.filter_by(booking_id=b.id).delete()
    Booking.query.filter_by(user_id=user_id).delete()

    db.session.delete(user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return {"error": "Failed to delete user"}, 500
    return {"message": "User deleted"}, 200


def get_all_buses():
    buses = Bus.query.all()
    return [{
        "id":           b.id,
        "bus_name":     b.name,
        "name":         b.name,
        "plate_number": b.plate_number,
        "total_seats":  b.total_seats,
        "seat_layout":  b.seat_layout,
        "is_active":    b.is_active
    } for b in buses]


def create_bus(data):
    name         = (data.get("name") or data.get("bus_name") or "").strip()
    plate_number = (data.get("plate_number") or "").strip()
    total_seats  = data.get("total_seats", 40)
    seat_layout  = data.get("seat_layout", "4-column")

    if not name or not plate_number:
        return {"error": "Bus name and plate number are required"}, 400
    if int(total_seats) < 1 or int(total_seats) > 100:
        return {"error": "Total seats must be between 1 and 100"}, 400

    existing = Bus.query.filter_by(plate_number=plate_number).first()
    if existing:
        return {"error": f"Plate number '{plate_number}' is already registered"}, 400

    bus = Bus(
        name         = name,
        plate_number = plate_number,
        total_seats  = int(total_seats),
        seat_layout  = seat_layout,
        is_active    = True
    )
    db.session.add(bus)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return {"error": "Failed to create bus"}, 500
    return {"message": "Bus added successfully", "id": bus.id}, 201


def delete_bus(bus_id):
    bus = Bus.query.get(bus_id)
    if not bus:
        return {"error": "Bus not found"}, 404
    linked = Schedule.query.filter_by(bus_id=bus_id).count()
    if linked > 0:
        return {"error": f"Cannot delete bus: {linked} schedule(s) are still assigned to it. Remove or reassign them first."}, 400
    db.session.delete(bus)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return {"error": "Failed to delete bus"}, 500
    return {"message": "Bus deleted"}, 200
