from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app.models import db
from app.models.vehicle import Vehicle
from app.models.booking import Booking
from app.models.payment import Payment
from app.forms import BookingForm
from app.services.payment_gateway import PaymentGatewayService
from datetime import date, datetime
import uuid

bp = Blueprint('booking', __name__)

@bp.route('/book/<int:vehicle_id>', methods=['POST'])
@login_required
def create(vehicle_id):
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    if vehicle.status != 'Active':
        flash('This vehicle is currently not available for booking.', 'error')
        return redirect(url_for('vehicle.index'))
    form = BookingForm()
    
    if form.validate_on_submit():
        start_date = form.start_date.data
        return_date = form.return_date.data
        
        # 1. Validate dates
        if not start_date or not return_date or start_date < date.today() or return_date <= start_date:
            flash('Invalid rental dates selected. Return date must be after pick-up date.', 'error')
            return redirect(url_for('vehicle.details', id=vehicle.id))
        
        # 2. Re-verify vehicle availability on backend
        overlapping_bookings = Booking.query.filter(
            Booking.vehicle_id == vehicle.id,
            Booking.booking_status.in_(['Confirmed', 'Active']),
            Booking.start_date <= return_date,
            Booking.return_date >= start_date
        ).all()
        
        if overlapping_bookings:
            flash('This vehicle is not available for the selected dates.', 'error')
            return redirect(url_for('vehicle.details', id=vehicle.id))
            
        # 3. Calculate final rental amount on backend (never trust frontend input)
        total_days = (return_date - start_date).days
        total_amount = total_days * vehicle.price_per_day
        
        # 4. Create booking with status PENDING
        booking = Booking(
            user_id=current_user.id,
            vehicle_id=vehicle.id,
            start_date=start_date,
            return_date=return_date,
            total_days=total_days,
            price_per_day=vehicle.price_per_day,
            total_amount=total_amount,
            booking_status='Pending'
        )
        db.session.add(booking)
        db.session.flush() # Populate booking.id
        
        # Create corresponding payment record with status PENDING
        payment = Payment(
            booking_id=booking.id,
            amount=total_amount,
            payment_status='Pending'
        )
        db.session.add(payment)
        db.session.commit()
        
        flash('Booking created successfully! Please complete payment in test sandbox mode to confirm your reservation.', 'success')
        return redirect(url_for('booking.checkout', id=booking.id))
        
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", 'error')
            
    return redirect(url_for('vehicle.details', id=vehicle.id))

@bp.route('/')
@login_required
def index():
    # Query strictly by logged-in user's database ID
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('booking/index.html', bookings=bookings)

@bp.route('/<int:id>')
@login_required
def details(id):
    booking = Booking.query.get_or_404(id)
    # Ensure authorization by database ID
    if booking.user_id != current_user.id and current_user.role != 'ADMIN':
        abort(403)
        
    # Ensure payment record exists for consistency
    if not booking.payment:
        payment = Payment(
            booking_id=booking.id,
            amount=booking.total_amount,
            payment_status='Pending'
        )
        db.session.add(payment)
        db.session.commit()

    payment_order = None
    if booking.payment_status == 'Pending' and booking.booking_status != 'Cancelled':
        payment_order = PaymentGatewayService.create_payment_order(booking)
        
    return render_template('booking/details.html', booking=booking, payment_order=payment_order)

@bp.route('/<int:id>/checkout')
@login_required
def checkout(id):
    booking = Booking.query.get_or_404(id)
    if booking.user_id != current_user.id and current_user.role != 'ADMIN':
        abort(403)
        
    if booking.booking_status == 'Cancelled':
        flash('This booking is cancelled and cannot be paid for.', 'error')
        return redirect(url_for('booking.details', id=booking.id))
        
    if booking.payment_status == 'Paid':
        flash('This booking is already paid and confirmed.', 'info')
        return redirect(url_for('booking.details', id=booking.id))
        
    payment_order = PaymentGatewayService.create_payment_order(booking)
    return render_template('booking/checkout.html', booking=booking, payment_order=payment_order)

@bp.route('/<int:id>/create-order', methods=['POST'])
@login_required
def create_order(id):
    booking = Booking.query.get_or_404(id)
    if booking.user_id != current_user.id and current_user.role != 'ADMIN':
        abort(403)
        
    if booking.booking_status == 'Cancelled':
        return jsonify({'success': False, 'error': 'Cannot create payment order for cancelled booking'}), 400
        
    payment_order = PaymentGatewayService.create_payment_order(booking)
    return jsonify({'success': True, 'order': payment_order})

@bp.route('/<int:id>/process-gateway', methods=['POST'])
@login_required
def process_gateway(id):
    booking = Booking.query.get_or_404(id)
    if booking.user_id != current_user.id and current_user.role != 'ADMIN':
        abort(403)
        
    if booking.booking_status == 'Cancelled':
        return jsonify({'success': False, 'error': 'Cannot process payment for cancelled booking'}), 400
        
    data = request.get_json(silent=True) or request.form
    order_id = data.get('order_id')
    method = data.get('method', 'Test Card')
    simulate_fail = data.get('simulate_failure', False)
    
    if simulate_fail:
        # Update payment status to Failed in backend database
        if not booking.payment:
            booking.payment = Payment(booking_id=booking.id, amount=booking.total_amount)
            db.session.add(booking.payment)
        booking.payment.payment_status = 'Failed'
        db.session.commit()
        return jsonify({
            'success': False,
            'error': 'Sandbox Gateway: Transaction declined by issuing bank (Simulated Failure)',
            'payment_status': 'Failed',
            'booking_status': booking.booking_status
        }), 400

    # Generate gateway-signed payment result with cryptographic HMAC signature
    gateway_result = PaymentGatewayService.simulate_gateway_processing(order_id, method=method)
    return jsonify({
        'success': True,
        'gateway_result': gateway_result
    })

@bp.route('/<int:id>/payment-failed', methods=['POST'])
@login_required
def payment_failed(id):
    """Handle explicit payment failure or user cancellation."""
    booking = Booking.query.get_or_404(id)
    if booking.user_id != current_user.id and current_user.role != 'ADMIN':
        abort(403)
        
    if not booking.payment:
        booking.payment = Payment(booking_id=booking.id, amount=booking.total_amount)
        db.session.add(booking.payment)
        
    data = request.get_json(silent=True) or request.form
    reason = data.get('reason', 'Payment declined or cancelled by user.')
    
    booking.payment.payment_status = 'Failed'
    db.session.commit()
    
    if request.is_json:
        return jsonify({
            'success': True,
            'payment_status': 'Failed',
            'booking_status': booking.booking_status,
            'message': reason
        })
    flash(reason, 'error')
    return redirect(url_for('booking.details', id=booking.id))

@bp.route('/<int:id>/verify-payment', methods=['POST'])
@login_required
def verify_payment(id):
    booking = Booking.query.get_or_404(id)
    if booking.user_id != current_user.id and current_user.role != 'ADMIN':
        abort(403)
        
    if booking.booking_status == 'Cancelled':
        msg = 'This booking is cancelled and cannot be paid for.'
        if request.is_json:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'error')
        return redirect(url_for('booking.details', id=booking.id))
        
    # Requirement 9 & 11: Idempotency & Duplicate Callback Protection
    if booking.booking_status == 'Confirmed' and booking.payment and booking.payment.payment_status == 'Paid':
        msg = f'Booking #{booking.id} is already confirmed with payment reference {booking.payment.payment_reference}.'
        if request.is_json:
            return jsonify({
                'success': True,
                'message': msg,
                'booking_id': booking.id,
                'payment_reference': booking.payment.payment_reference,
                'status': 'Confirmed',
                'payment_status': 'Paid',
                'is_duplicate': True
            }), 200
        flash(msg, 'info')
        return redirect(url_for('booking.details', id=booking.id))

    data = request.get_json(silent=True) or request.form
    order_id = data.get('order_id')
    payment_id = data.get('payment_id')
    signature = data.get('signature')

    # Requirement 11: Invalid payment response validation
    if not order_id or not payment_id or not signature:
        if not booking.payment:
            booking.payment = Payment(booking_id=booking.id, amount=booking.total_amount)
            db.session.add(booking.payment)
        booking.payment.payment_status = 'Failed'
        db.session.commit()
        error_msg = 'Invalid payment payload received. Missing order ID, payment ID, or signature.'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg, 'payment_status': 'Failed'}), 400
        flash(error_msg, 'error')
        return redirect(url_for('booking.details', id=booking.id))

    # Requirement 4, 5, 6: Cryptographic Signature Verification
    # NEVER mark booking as confirmed based only on frontend success!
    is_valid = PaymentGatewayService.verify_payment_signature(order_id, payment_id, signature)
    
    if not is_valid:
        if not booking.payment:
            booking.payment = Payment(booking_id=booking.id, amount=booking.total_amount)
            db.session.add(booking.payment)
            
        booking.payment.payment_status = 'Failed'
        db.session.commit()
        
        error_msg = "Security Alert: Backend signature verification failed! Payment rejected."
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg, 'payment_status': 'Failed', 'booking_status': booking.booking_status}), 400
        flash(error_msg, 'error')
        return redirect(url_for('booking.details', id=booking.id))

    # Requirement 11: Booking becoming unavailable before payment completion (Race condition)
    overlapping_confirmed = Booking.query.filter(
        Booking.vehicle_id == booking.vehicle_id,
        Booking.id != booking.id,
        Booking.booking_status.in_(['Confirmed', 'Active']),
        Booking.start_date <= booking.return_date,
        Booking.return_date >= booking.start_date
    ).first()
    
    if overlapping_confirmed:
        if not booking.payment:
            booking.payment = Payment(booking_id=booking.id, amount=booking.total_amount)
            db.session.add(booking.payment)
        booking.payment.payment_reference = payment_id
        booking.payment.amount = booking.total_amount
        booking.payment.payment_status = 'Refunded'
        booking.payment.paid_at = datetime.utcnow()
        booking.booking_status = 'Cancelled'
        db.session.commit()
        
        error_msg = "This vehicle was booked and confirmed by another reservation while payment was in progress. Your transaction has been recorded and marked for refund."
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg, 'status': 'Cancelled', 'payment_status': 'Refunded'}), 409
        flash(error_msg, 'error')
        return redirect(url_for('booking.details', id=booking.id))

    # Requirement 5: Success Flow
    # Payment: status = PAID, payment_reference = verified reference ID, paid_at = current timestamp
    # Booking: status = CONFIRMED
    if not booking.payment:
        booking.payment = Payment(booking_id=booking.id, amount=booking.total_amount)
        db.session.add(booking.payment)
        
    booking.payment.payment_reference = payment_id
    booking.payment.amount = booking.total_amount
    booking.payment.payment_status = 'Paid'
    booking.payment.paid_at = datetime.utcnow()
    
    booking.booking_status = 'Confirmed'
    db.session.commit()
    
    success_msg = f'Payment of ₹{int(booking.total_amount):,} verified and confirmed! Booking #{booking.id} is now Confirmed.'
    if request.is_json:
        return jsonify({
            'success': True,
            'message': success_msg,
            'booking_id': booking.id,
            'payment_reference': payment_id,
            'status': 'Confirmed',
            'payment_status': 'Paid'
        })
        
    flash(success_msg, 'success')
    return redirect(url_for('booking.details', id=booking.id))

@bp.route('/<int:id>/pay', methods=['POST'])
@login_required
def pay(id):
    booking = Booking.query.get_or_404(id)
    if booking.user_id != current_user.id and current_user.role != 'ADMIN':
        abort(403)
        
    if booking.booking_status == 'Cancelled':
        flash('This booking is cancelled and cannot be paid for.', 'error')
        return redirect(url_for('booking.details', id=booking.id))
        
    # Execute full verified gateway flow: Order -> Gateway Simulation -> Backend Verification -> Confirmation
    order = PaymentGatewayService.create_payment_order(booking)
    gateway_result = PaymentGatewayService.simulate_gateway_processing(order['order_id'], method='Test Card (Express)')
    
    return verify_payment_internal(booking, gateway_result['order_id'], gateway_result['payment_id'], gateway_result['signature'])

def verify_payment_internal(booking, order_id, payment_id, signature):
    is_valid = PaymentGatewayService.verify_payment_signature(order_id, payment_id, signature)
    if not is_valid:
        if not booking.payment:
            booking.payment = Payment(booking_id=booking.id, amount=booking.total_amount)
            db.session.add(booking.payment)
        booking.payment.payment_status = 'Failed'
        db.session.commit()
        flash("Security Alert: Payment signature verification failed.", "error")
        return redirect(url_for('booking.details', id=booking.id))
        
    if not booking.payment:
        booking.payment = Payment(booking_id=booking.id, amount=booking.total_amount)
        db.session.add(booking.payment)
        
    booking.payment.payment_reference = payment_id
    booking.payment.amount = booking.total_amount
    booking.payment.payment_status = 'Paid'
    booking.payment.paid_at = datetime.utcnow()
    booking.booking_status = 'Confirmed'
    db.session.commit()
    
    flash(f'Payment of ₹{int(booking.total_amount):,} verified by Sandbox Gateway! Your booking is now Confirmed.', 'success')
    return redirect(url_for('booking.details', id=booking.id))


@bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
def cancel(id):
    booking = Booking.query.get_or_404(id)
    # Ensure authorization by database ID
    if booking.user_id != current_user.id and current_user.role != 'ADMIN':
        abort(403)
        
    if booking.booking_status in ['Pending', 'Confirmed']:
        booking.booking_status = 'Cancelled'
        if booking.payment:
            if booking.payment.payment_status == 'Paid':
                booking.payment.payment_status = 'Refunded'
                flash(f'Booking #{booking.id} cancelled successfully. Your payment of ₹{int(booking.total_amount):,} will be refunded.', 'success')
            else:
                booking.payment.payment_status = 'Cancelled'
                flash(f'Booking #{booking.id} cancelled successfully.', 'success')
        else:
            flash(f'Booking #{booking.id} cancelled successfully.', 'success')
        db.session.commit()
    else:
        flash('This booking cannot be cancelled because it is already active, completed, or cancelled.', 'error')
        
    next_url = request.referrer or url_for('booking.details', id=booking.id)
    return redirect(next_url)

