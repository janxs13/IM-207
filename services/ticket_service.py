from utils.qr_generator import generate_qr
from utils.pdf_generator import generate_ticket_pdf
from models.schedule import Schedule
from models.user import User


def create_ticket(booking):
    schedule = Schedule.query.get(booking.schedule_id)
    user     = User.query.get(booking.user_id)

    route_parts = (schedule.route if schedule else "Unknown - Unknown").split(" - ")
    origin      = route_parts[0] if len(route_parts) > 0 else "—"
    destination = route_parts[1] if len(route_parts) > 1 else "—"

    qr_path = generate_qr(booking.booking_code)

    passenger_name = f"{user.first_name} {user.last_name}" if user else str(booking.user_id)

    ticket_data = {
        "booking_code": booking.booking_code,
        "user":         passenger_name,
        "origin":       origin,
        "destination":  destination,
        "seat":         booking.seat_number or "—",
        "departure":    schedule.departure_time if schedule else "—",
        "travel_date":  booking.travel_date or "—",
        "amount":       booking.amount or 0,
        "qr_path":      qr_path
    }

    pdf = generate_ticket_pdf(ticket_data)

    return {
        "qr":  qr_path,
        "pdf": pdf
    }
