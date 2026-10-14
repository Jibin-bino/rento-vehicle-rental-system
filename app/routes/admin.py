from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user
from app.models import db
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.category import Category
from app.models.booking import Booking
from app.models.payment import Payment
from app.forms import VehicleForm
from datetime import datetime

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.before_request
def require_admin():
    # Enforce authentication and strictly verify ADMIN role for every /admin/* route
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.path))
    if current_user.role != 'ADMIN':
        abort(403)

# -------------------------------------------------------------
# 1. ADMIN DASHBOARD
# -------------------------------------------------------------
@bp.route('/')
@bp.route('/dashboard')
def dashboard():
    total_vehicles = Vehicle.query.count()
    active_vehicles = Vehicle.query.filter_by(status='Active').count()
    total_users = User.query.count()
    total_bookings = Booking.query.count()
    active_bookings = Booking.query.filter(Booking.booking_status.in_(['Confirmed', 'Active'])).count()
    pending_bookings = Booking.query.filter_by(booking_status='Pending').count()
    
    # Calculate revenue from paid payments
    paid_payments = Payment.query.filter_by(payment_status='Paid').all()
    total_revenue = sum(p.amount for p in paid_payments)
    
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(8).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return render_template(
        'admin/dashboard.html',
        total_vehicles=total_vehicles,
        active_vehicles=active_vehicles,
        total_users=total_users,
        total_bookings=total_bookings,
        active_bookings=active_bookings,
        pending_bookings=pending_bookings,
        total_revenue=total_revenue,
        recent_bookings=recent_bookings,
        recent_users=recent_users
    )

# -------------------------------------------------------------
# 2. VEHICLE MANAGEMENT (Add, Edit, Delete, View)
# -------------------------------------------------------------
@bp.route('/vehicles')
def vehicles():
    search = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', type=int)
    status = request.args.get('status', '').strip()
    
    query = Vehicle.query
    if search:
        query = query.filter((Vehicle.name.ilike(f'%{search}%')) | (Vehicle.brand.ilike(f'%{search}%')) | (Vehicle.model.ilike(f'%{search}%')) | (Vehicle.location.ilike(f'%{search}%')))
    if category_id:
        query = query.filter_by(category_id=category_id)
    if status and status != 'All':
        query = query.filter_by(status=status)
        
    vehicles_list = query.order_by(Vehicle.id.desc()).all()
    categories = Category.query.all()
    
    return render_template(
        'admin/vehicles/index.html',
        vehicles=vehicles_list,
        categories=categories,
        search=search,
        selected_category=category_id,
        selected_status=status
    )

@bp.route('/vehicles/add', methods=['GET', 'POST'])
def vehicle_add():
    form = VehicleForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    
    if form.validate_on_submit():
        vehicle = Vehicle(
            name=form.name.data.strip(),
            brand=form.brand.data.strip(),
            model=form.model.data.strip(),
            category_id=form.category_id.data,
            price_per_day=form.price_per_day.data,
            fuel_type=form.fuel_type.data,
            transmission=form.transmission.data,
            seats=form.seats.data,
            location=form.location.data.strip(),
            status=form.status.data,
            description=form.description.data.strip() if form.description.data else '',
            image=form.image.data.strip() if form.image.data else None
        )
        db.session.add(vehicle)
        db.session.commit()
        flash(f'Vehicle "{vehicle.name}" added successfully!', 'success')
        return redirect(url_for('admin.vehicles'))
        
    return render_template('admin/vehicles/form.html', form=form, title='Add New Vehicle', is_edit=False)

@bp.route('/vehicles/<int:id>/edit', methods=['GET', 'POST'])
def vehicle_edit(id):
    vehicle = Vehicle.query.get_or_404(id)
    form = VehicleForm(obj=vehicle)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    
    if form.validate_on_submit():
        vehicle.name = form.name.data.strip()
        vehicle.brand = form.brand.data.strip()
        vehicle.model = form.model.data.strip()
        vehicle.category_id = form.category_id.data
        vehicle.price_per_day = form.price_per_day.data
        vehicle.fuel_type = form.fuel_type.data
        vehicle.transmission = form.transmission.data
        vehicle.seats = form.seats.data
        vehicle.location = form.location.data.strip()
        vehicle.status = form.status.data
        vehicle.description = form.description.data.strip() if form.description.data else ''
        if form.image.data:
            vehicle.image = form.image.data.strip()
            
        db.session.commit()
        flash(f'Vehicle "{vehicle.name}" updated successfully!', 'success')
        return redirect(url_for('admin.vehicles'))
        
    return render_template('admin/vehicles/form.html', form=form, vehicle=vehicle, title=f'Edit Vehicle - {vehicle.name}', is_edit=True)

@bp.route('/vehicles/<int:id>/delete', methods=['POST'])
def vehicle_delete(id):
    vehicle = Vehicle.query.get_or_404(id)
    
    # Check for any bookings to prevent data loss (missing booking history)
    any_bookings = Booking.query.filter_by(vehicle_id=vehicle.id).first()
    
    if any_bookings:
        flash(f'Cannot delete "{vehicle.name}" because it has associated booking history. You can change its status to Inactive or Maintenance instead.', 'error')
        return redirect(url_for('admin.vehicles'))
        
    # If safe or has past bookings, cascade or delete bookings safely
    for b in vehicle.bookings:
        if b.payment:
            db.session.delete(b.payment)
        db.session.delete(b)
        
    name = vehicle.name
    db.session.delete(vehicle)
    db.session.commit()
    flash(f'Vehicle "{name}" has been deleted successfully.', 'success')
    return redirect(url_for('admin.vehicles'))

# -------------------------------------------------------------
# 3. USERS MANAGEMENT
# -------------------------------------------------------------
@bp.route('/users')
def users():
    search = request.args.get('q', '').strip()
    role_filter = request.args.get('role', '').strip()
    
    query = User.query
    if search:
        query = query.filter((User.name.ilike(f'%{search}%')) | (User.email.ilike(f'%{search}%')) | (User.phone.ilike(f'%{search}%')))
    if role_filter and role_filter != 'All':
        query = query.filter_by(role=role_filter)
        
    users_list = query.order_by(User.id.asc()).all()
    return render_template('admin/users/index.html', users=users_list, search=search, selected_role=role_filter)

@bp.route('/users/<int:id>/role', methods=['POST'])
def user_toggle_role(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('You cannot change your own role.', 'error')
        return redirect(url_for('admin.users'))
        
    new_role = 'ADMIN' if user.role == 'USER' else 'USER'
    user.role = new_role
    db.session.commit()
    flash(f'User "{user.name}" role updated to {new_role}.', 'success')
    return redirect(url_for('admin.users'))

# -------------------------------------------------------------
# 4. BOOKINGS MANAGEMENT (View, Filter, Status Update)
# -------------------------------------------------------------
@bp.route('/bookings')
def bookings():
    search = request.args.get('q', '').strip()
    booking_status = request.args.get('status', '').strip()
    payment_status = request.args.get('payment_status', '').strip()
    
    query = Booking.query.join(User).join(Vehicle)
    
    if search:
        if search.startswith('#'):
            clean_search = search[1:]
        else:
            clean_search = search
        if clean_search.isdigit():
            query = query.filter(Booking.id == int(clean_search))
        else:
            query = query.filter(
                (User.name.ilike(f'%{search}%')) |
                (User.email.ilike(f'%{search}%')) |
                (Vehicle.name.ilike(f'%{search}%')) |
                (Vehicle.brand.ilike(f'%{search}%'))
            )
            
    if booking_status and booking_status != 'All':
        query = query.filter(Booking.booking_status == booking_status)
        
    if payment_status and payment_status != 'All':
        query = query.join(Payment).filter(Payment.payment_status == payment_status)
        
    bookings_list = query.order_by(Booking.id.desc()).all()
    
    return render_template(
        'admin/bookings/index.html',
        bookings=bookings_list,
        search=search,
        selected_status=booking_status,
        selected_payment_status=payment_status
    )

@bp.route('/bookings/<int:id>')
def booking_details(id):
    booking = Booking.query.get_or_404(id)
    return render_template('admin/bookings/details.html', booking=booking)

@bp.route('/bookings/<int:id>/status', methods=['POST'])
def booking_update_status(id):
    booking = Booking.query.get_or_404(id)
    new_booking_status = request.form.get('booking_status')
    new_payment_status = request.form.get('payment_status')
    
    valid_booking_statuses = ['Pending', 'Confirmed', 'Active', 'Completed', 'Cancelled']
    valid_payment_statuses = ['Pending', 'Paid', 'Refunded', 'Cancelled', 'Failed']
    
    if new_booking_status in valid_booking_statuses:
        booking.booking_status = new_booking_status
        
        # If cancelled by admin and was paid, auto-update payment to Refunded if not specified
        if new_booking_status == 'Cancelled' and booking.payment and booking.payment.payment_status == 'Paid':
            if not new_payment_status or new_payment_status == 'Paid':
                booking.payment.payment_status = 'Refunded'
                
    if new_payment_status in valid_payment_statuses and booking.payment:
        booking.payment.payment_status = new_payment_status
        if new_payment_status == 'Paid' and not booking.payment.paid_at:
            booking.payment.paid_at = datetime.utcnow()
            
    db.session.commit()
    flash(f'Booking #{booking.id} status updated successfully.', 'success')
    return redirect(request.referrer or url_for('admin.booking_details', id=booking.id))
