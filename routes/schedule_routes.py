from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from utils.decorators import admin_required
from services.schedule_service import create_schedule, get_schedules, delete_schedule
from models.schedule import Schedule
from models.booking import Booking
from models.bus import Bus
from extensions import db

schedule_bp = Blueprint("schedule", __name__)


# ── GET /api/schedules/ — public ─────────────────────────────────
@schedule_bp.route("/", methods=["GET"])
def list_schedules():
    return jsonify({"schedules": get_schedules()})


# ── GET /api/schedules/search ─────────────────────────────────────
@schedule_bp.route("/search", methods=["GET"])
def search_schedules():
    origin      = (request.args.get("origin")      or "").strip().lower()
    destination = (request.args.get("destination") or "").strip().lower()

    if not origin or not destination:
        return jsonify({"error": "origin and destination are required"}), 400

    all_schedules = Schedule.query.filter_by(is_active=True).all()
    results = []
    for s in all_schedules:
        route_lower = (s.route or "").lower()
        if origin in route_lower and destination in route_lower:
            bus = Bus.query.get(s.bus_id) if s.bus_id else None
            results.append(_serialize_schedule(s, bus))
    return jsonify({"schedules": results})


# ── GET /api/schedules/<id> — single schedule ─────────────────────
@schedule_bp.route("/<int:schedule_id>", methods=["GET"])
def get_schedule(schedule_id):
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return jsonify({"error": "Schedule not found"}), 404
    bus = Bus.query.get(schedule.bus_id) if schedule.bus_id else None
    return jsonify({"schedule": _serialize_schedule(schedule, bus)}), 200


# ── GET /api/schedules/<id>/seats ─────────────────────────────────
@schedule_bp.route("/<int:schedule_id>/seats", methods=["GET"])
def schedule_seats(schedule_id):
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return jsonify({"error": "Schedule not found"}), 404

    bus = Bus.query.get(schedule.bus_id) if schedule.bus_id else None

    taken_bookings = Booking.query.filter(
        Booking.schedule_id == schedule_id,
        Booking.status.in_(["locked", "pending", "confirmed"])
    ).all()

    booked = []
    for b in taken_bookings:
        if b.seat_number:
            for s in b.seat_number.split(","):
                s = s.strip()
                if s:
                    booked.append(s)

    return jsonify({
        "schedule_id":     schedule_id,
        "seat_layout":     bus.seat_layout  if bus else "4-column",
        "total_seats":     bus.total_seats  if bus else 40,
        "booked_seats":    booked,
        "seats_available": schedule.seats_available,
    })


# ── POST /api/schedules/ — admin only ────────────────────────────
@schedule_bp.route("/", methods=["POST"])
@jwt_required()
@admin_required
def create():
    data = request.get_json() or {}
    result, status = create_schedule(data)
    return jsonify(result), status


# ── PUT /api/schedules/<id> ───────────────────────────────────────
@schedule_bp.route("/<int:schedule_id>", methods=["PUT"])
@jwt_required()
@admin_required
def update(schedule_id):
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return jsonify({"error": "Schedule not found"}), 404

    data = request.get_json() or {}
    if data.get("route"):
        if len(data["route"].strip()) > 200:
            return jsonify({"error": "Route name too long"}), 400
        schedule.route = data["route"].strip()
    if data.get("departure_time"):
        schedule.departure_time = data["departure_time"]
    if data.get("arrival_time") is not None:
        schedule.arrival_time = data["arrival_time"]
    if data.get("fare") is not None:
        fare = float(data["fare"])
        if fare < 0:
            return jsonify({"error": "Fare cannot be negative"}), 400
        schedule.fare = fare
    if data.get("seats_available") is not None:
        seats = int(data["seats_available"])
        if seats < 0:
            return jsonify({"error": "Seats cannot be negative"}), 400
        schedule.seats_available = seats
    if data.get("bus_id") is not None:
        schedule.bus_id = data["bus_id"] or None
    if "is_active" in data:
        schedule.is_active = bool(data["is_active"])

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update schedule"}), 500

    return jsonify({"message": "Schedule updated"}), 200


# ── DELETE /api/schedules/<id> ────────────────────────────────────
@schedule_bp.route("/<int:schedule_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete(schedule_id):
    result, status = delete_schedule(schedule_id)
    return jsonify(result), status


# ── Helper ────────────────────────────────────────────────────────
def _serialize_schedule(s, bus):
    return {
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
        "total_seats":     bus.total_seats  if bus else 40,
    }
