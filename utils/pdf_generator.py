"""
PDF ticket generator — ReportLab-based.
Uses only standard Latin fonts (Helvetica/Times) — no emoji.
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os


def generate_ticket_pdf(data):
    folder = "static/tickets"
    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, f"{data['booking_code']}.pdf")
    c = canvas.Canvas(file_path, pagesize=letter)
    w, h = letter

    # ── Header bar ────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#f4a261"))
    c.rect(0, h - 90, w, 90, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 26)
    # FIX: removed emoji — use plain text only
    c.drawCentredString(w / 2, h - 38, "BUS E-TICKET")
    c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2, h - 62, "BusBook — Your trip is confirmed!")

    # ── Route ────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#1a1a2e"))
    c.setFont("Helvetica-Bold", 18)
    route_text = f"{data.get('origin', '—')}  -->  {data.get('destination', '—')}"
    c.drawCentredString(w / 2, h - 118, route_text)

    # ── Divider ──────────────────────────────────────────────────
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.line(40, h - 133, w - 40, h - 133)

    # ── Detail grid ──────────────────────────────────────────────
    details = [
        ("PASSENGER",    data.get("user",          "—")),
        ("BOOKING CODE", data.get("booking_code",  "—")),
        ("SEAT NO.",      data.get("seat",          "—")),
        ("TRAVEL DATE",  data.get("travel_date",   "—")),
        ("DEPARTURE",    data.get("departure",     "—")),
        ("AMOUNT PAID",  f"PHP {float(data.get('amount', 0)):.2f}"),
    ]
    y = h - 158
    for i, (label, value) in enumerate(details):
        x = 48 if i % 2 == 0 else 320
        if i % 2 == 0 and i > 0:
            y -= 56
        # Label
        c.setFillColor(colors.HexColor("#94a3b8"))
        c.setFont("Helvetica", 9)
        c.drawString(x, y, label)
        # Value
        c.setFillColor(colors.HexColor("#1e293b"))
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x, y - 17, str(value))

    # ── Dashed cut line ──────────────────────────────────────────
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setDash(4, 4)
    c.line(40, y - 40, w - 40, y - 40)
    c.setDash()

    # ── QR code ──────────────────────────────────────────────────
    qr_path = data.get("qr_path")
    if qr_path and os.path.exists(qr_path):
        qr_y = y - 165
        c.drawImage(qr_path, w / 2 - 60, qr_y, width=120, height=120)
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#94a3b8"))
        c.drawCentredString(w / 2, qr_y - 14, "Scan QR code at the terminal gate")

    # ── Footer ───────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#f4a261"))
    c.rect(0, 0, w, 28, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, 9, "BusBook Bus Ticketing System  |  Issued electronically")

    c.save()
    return file_path
