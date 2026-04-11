from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(db.Model):
    id                  = db.Column(db.Integer,     primary_key=True)
    first_name          = db.Column(db.String(100))
    last_name           = db.Column(db.String(100))
    email               = db.Column(db.String(120), unique=True, nullable=False)
    phone               = db.Column(db.String(20))
    password            = db.Column(db.String(255), nullable=False)
    role                = db.Column(db.String(20),  default="user")
    reset_token         = db.Column(db.String(20),  nullable=True)
    reset_token_expires = db.Column(db.DateTime,    nullable=True)  # token expiry

    def set_password(self, pw):
        self.password = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password, pw)

    def is_reset_token_valid(self, token):
        """Returns True if the token matches and hasn't expired."""
        if not self.reset_token or self.reset_token != token:
            return False
        if self.reset_token_expires and datetime.utcnow() > self.reset_token_expires:
            return False
        return True
