from app.models import db
from datetime import datetime

class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Integer, nullable=False)
    price_per_day = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    booking_status = db.Column(db.String(20), default='Pending') # Pending, Confirmed, Active, Completed, Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payment = db.relationship('Payment', backref='booking', uselist=False, lazy=True)

    @property
    def payment_status(self):
        if self.payment:
            return self.payment.payment_status
        return 'Pending'

    def __repr__(self):
        return f'<Booking {self.id}>'
