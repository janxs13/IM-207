from extensions import db

class Bus(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100))
    plate_number = db.Column(db.String(50))
    total_seats  = db.Column(db.Integer)
    seat_layout  = db.Column(db.String(50))