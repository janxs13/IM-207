from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from services.admin_service import (
    get_dashboard_stats, get_all_users, delete_user,
    get_all_buses, create_bus, delete_bus
)
from models.booking import Booking
from models.schedule import Schedule
from models.user import User
from models.bus import Bus
from extensions import db
from datetime import datetime, timedelta

admin_bp = Blueprint("admin", __name__)

def admin_required():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    return None

@admin_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    err = admin_required()
    if err: return err
    return jsonify(get_dashboard_stats())

# ── Users ────────────────────────────────────────────────────────
@admin_bp.route("/users", methods=["GET"])
@jwt_required()
def users():
    err = admin_required()
    if err: return err
    return jsonify({"users": get_all_users()})

@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def remove_user(user_id):
    err = admin_required()
    if err: return err
    result, status = delete_user(user_id)
    return jsonify(result), status

# ── Buses ────────────────────────────────────────────────────────
@admin_bp.route("/buses", methods=["GET"])
@jwt_required()
def list_buses():
    err = admin_required()
    if err: return err
    return jsonify({"buses": get_all_buses()})

@admin_bp.route("/buses", methods=["POST"])
@jwt_required()
def add_bus():
    err = admin_required()
    if err: return err
    data = request.get_json()
    if not data.get("name") and data.get("bus_name"):
        data["name"] = data["bus_name"]
    result, status = create_bus(data)
    return jsonify(result), status

@admin_bp.route("/buses/<int:bus_id>", methods=["PUT"])
@jwt_required()
def edit_bus(bus_id):
    err = admin_required()
    if err: return err
    bus = Bus.query.get(bus_id)
    if not bus:
        return jsonify({"error": "Bus not found"}), 404
    data = request.get_json() or {}
    if data.get("name"):         bus.name         = data["name"].strip()
    if data.get("bus_name"):     bus.name         = data["bus_name"].strip()
    if data.get("plate_number"): bus.plate_number = data["plate_number"].strip()
    if data.get("total_seats"):  bus.total_seats  = int(data["total_seats"])
    if data.get("seat_layout"):  bus.seat_layout  = data["seat_layout"]
    db.session.commit()
    return jsonify({"message": "Bus updated"}), 200

@admin_bp.route("/buses/<int:bus_id>", methods=["DELETE"])
@jwt_required()
def remove_bus(bus_id):
    err = admin_required()
    if err: return err
    result, status = delete_bus(bus_id)
    return jsonify(result), status

# ── Feature 8: All bookings with filter (admin report) ───────────
@admin_bp.route("/bookings", methods=["GET"])
@jwt_required()
def all_bookings_admin():
    err = admin_required()
    if err: return err

    status_filter = request.args.get("status")       # confirmed/pending/cancelled
    from_date     = request.args.get("from_date")
    to_date       = request.args.get("to_date")

    query = Booking.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if from_date:
        query = query.filter(Booking.travel_date >= from_date)
    if to_date:
        query = query.filter(Booking.travel_date <= to_date)

    bookings = query.order_by(Booking.created_at.desc()).all()
    result = []
    for b in bookings:
        sched = Schedule.query.get(b.schedule_id)
        usr   = User.query.get(b.user_id)
        from models.bus import Bus as BusModel
        bus = BusModel.query.get(sched.bus_id) if sched and sched.bus_id else None
        result.append({
            "id":           b.id,
            "booking_code": b.booking_code,
            "passenger":    f"{usr.first_name} {usr.last_name}".strip() if usr else "—",
            "email":        usr.email if usr else "—",
            "route":        sched.route if sched else "—",
            "travel_date":  b.travel_date,
            "departure":    (sched.departure_time or "—").split("T")[-1] if sched else "—",
            "seat_number":  b.seat_number or "—",
            "passenger_count": b.passenger_count or 1,
            "amount":       b.amount or 0,
            "status":       b.status,
            "payment_method": b.payment_method or "—",
            "bus_name":     bus.name if bus else "—",
            "bus_plate":    bus.plate_number if bus else "—",
        })
    return jsonify({"bookings": result, "total": len(result)})


# ── Admin: update booking status ────────────────────────────────
@admin_bp.route("/bookings/<int:booking_id>/status", methods=["PUT"])
@jwt_required()
def update_booking_status(booking_id):
    err = admin_required()
    if err: return err

    data       = request.get_json() or {}
    new_status = (data.get("status") or "").strip().lower()

    allowed = {"confirmed", "pending", "cancelled"}
    if new_status not in allowed:
        return jsonify({"error": f"Invalid status. Must be one of: {', '.join(sorted(allowed))}"}), 400

    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    old_status = booking.status

    # When cancelling: restore seats back to the schedule
    if new_status == "cancelled" and old_status != "cancelled":
        schedule = Schedule.query.get(booking.schedule_id)
        if schedule:
            pax = booking.passenger_count or 1
            schedule.seats_available += pax

    # When un-cancelling (cancelled → confirmed/pending): deduct seats again
    if old_status == "cancelled" and new_status != "cancelled":
        schedule = Schedule.query.get(booking.schedule_id)
        if schedule:
            pax = booking.passenger_count or 1
            if schedule.seats_available >= pax:
                schedule.seats_available -= pax
            else:
                return jsonify({"error": "Not enough seats available to reinstate this booking"}), 400

    booking.status = new_status
    from extensions import db as _db
    _db.session.commit()

    return jsonify({
        "message":     f"Booking {booking.booking_code} status updated to '{new_status}'",
        "booking_id":  booking_id,
        "booking_code": booking.booking_code,
        "old_status":  old_status,
        "new_status":  new_status
    }), 200

# ── Feature 4: Revenue chart data ───────────────────────────────
@admin_bp.route("/revenue", methods=["GET"])
@jwt_required()
def revenue_chart():
    err = admin_required()
    if err: return err

    # Last 7 days daily revenue
    today = datetime.utcnow().date()
    days_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        rev = db.session.query(db.func.sum(Booking.amount)).filter(
            Booking.status == "confirmed",
            Booking.travel_date == day_str
        ).scalar() or 0
        count = Booking.query.filter(
            Booking.status == "confirmed",
            Booking.travel_date == day_str
        ).count()
        days_data.append({
            "date":    day_str,
            "label":  day.strftime("%b %d"),
            "revenue": float(rev),
            "bookings": count
        })

    # Monthly totals (last 6 months)
    months_data = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_end_day = (month_start.replace(month=month_start.month % 12 + 1, day=1)
                         if month_start.month < 12
                         else month_start.replace(year=month_start.year+1, month=1, day=1))
        month_str    = month_start.strftime("%Y-%m")
        rev = db.session.query(db.func.sum(Booking.amount)).filter(
            Booking.status == "confirmed",
            Booking.travel_date >= month_start.strftime("%Y-%m-%d"),
            Booking.travel_date <  month_end_day.strftime("%Y-%m-%d")
        ).scalar() or 0
        months_data.append({
            "month":   month_str,
            "label":   month_start.strftime("%b %Y"),
            "revenue": float(rev)
        })

    return jsonify({"daily": days_data, "monthly": months_data})

# ── Feature 9: Password reset (admin can reset any user) ────────
@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@jwt_required()
def admin_reset_password(user_id):
    err = admin_required()
    if err: return err
    from werkzeug.security import generate_password_hash
    data = request.get_json() or {}
    new_password = data.get("new_password", "BusBook2026!")
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.password = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({"message": f"Password reset for {user.email}"}), 200

# FIX 2 — GET /api/admin/bookings/recent — last 10 bookings for dashboard
@admin_bp.route("/bookings/recent", methods=["GET"])
@jwt_required()
def recent_bookings():
    err = admin_required()
    if err: return err

    bookings = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
    result = []
    for b in bookings:
        sched = Schedule.query.get(b.schedule_id)
        usr   = User.query.get(b.user_id)
        result.append({
            "id":              b.id,
            "booking_code":    b.booking_code,
            "passenger":       f"{usr.first_name} {usr.last_name}".strip() if usr else "—",
            "email":           usr.email if usr else "—",
            "route":           sched.route if sched else "—",
            "travel_date":     b.travel_date,
            "departure":       (sched.departure_time or "—").split("T")[-1] if sched else "—",
            "seat_number":     b.seat_number or "—",
            "passenger_count": b.passenger_count or 1,
            "amount":          b.amount or 0,
            "status":          b.status,
            "payment_method":  b.payment_method or "—",
        })
    return jsonify({"bookings": result})
