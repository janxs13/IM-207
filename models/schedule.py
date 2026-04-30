from extensions import db

class Schedule(db.Model):
    id              = db.Column(db.Integer,  primary_key=True)
    route           = db.Column(db.String(200))
    departure_time  = db.Column(db.String(50))
    arrival_time    = db.Column(db.String(50))
    fare            = db.Column(db.Float)
    seats_available = db.Column(db.Integer,  default=40)
    is_active       = db.Column(db.Boolean,  default=True)
    bus_id          = db.Column(db.Integer,  db.ForeignKey("bus.id"), nullable=True)
    # ── New fields ───────────────────────────────────────
    distance_km     = db.Column(db.Float,    nullable=True)        # for LTFRB fare
    bus_type        = db.Column(db.String(50), default="ordinary") # ordinary/aircon/provincial
    trip_status     = db.Column(db.String(30), default="scheduled")  # scheduled/boarding/departed/arrived/cancelled/delayed
    delay_minutes   = db.Column(db.Integer,  default=0)
    delay_reason    = db.Column(db.String(200), nullable=True)
