from extensions import db
from datetime import datetime


class ContactMessage(db.Model):
    """Stores contact form submissions from passengers."""
    __tablename__ = "contact_message"

    id         = db.Column(db.Integer,     primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(120), nullable=False)
    subject    = db.Column(db.String(200), nullable=False)
    message    = db.Column(db.Text,        nullable=False)
    is_read    = db.Column(db.Boolean,     default=False)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "subject":    self.subject,
            "message":    self.message,
            "is_read":    self.is_read,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "—",
        }
