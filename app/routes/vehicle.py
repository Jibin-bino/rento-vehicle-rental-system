from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models.vehicle import Vehicle
from app.models.booking import Booking
from app.forms import BookingForm
from datetime import datetime

bp = Blueprint('vehicle', __name__)

@bp.route('/')
def index():
    query = Vehicle.query.filter_by(status='Active')
    
    location = request.args.get('location', '')
    start_date_str = request.args.get('start_date', '')
    return_date_str = request.args.get('return_date', '')
    
    if location:
        query = query.filter(Vehicle.location == location)
        
    if start_date_str and return_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date()
            
            if start_date <= return_date:
                # Find bookings that overlap with the requested dates
                overlapping_bookings = Booking.query.filter(
                    Booking.booking_status.in_(['Confirmed', 'Active']),
                    Booking.start_date <= return_date,
                    Booking.return_date >= start_date
                ).with_entities(Booking.vehicle_id)
                
                query = query.filter(~Vehicle.id.in_(overlapping_bookings))
        except ValueError:
            pass
            
    vehicles = query.all()
    return render_template('vehicle/index.html', vehicles=vehicles, 
                           location=location, start_date=start_date_str, return_date=return_date_str)

@bp.route('/<int:id>')
def details(id):
    vehicle = Vehicle.query.get_or_404(id)
    if vehicle.status != 'Active':
        flash('This vehicle is currently not available.', 'error')
        return redirect(url_for('vehicle.index'))
    form = BookingForm()
    return render_template('vehicle/details.html', vehicle=vehicle, form=form)
