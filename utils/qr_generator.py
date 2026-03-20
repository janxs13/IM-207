import qrcode
import os

def generate_qr(booking_code):

    folder = "static/qrcodes"

    if not os.path.exists(folder):
        os.makedirs(folder)

    file_path = f"{folder}/{booking_code}.png"

    img = qrcode.make(booking_code)

    img.save(file_path)

    return file_path