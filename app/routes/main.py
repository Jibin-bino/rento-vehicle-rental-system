from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from app.models.vehicle import Vehicle
from app.models.booking import Booking

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    featured_vehicles = Vehicle.query.filter_by(status='Active').all()
    return render_template('index.html', featured_vehicles=featured_vehicles)

@bp.route('/dashboard')
@login_required
def dashboard():
    # Use the logged-in user's database ID, not hard-coded data
    user_id = current_user.id
    
    total_bookings = Booking.query.filter_by(user_id=user_id).count()
    active_bookings = Booking.query.filter(
        Booking.user_id == user_id,
        Booking.booking_status.in_(['Confirmed', 'Active'])
    ).count()
    pending_bookings = Booking.query.filter_by(user_id=user_id, booking_status='Pending').count()
    cancelled_bookings = Booking.query.filter_by(user_id=user_id, booking_status='Cancelled').count()
    completed_bookings = Booking.query.filter_by(user_id=user_id, booking_status='Completed').count()
    
    valid_bookings = Booking.query.filter(
        Booking.user_id == user_id,
        Booking.booking_status.in_(['Confirmed', 'Active', 'Completed'])
    ).all()
    total_spent = sum(b.total_amount for b in valid_bookings)
    
    recent_bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.created_at.desc()).limit(5).all()
    
    return render_template(
        'dashboard.html',
        user=current_user,
        total_bookings=total_bookings,
        active_bookings=active_bookings,
        pending_bookings=pending_bookings,
        cancelled_bookings=cancelled_bookings,
        completed_bookings=completed_bookings,
        total_spent=total_spent,
        recent_bookings=recent_bookings
    )

