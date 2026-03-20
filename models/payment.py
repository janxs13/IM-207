from extensions import db
from datetime import datetime

class Payment(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    booking_id     = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=False)
    amount         = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    reference_no   = db.Column(db.String(50), unique=True, nullable=False)
    status         = db.Column(db.String(20), default="completed")
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    booking = db.relationship("Booking", backref=db.backref("payments", lazy=True))