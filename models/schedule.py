from extensions import db

class Schedule(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    route           = db.Column(db.String(200))           # "Cebu - Mandaue"
    departure_time  = db.Column(db.String(50))
    arrival_time    = db.Column(db.String(50))
    fare            = db.Column(db.Float)
    seats_available = db.Column(db.Integer, default=40)
    is_active       = db.Column(db.Boolean, default=True)
    bus_id          = db.Column(db.Integer, db.ForeignKey("bus.id"), nullable=True)