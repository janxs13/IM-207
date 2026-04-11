import qrcode
import os

# Base URL for the verify endpoint — change if your server uses a different host/port
VERIFY_BASE_URL = "http://localhost:5000/verify"

def generate_qr(booking_code, base_url=None):
    folder = "static/qrcodes"
    if not os.path.exists(folder):
        os.makedirs(folder)

    file_path = f"{folder}/{booking_code}.png"

    # Encode a full URL so scanning on a phone opens the mobile verify page
    url = base_url or VERIFY_BASE_URL
    qr_data = f"{url}/{booking_code.upper()}"

    img = qrcode.make(qr_data)
    img.save(file_path)

    return file_path
