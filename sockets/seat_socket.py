from extensions import socketio

def emit_seat_update(schedule_id, seat, status):

    socketio.emit(
        "seat_update",
        {
            "schedule_id": schedule_id,
            "seat": seat,
            "status": status
        }
    )