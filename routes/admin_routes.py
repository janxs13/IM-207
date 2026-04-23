from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from utils.decorators import admin_required
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
import os

admin_bp = Blueprint("admin", __name__)


# ── Dashboard ────────────────────────────────────────────────────
@admin_bp.route("/dashboard", methods=["GET"])
@jwt_required()
@admin_required
def dashboard():
    return jsonify(get_dashboard_stats())


# ── Users ─────────────────────────────────────────────────────────
@admin_bp.route("/users", methods=["GET"])
@jwt_required()
@admin_required
def users():
    return jsonify({"users": get_all_users()})


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def remove_user(user_id):
    result, status = delete_user(user_id)
    return jsonify(result), status


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@jwt_required()
@admin_required
def admin_reset_password(user_id):
    from werkzeug.security import generate_password_hash
    data = request.get_json() or {}
    new_password = (data.get("new_password") or "BusBook2026!").strip()
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.password = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({"message": f"Password reset for {user.email}"}), 200


# ── Buses ─────────────────────────────────────────────────────────
@admin_bp.route("/buses", methods=["GET"])
@jwt_required()
@admin_required
def list_buses():
    return jsonify({"buses": get_all_buses()})


@admin_bp.route("/buses", methods=["POST"])
@jwt_required()
@admin_required
def add_bus():
    data = request.get_json() or {}
    if not data.get("name") and data.get("bus_name"):
        data["name"] = data["bus_name"]
    result, status = create_bus(data)
    return jsonify(result), status


@admin_bp.route("/buses/<int:bus_id>", methods=["PUT"])
@jwt_required()
@admin_required
def edit_bus(bus_id):
    bus = Bus.query.get(bus_id)
    if not bus:
        return jsonify({"error": "Bus not found"}), 404
    data = request.get_json() or {}
    if data.get("name"):         bus.name         = data["name"].strip()
    if data.get("bus_name"):     bus.name         = data["bus_name"].strip()
    if data.get("plate_number"): bus.plate_number = data["plate_number"].strip()
    if data.get("total_seats"):  bus.total_seats  = int(data["total_seats"])
    if data.get("seat_layout"):  bus.seat_layout  = data["seat_layout"]
    if "is_active" in data:      bus.is_active    = bool(data["is_active"])
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update bus"}), 500
    return jsonify({"message": "Bus updated"}), 200


@admin_bp.route("/buses/<int:bus_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def remove_bus(bus_id):
    result, status = delete_bus(bus_id)
    return jsonify(result), status


# ── Bus image upload ──────────────────────────────────────────────
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024   # 5 MB


def _allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def _bus_images_dir():
    from flask import current_app
    path = os.path.join(current_app.static_folder, "bus_images")
    os.makedirs(path, exist_ok=True)
    return path


@admin_bp.route("/buses/<int:bus_id>/image", methods=["POST"])
@jwt_required()
@admin_required
def upload_bus_image(bus_id):
    bus = Bus.query.get(bus_id)
    if not bus:
        return jsonify({"error": "Bus not found"}), 404

    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not _allowed_image(file.filename):
        return jsonify({"error": "Only JPG, PNG, and WEBP images are allowed"}), 400

    # Check file size
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_IMAGE_BYTES:
        return jsonify({"error": "Image must be under 5 MB"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"bus_{bus_id}.{ext}"
    save_dir = _bus_images_dir()

    # Delete any old image for this bus (different extension)
    for old_ext in ALLOWED_IMAGE_EXTENSIONS:
        old_path = os.path.join(save_dir, f"bus_{bus_id}.{old_ext}")
        if os.path.exists(old_path) and old_ext != ext:
            try:
                os.remove(old_path)
            except OSError:
                pass

    save_path = os.path.join(save_dir, filename)
    try:
        file.save(save_path)
    except Exception:
        return jsonify({"error": "Failed to save image. Please try again."}), 500

    bus.image_filename = filename
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update bus record"}), 500

    image_url = f"/static/bus_images/{filename}"
    return jsonify({"message": "Image uploaded", "image_url": image_url}), 200


@admin_bp.route("/buses/<int:bus_id>/image", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_bus_image(bus_id):
    bus = Bus.query.get(bus_id)
    if not bus:
        return jsonify({"error": "Bus not found"}), 404

    if bus.image_filename:
        try:
            path = os.path.join(_bus_images_dir(), bus.image_filename)
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
        bus.image_filename = None
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Failed to remove image reference"}), 500

    return jsonify({"message": "Image removed"}), 200


# ── Bookings (paginated) ──────────────────────────────────────────
@admin_bp.route("/bookings", methods=["GET"])
@jwt_required()
@admin_required
def all_bookings_admin():
    status_filter = request.args.get("status")
    from_date     = request.args.get("from_date")
    to_date       = request.args.get("to_date")
    page          = max(1, int(request.args.get("page", 1)))
    per_page      = min(100, max(1, int(request.args.get("per_page", 50))))

    query = Booking.query.filter(Booking.deleted_at.is_(None))
    if status_filter:
        query = query.filter_by(status=status_filter)
    if from_date:
        query = query.filter(Booking.travel_date >= from_date)
    if to_date:
        query = query.filter(Booking.travel_date <= to_date)

    total    = query.count()
    bookings = query.order_by(Booking.created_at.desc()) \
                    .offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "bookings":  [_serialize_booking_admin(b) for b in bookings],
        "total":     total,
        "page":      page,
        "per_page":  per_page,
        "pages":     (total + per_page - 1) // per_page
    })


@admin_bp.route("/bookings/recent", methods=["GET"])
@jwt_required()
@admin_required
def recent_bookings():
    bookings = Booking.query.filter(Booking.deleted_at.is_(None)) \
                            .order_by(Booking.created_at.desc()).limit(10).all()
    return jsonify({"bookings": [_serialize_booking_admin(b) for b in bookings]})


@admin_bp.route("/bookings/<int:booking_id>/status", methods=["PUT"])
@jwt_required()
@admin_required
def update_booking_status(booking_id):
    data       = request.get_json() or {}
    new_status = (data.get("status") or "").strip().lower()
    allowed    = {"confirmed", "pending", "cancelled"}
    if new_status not in allowed:
        return jsonify({"error": f"Invalid status. Allowed: {', '.join(sorted(allowed))}"}), 400

    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    old_status = booking.status

    if new_status == "cancelled" and old_status != "cancelled":
        schedule = Schedule.query.get(booking.schedule_id)
        if schedule:
            schedule.seats_available += (booking.passenger_count or 1)

    if old_status == "cancelled" and new_status != "cancelled":
        schedule = Schedule.query.get(booking.schedule_id)
        if schedule:
            pax = booking.passenger_count or 1
            if schedule.seats_available < pax:
                return jsonify({"error": "Not enough seats to reinstate this booking"}), 400
            schedule.seats_available -= pax

    booking.status = new_status
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update booking status"}), 500

    return jsonify({
        "message":      f"Booking {booking.booking_code} status updated to '{new_status}'",
        "booking_id":   booking_id,
        "booking_code": booking.booking_code,
        "old_status":   old_status,
        "new_status":   new_status
    }), 200


@admin_bp.route("/bookings/<int:booking_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_booking(booking_id):
    booking = Booking.query.filter_by(id=booking_id, deleted_at=None).first()
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    if booking.status != "cancelled":
        schedule = Schedule.query.get(booking.schedule_id)
        if schedule:
            schedule.seats_available += (booking.passenger_count or 1)

    claims = get_jwt()
    booking.deleted_at = datetime.utcnow()
    booking.deleted_by = claims.get("email") or claims.get("sub") or "admin"
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to delete booking"}), 500

    return jsonify({"message": f"Booking {booking.booking_code} moved to trash."}), 200


@admin_bp.route("/bookings/deleted", methods=["GET"])
@jwt_required()
@admin_required
def list_deleted_bookings():
    bookings = Booking.query.filter(Booking.deleted_at.isnot(None)) \
                            .order_by(Booking.deleted_at.desc()).all()
    result = []
    for b in bookings:
        sched = Schedule.query.get(b.schedule_id)
        usr   = User.query.get(b.user_id)
        bus   = Bus.query.get(sched.bus_id) if sched and sched.bus_id else None
        result.append({
            "id":             b.id,
            "booking_code":   b.booking_code,
            "passenger":      f"{usr.first_name} {usr.last_name}".strip() if usr else "—",
            "email":          usr.email if usr else "—",
            "route":          sched.route if sched else "—",
            "travel_date":    b.travel_date,
            "seat_number":    b.seat_number or "—",
            "amount":         b.amount or 0,
            "status":         b.status,
            "payment_method": b.payment_method or "—",
            "bus_name":       bus.name if bus else "—",
            "deleted_at":     b.deleted_at.strftime("%Y-%m-%d %H:%M") if b.deleted_at else "—",
            "deleted_by":     b.deleted_by or "—",
        })
    return jsonify({"bookings": result, "total": len(result)})


@admin_bp.route("/bookings/<int:booking_id>/restore", methods=["POST"])
@jwt_required()
@admin_required
def restore_booking(booking_id):
    booking = Booking.query.filter(
        Booking.id == booking_id, Booking.deleted_at.isnot(None)
    ).first()
    if not booking:
        return jsonify({"error": "Booking not found in trash"}), 404

    if booking.status != "cancelled":
        schedule = Schedule.query.get(booking.schedule_id)
        if schedule:
            pax = booking.passenger_count or 1
            if schedule.seats_available < pax:
                return jsonify({"error": "Not enough seats to restore this booking"}), 400
            schedule.seats_available -= pax

    booking.deleted_at = None
    booking.deleted_by = None
    db.session.commit()
    return jsonify({"message": f"Booking {booking.booking_code} restored."}), 200


@admin_bp.route("/bookings/<int:booking_id>/permanent", methods=["DELETE"])
@jwt_required()
@admin_required
def permanent_delete_booking(booking_id):
    booking = Booking.query.filter(
        Booking.id == booking_id, Booking.deleted_at.isnot(None)
    ).first()
    if not booking:
        return jsonify({"error": "Booking not found in trash"}), 404

    booking_code = booking.booking_code
    from models.payment import Payment
    Payment.query.filter_by(booking_id=booking_id).delete()
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"message": f"Booking {booking_code} permanently deleted."}), 200


# ── Revenue ───────────────────────────────────────────────────────
@admin_bp.route("/revenue", methods=["GET"])
@jwt_required()
@admin_required
def revenue_chart():
    today     = datetime.utcnow().date()
    days_data = []
    for i in range(6, -1, -1):
        day     = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        rev = db.session.query(db.func.sum(Booking.amount)).filter(
            Booking.status == "confirmed",
            Booking.travel_date == day_str,
            Booking.deleted_at.is_(None)
        ).scalar() or 0
        count = Booking.query.filter(
            Booking.status == "confirmed",
            Booking.travel_date == day_str,
            Booking.deleted_at.is_(None)
        ).count()
        days_data.append({
            "date":     day_str,
            "label":    day.strftime("%b %d"),
            "revenue":  float(rev),
            "bookings": count
        })

    months_data = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        if month_start.month < 12:
            month_end = month_start.replace(month=month_start.month + 1, day=1)
        else:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
        rev = db.session.query(db.func.sum(Booking.amount)).filter(
            Booking.status == "confirmed",
            Booking.travel_date >= month_start.strftime("%Y-%m-%d"),
            Booking.travel_date <  month_end.strftime("%Y-%m-%d"),
            Booking.deleted_at.is_(None)
        ).scalar() or 0
        months_data.append({
            "month":   month_start.strftime("%Y-%m"),
            "label":   month_start.strftime("%b %Y"),
            "revenue": float(rev)
        })

    return jsonify({"daily": days_data, "monthly": months_data})


# ── Helper ────────────────────────────────────────────────────────
def _serialize_booking_admin(b):
    sched = Schedule.query.get(b.schedule_id)
    usr   = User.query.get(b.user_id)
    bus   = Bus.query.get(sched.bus_id) if sched and sched.bus_id else None
    return {
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
        "bus_name":        bus.name if bus else "—",
        "bus_plate":       bus.plate_number if bus else "—",
    }
