from app.models import db
from datetime import datetime

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_reference = db.Column(db.String(100), nullable=True)
    payment_status = db.Column(db.String(20), default='Pending') # Pending, Paid, Failed, Refunded
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Payment {self.id}>'
