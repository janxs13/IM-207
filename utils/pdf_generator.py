from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os


def generate_ticket_pdf(data):
    folder = "static/tickets"
    if not os.path.exists(folder):
        os.makedirs(folder)

    file_path = f"{folder}/{data['booking_code']}.pdf"
    c = canvas.Canvas(file_path, pagesize=letter)
    w, h = letter

    # Header bar
    c.setFillColor(colors.HexColor("#f4a261"))
    c.rect(0, h - 100, w, 100, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(w / 2, h - 45, "🚌 BUS TICKET")
    c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2, h - 70, "Your trip has been confirmed!")

    # Route display
    c.setFillColor(colors.HexColor("#333333"))
    c.setFont("Helvetica-Bold", 20)
    route_text = f"{data['origin']}  →  {data['destination']}"
    c.drawCentredString(w / 2, h - 130, route_text)

    # Detail grid
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#888888"))
    details = [
        ("PASSENGER",    data["user"]),
        ("SEAT NO.",      data["seat"]),
        ("TRAVEL DATE",  data.get("travel_date", "—")),
        ("DEPARTURE",    data["departure"]),
        ("BOOKING CODE", data["booking_code"]),
        ("AMOUNT PAID",  f"PHP {float(data.get('amount', 0)):.2f}"),
    ]
    y = h - 170
    for i, (label, value) in enumerate(details):
        x = 50 if i % 2 == 0 else 320
        if i % 2 == 0 and i > 0:
            y -= 50
        c.setFillColor(colors.HexColor("#888888"))
        c.setFont("Helvetica", 9)
        c.drawString(x, y, label)
        c.setFillColor(colors.HexColor("#333333"))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y - 16, str(value))

    # QR code
    qr_path = data.get("qr_path")
    if qr_path and os.path.exists(qr_path):
        c.drawImage(qr_path, w - 160, 50, width=120, height=120)
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#888888"))
        c.drawCentredString(w - 100, 40, "Scan to verify")

    # Footer
    c.setFillColor(colors.HexColor("#f4a261"))
    c.rect(0, 0, w, 30, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, 10, "Bus Ticket Booking System © 2026")

    c.save()
    return file_path
