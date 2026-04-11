from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.payment_service import process_payment
from extensions import limiter
from utils.decorators import current_user_is_admin

payment_bp = Blueprint("payment", __name__)


@payment_bp.route("/", methods=["POST"])
@jwt_required()
@limiter.limit("20 per hour")
def pay():
    data = request.get_json() or {}
    result, status = process_payment(
        data, int(get_jwt_identity()), is_admin=current_user_is_admin()
    )
    return jsonify(result), status
