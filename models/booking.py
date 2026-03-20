from extensions import db
from datetime import datetime

class Booking(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("user.id"))
    schedule_id     = db.Column(db.Integer, db.ForeignKey("schedule.id"))
    seat_number     = db.Column(db.String(10))
    booking_code    = db.Column(db.String(50), unique=True)
    status          = db.Column(db.String(20), default="pending")
    travel_date     = db.Column(db.String(20))
    payment_method  = db.Column(db.String(50))
    reference_no    = db.Column(db.String(50))
    amount          = db.Column(db.Float)
    passenger_count = db.Column(db.Integer, default=1)
    locked_until    = db.Column(db.DateTime)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)