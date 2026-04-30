from extensions import db
from datetime import datetime

class Booking(db.Model):
    id               = db.Column(db.Integer,  primary_key=True)
    user_id          = db.Column(db.Integer,  db.ForeignKey("user.id"))
    schedule_id      = db.Column(db.Integer,  db.ForeignKey("schedule.id"))
    seat_number      = db.Column(db.String(100))
    booking_code     = db.Column(db.String(50), unique=True)
    status           = db.Column(db.String(20), default="pending")
    travel_date      = db.Column(db.String(20))
    payment_method   = db.Column(db.String(50))
    reference_no     = db.Column(db.String(50))
    amount           = db.Column(db.Float)
    passenger_count  = db.Column(db.Integer,  default=1)
    locked_until     = db.Column(db.DateTime)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    verify_count     = db.Column(db.Integer,  default=0)
    deleted_at       = db.Column(db.DateTime, nullable=True, default=None)
    deleted_by       = db.Column(db.String(100), nullable=True, default=None)
    # ── Discount fields (RA 9994 / RA 7277) ──────────────
    passenger_type   = db.Column(db.String(20), default="regular")  # regular/senior/pwd/student
    discount_type    = db.Column(db.String(20), nullable=True)
    discount_amount  = db.Column(db.Float, default=0.0)
    original_amount  = db.Column(db.Float, nullable=True)
    id_number        = db.Column(db.String(100), nullable=True)   # OSCA/PWD ID number
    id_type          = db.Column(db.String(50),  nullable=True)   # OSCA Card / PWD ID / PhilSys
