from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from services.schedule_service import create_schedule, get_schedules, delete_schedule
from models.schedule import Schedule
from extensions import db

schedule_bp = Blueprint("schedule", __name__)

def admin_required():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    return None

# GET /api/schedules/ — public, no auth needed
@schedule_bp.route("/", methods=["GET"])
def list_schedules():
    # Return {"schedules": [...]} so frontend can handle both array and object
    return jsonify({"schedules": get_schedules()})

# POST /api/schedules/ — admin only
@schedule_bp.route("/", methods=["POST"])
@jwt_required()
def create():
    err = admin_required()
    if err: return err
    data = request.get_json()
    result, status = create_schedule(data)
    return jsonify(result), status

# PUT /api/schedules/<id>
@schedule_bp.route("/<int:schedule_id>", methods=["PUT"])
@jwt_required()
def update(schedule_id):
    err = admin_required()
    if err: return err
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return jsonify({"error": "Schedule not found"}), 404
    data = request.get_json() or {}
    if data.get("route"):           schedule.route           = data["route"].strip()
    if data.get("departure_time"):  schedule.departure_time  = data["departure_time"]
    if data.get("arrival_time") is not None: schedule.arrival_time = data["arrival_time"]
    if data.get("fare") is not None:
        fare = float(data["fare"])
        if fare < 0: return jsonify({"error": "Fare cannot be negative"}), 400
        schedule.fare = fare
    if data.get("seats_available") is not None:
        seats = int(data["seats_available"])
        if seats < 0: return jsonify({"error": "Seats cannot be negative"}), 400
        schedule.seats_available = seats
    if data.get("bus_id") is not None:
        schedule.bus_id = data["bus_id"] or None
    db.session.commit()
    return jsonify({"message": "Schedule updated"}), 200

# DELETE /api/schedules/<id>
@schedule_bp.route("/<int:schedule_id>", methods=["DELETE"])
@jwt_required()
def delete(schedule_id):
    err = admin_required()
    if err: return err
    result, status = delete_schedule(schedule_id)
    return jsonify(result), status
