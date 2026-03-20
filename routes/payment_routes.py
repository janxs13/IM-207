from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from services.payment_service import process_payment

payment_bp = Blueprint("payment", __name__)

@payment_bp.route("/", methods=["POST"])
@jwt_required()
def pay():
    data = request.get_json()
    result, status = process_payment(data)
    return jsonify(result), status
