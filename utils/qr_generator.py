"""
QR code generator for BusBook e-tickets.
Encodes a full verify URL so scanning on any device opens the right page.
Uses APP_BASE_URL from Flask config — set in .env for production.
"""
import qrcode
import os


def generate_qr(booking_code: str, base_url: str = None) -> str:
    """
    Generate a QR code PNG for booking_code.
    base_url: override the verify URL base (defaults to APP_BASE_URL from config).
    Returns the file path of the saved PNG.
    """
    folder = "static/qrcodes"
    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, f"{booking_code.upper()}.png")

    # FIX: read APP_BASE_URL from Flask config, fallback to localhost only for dev
    if not base_url:
        try:
            from flask import current_app
            base_url = current_app.config.get("APP_BASE_URL", "http://localhost:5000")
        except RuntimeError:
            # Outside Flask context (e.g. tests)
            base_url = os.environ.get("APP_BASE_URL", "http://localhost:5000")

    base_url = base_url.rstrip("/")
    qr_data  = f"{base_url}/verify/{booking_code.upper()}"

    qr = qrcode.QRCode(
        version        = 1,
        error_correction = qrcode.constants.ERROR_CORRECT_M,
        box_size       = 10,
        border         = 4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(file_path)
    return file_path
