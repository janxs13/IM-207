from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.payment_service import process_payment
from services.ticket_service import create_ticket
from models.booking import Booking
import os

ticket_bp = Blueprint("ticket", __name__)

# POST /api/ticket/pay — legacy compat
@ticket_bp.route("/pay", methods=["POST"])
@jwt_required()
def pay():
    data = request.json
    result, status = process_payment(data)
    return jsonify(result), status

# GET /api/ticket/download/<booking_code>
@ticket_bp.route("/download/<booking_code>", methods=["GET"])
@jwt_required()
def download_ticket(booking_code):
    booking = Booking.query.filter_by(booking_code=booking_code.upper()).first()
    if not booking:
        return jsonify({"error": "Ticket not found"}), 404
    if booking.status != "confirmed":
        return jsonify({"error": "Ticket is not confirmed yet"}), 400

    # Verify ownership
    current_user_id = int(get_jwt_identity())
    if booking.user_id != current_user_id:
        return jsonify({"error": "Access denied"}), 403

    ticket = create_ticket(booking)
    pdf_path = ticket.get("pdf")
    if pdf_path and os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True,
                         download_name=f"ticket_{booking_code}.pdf")
    return jsonify({"error": "PDF generation failed"}), 500

# GET /api/ticket/qr/<booking_code> — returns QR image (no auth needed for display)
@ticket_bp.route("/qr/<booking_code>", methods=["GET"])
def get_qr(booking_code):
    # Check if QR already exists
    qr_path = f"static/qrcodes/{booking_code.upper()}.png"
    if os.path.exists(qr_path):
        return send_file(qr_path, mimetype="image/png")

    # Generate it
    booking = Booking.query.filter_by(booking_code=booking_code.upper()).first()
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    try:
        from utils.qr_generator import generate_qr
        path = generate_qr(booking_code.upper())
        if os.path.exists(path):
            return send_file(path, mimetype="image/png")
    except Exception as e:
        return jsonify({"error": f"QR generation failed: {str(e)}"}), 500

    return jsonify({"error": "QR not found"}), 404
