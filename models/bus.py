from extensions import db

class Bus(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    plate_number = db.Column(db.String(50),  nullable=False, unique=True)
    total_seats  = db.Column(db.Integer,     nullable=False, default=40)
    seat_layout  = db.Column(db.String(50),  default="4-column")
    is_active    = db.Column(db.Boolean,     default=True)
