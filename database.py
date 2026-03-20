from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


# ─── USER MODEL ───────────────────────────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'

    id         = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50),  nullable=False)
    last_name  = db.Column(db.String(50),  nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    phone      = db.Column(db.String(20),  nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    role       = db.Column(db.String(10),  default='user')   # 'user' or 'admin'
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    bookings   = db.relationship('Booking', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'


# ─── SCHEDULE MODEL ───────────────────────────────────────────────────────────
class Schedule(db.Model):
    __tablename__ = 'schedules'

    id               = db.Column(db.Integer, primary_key=True)
    route            = db.Column(db.String(100), nullable=False)
    departure_time   = db.Column(db.String(10),  nullable=False)   # e.g. "06:00"
    fare             = db.Column(db.Float,        nullable=False)
    seats_available  = db.Column(db.Integer,      default=40)
    is_active        = db.Column(db.Boolean,      default=True)
    created_at       = db.Column(db.DateTime,     default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='schedule', lazy=True)

    def to_dict(self):
        return {
            'id':              self.id,
            'route':           self.route,
            'departure_time':  self.departure_time,
            'fare':            self.fare,
            'seats_available': self.seats_available,
            'is_active':       self.is_active
        }

    def __repr__(self):
        return f'<Schedule {self.route} at {self.departure_time}>'


# ─── BOOKING MODEL ────────────────────────────────────────────────────────────
class Booking(db.Model):
    __tablename__ = 'bookings'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'),     nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id'), nullable=False)
    travel_date = db.Column(db.String(20),  nullable=False)   # ISO date string
    seat_number = db.Column(db.String(5),   nullable=True)
    status      = db.Column(db.String(20),  default='pending')  # pending | confirmed | cancelled
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow)

    payment = db.relationship('Payment', backref='booking', uselist=False, lazy=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'user_id':     self.user_id,
            'schedule_id': self.schedule_id,
            'route':       self.schedule.route          if self.schedule else '',
            'time':        self.schedule.departure_time if self.schedule else '',
            'fare':        self.schedule.fare           if self.schedule else 0,
            'travel_date': self.travel_date,
            'seat_number': self.seat_number,
            'status':      self.status,
            'created_at':  self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<Booking {self.id} - {self.status}>'


# ─── PAYMENT MODEL ────────────────────────────────────────────────────────────
class Payment(db.Model):
    __tablename__ = 'payments'

    id             = db.Column(db.Integer, primary_key=True)
    booking_id     = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    payment_method = db.Column(db.String(30),  nullable=False)   # GCash | PayMaya | PayPal
    amount         = db.Column(db.Float,        nullable=False)
    reference_no   = db.Column(db.String(20),   unique=True, nullable=False)
    status         = db.Column(db.String(20),   default='completed')
    paid_at        = db.Column(db.DateTime,     default=datetime.utcnow)

    def __repr__(self):
        return f'<Payment {self.reference_no} - {self.amount}>'