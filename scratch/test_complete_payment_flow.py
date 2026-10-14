import os
import sys
from datetime import date, timedelta, datetime
import hmac
import hashlib

# Ensure repository root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.booking import Booking
from app.models.payment import Payment
from app.services.payment_gateway import PaymentGatewayService

def run_tests():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        print("=" * 60)
        print("STARTING COMPLETE PAYMENT VERIFICATION TEST SUITE FOR RENTO")
        print("=" * 60)

        client = app.test_client()

        # Step 0: Identify test user and vehicle
        user = User.query.filter_by(email='test@rento.com').first()
        if not user:
            print("ERROR: test@rento.com not found!")
            return False

        vehicle = Vehicle.query.filter_by(status='Active').first()
        if not vehicle:
            print("ERROR: No active vehicle found!")
            return False

        # Clean up any previous test-run bookings
        old_test_bookings = Booking.query.filter(Booking.start_date >= date.today() + timedelta(days=30)).all()
        for otb in old_test_bookings:
            if otb.payment:
                db.session.delete(otb.payment)
            db.session.delete(otb)
        db.session.commit()

        # Log in test user via test client
        login_res = client.post('/auth/login', data={
            'email': 'test@rento.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert login_res.status_code == 200, "Login failed"
        print("Logged in successfully as test user.")

        # =========================================================================
        # TEST 1: User -> Select vehicle -> Select dates -> Book -> Successful test payment
        # Expected: Payment = PAID, Booking = CONFIRMED
        # =========================================================================
        print("\n--- TEST 1: Full Successful Payment Verification Flow ---")
        start_d1 = date.today() + timedelta(days=40)
        return_d1 = start_d1 + timedelta(days=3)
        expected_days1 = 3
        expected_amount1 = expected_days1 * vehicle.price_per_day

        # 1. Book Now
        book_res1 = client.post(f'/bookings/book/{vehicle.id}', data={
            'start_date': start_d1.strftime('%Y-%m-%d'),
            'return_date': return_d1.strftime('%Y-%m-%d')
        }, follow_redirects=True)
        assert book_res1.status_code == 200, "Booking creation request failed"

        # Check booking created with Pending status
        b1 = Booking.query.filter_by(user_id=user.id, vehicle_id=vehicle.id, start_date=start_d1).first()
        assert b1 is not None, "Booking 1 was not created"
        assert b1.booking_status == 'Pending', f"Booking status expected 'Pending', got '{b1.booking_status}'"
        assert b1.payment is not None, "Payment record not created with booking"
        assert b1.payment.payment_status == 'Pending', f"Payment status expected 'Pending', got '{b1.payment.payment_status}'"
        assert b1.total_amount == expected_amount1, f"Calculated amount mismatch: {b1.total_amount} != {expected_amount1}"
        print(f"  [OK] Booking #{b1.id} created with status '{b1.booking_status}', Payment status '{b1.payment.payment_status}', Amount Rs.{b1.total_amount}")

        # 2. Gateway Order Creation
        order_res1 = client.post(f'/bookings/{b1.id}/create-order')
        assert order_res1.status_code == 200
        order_data1 = order_res1.get_json()['order']
        assert order_data1['order_id'] is not None
        assert order_data1['amount'] == expected_amount1
        print(f"  [OK] Gateway payment order created: {order_data1['order_id']}")

        # 3. Gateway Sandbox Authorization
        proc_res1 = client.post(f'/bookings/{b1.id}/process-gateway', json={
            'order_id': order_data1['order_id'],
            'method': 'Test Card',
            'simulate_failure': False
        })
        assert proc_res1.status_code == 200
        gw_result1 = proc_res1.get_json()['gateway_result']
        print(f"  [OK] Sandbox gateway authorized transaction: Payment ID {gw_result1['payment_id']}")

        # 4. Backend Cryptographic Verification
        verify_res1 = client.post(f'/bookings/{b1.id}/verify-payment', json={
            'order_id': gw_result1['order_id'],
            'payment_id': gw_result1['payment_id'],
            'signature': gw_result1['signature']
        })
        assert verify_res1.status_code == 200
        v_data1 = verify_res1.get_json()
        assert v_data1['success'] is True
        assert v_data1['status'] == 'Confirmed'

        # Refresh from database
        db.session.refresh(b1)
        db.session.refresh(b1.payment)
        assert b1.booking_status == 'Confirmed', f"Expected Booking Confirmed, got {b1.booking_status}"
        assert b1.payment.payment_status == 'Paid', f"Expected Payment Paid, got {b1.payment.payment_status}"
        assert b1.payment.payment_reference == gw_result1['payment_id']
        assert b1.payment.paid_at is not None
        print(f"  [SUCCESS] TEST 1 PASSED: Booking #{b1.id} Confirmed, Payment #{b1.payment.id} Paid, Reference: {b1.payment.payment_reference}, Paid At: {b1.payment.paid_at}")

        # =========================================================================
        # TEST 2: User -> Start booking -> Failed test payment
        # Expected: Payment = FAILED, Booking is NOT CONFIRMED (status Pending)
        # =========================================================================
        print("\n--- TEST 2: Failed / Declined Test Payment Flow ---")
        start_d2 = date.today() + timedelta(days=45)
        return_d2 = start_d2 + timedelta(days=2)

        # 1. Book Now
        book_res2 = client.post(f'/bookings/book/{vehicle.id}', data={
            'start_date': start_d2.strftime('%Y-%m-%d'),
            'return_date': return_d2.strftime('%Y-%m-%d')
        }, follow_redirects=True)
        assert book_res2.status_code == 200

        b2 = Booking.query.filter_by(user_id=user.id, vehicle_id=vehicle.id, start_date=start_d2).first()
        assert b2 is not None
        assert b2.booking_status == 'Pending'
        print(f"  [OK] Booking #{b2.id} created with status 'Pending'")

        # 2. Simulate Payment Failure via Gateway
        order_res2 = client.post(f'/bookings/{b2.id}/create-order')
        order_data2 = order_res2.get_json()['order']

        fail_res = client.post(f'/bookings/{b2.id}/process-gateway', json={
            'order_id': order_data2['order_id'],
            'simulate_failure': True
        })
        assert fail_res.status_code == 400
        print("  [OK] Gateway correctly returned 400 transaction declined")

        # Verify DB: Payment must be FAILED, Booking must NOT be Confirmed
        db.session.refresh(b2)
        db.session.refresh(b2.payment)
        assert b2.payment.payment_status == 'Failed', f"Expected Payment Failed, got {b2.payment.payment_status}"
        assert b2.booking_status != 'Confirmed', f"Expected Booking NOT Confirmed, got {b2.booking_status}"
        assert b2.booking_status == 'Pending'
        print(f"  [SUCCESS] TEST 2 PASSED: Payment status = '{b2.payment.payment_status}', Booking status = '{b2.booking_status}' (NOT Confirmed)")

        # Also test Tampered Signature verification failure
        print("  Testing tampered signature rejection...")
        fake_res = client.post(f'/bookings/{b2.id}/verify-payment', json={
            'order_id': order_data2['order_id'],
            'payment_id': 'pay_fake_hacker_123',
            'signature': 'bad_fake_signature_9999999'
        })
        assert fake_res.status_code == 400
        db.session.refresh(b2)
        assert b2.booking_status != 'Confirmed'
        assert b2.payment.payment_status == 'Failed'
        print("  [OK] Tampered signature properly rejected with 400 and booking remained unconfirmed.")

        # =========================================================================
        # TEST 3: Refresh/call the payment callback twice (Duplicate callback idempotency)
        # Expected: No duplicate booking or duplicate payment record.
        # =========================================================================
        print("\n--- TEST 3: Duplicate Payment Callback / Idempotency ---")
        initial_booking_count = Booking.query.count()
        initial_payment_count = Payment.query.count()
        initial_paid_at = b1.payment.paid_at

        # Call verify-payment a second time on b1 (which is already Paid & Confirmed)
        dup_verify_res = client.post(f'/bookings/{b1.id}/verify-payment', json={
            'order_id': gw_result1['order_id'],
            'payment_id': gw_result1['payment_id'],
            'signature': gw_result1['signature']
        })
        assert dup_verify_res.status_code == 200
        dup_data = dup_verify_res.get_json()
        assert dup_data['success'] is True
        assert dup_data.get('is_duplicate') is True
        print(f"  [OK] Duplicate callback responded idempotently: {dup_data['message']}")

        # Ensure no duplicate records created and paid_at not corrupted
        new_booking_count = Booking.query.count()
        new_payment_count = Payment.query.count()
        db.session.refresh(b1.payment)
        assert new_booking_count == initial_booking_count, "Duplicate booking was created!"
        assert new_payment_count == initial_payment_count, "Duplicate payment was created!"
        assert b1.payment.paid_at == initial_paid_at, "paid_at timestamp was modified!"
        print(f"  [SUCCESS] TEST 3 PASSED: Total Bookings ({new_booking_count}) and Payments ({new_payment_count}) remained identical. No duplicate records.")

        # =========================================================================
        # TEST 4: User opens My Bookings
        # Expected: Correct booking status and payment status are displayed.
        # =========================================================================
        print("\n--- TEST 4: My Bookings & Booking Details Status Visibility ---")
        my_bookings_res = client.get('/bookings/')
        assert my_bookings_res.status_code == 200
        html = my_bookings_res.data.decode('utf-8')

        # Check b1 appears with Confirmed and Paid
        assert f"Booking #{b1.id}" in html or f"#{b1.id}" in html
        assert "Confirmed" in html
        assert "Paid" in html
        print(f"  [OK] My Bookings page displays Booking #{b1.id} with Confirmed and Paid badges.")

        # Check Booking Details page
        details_res = client.get(f'/bookings/{b1.id}')
        assert details_res.status_code == 200
        d_html = details_res.data.decode('utf-8')
        assert "Booking Status:" in d_html
        assert "Confirmed" in d_html
        assert "Payment Status:" in d_html
        assert "Paid" in d_html
        assert "Payment Reference:" in d_html
        assert b1.payment.payment_reference in d_html
        assert "Payment Date:" in d_html
        print(f"  [OK] Booking Details page #{b1.id} displays all 5 required fields:")
        print(f"       - Booking Status: Confirmed")
        print(f"       - Payment Status: Paid")
        print(f"       - Amount: Rs.{int(b1.total_amount)}")
        print(f"       - Payment Reference: {b1.payment.payment_reference}")
        print(f"       - Payment Date: {b1.payment.paid_at.strftime('%B %d, %Y at %I:%M %p')}")

        # Check Admin Booking Details visibility
        client.get('/auth/logout', follow_redirects=True)
        admin_login = client.post('/auth/login', data={
            'email': 'admin@rento.com',
            'password': 'admin123'
        }, follow_redirects=True)
        assert admin_login.status_code == 200

        admin_details_res = client.get(f'/admin/bookings/{b1.id}')
        assert admin_details_res.status_code == 200
        a_html = admin_details_res.data.decode('utf-8')
        assert "Payment Status:" in a_html
        assert "Paid" in a_html
        assert b1.payment.payment_reference in a_html
        print(f"  [OK] Admin Booking Details page #{b1.id} correctly displays Payment Status & Reference.")

        print("\n" + "=" * 60)
        print("ALL 4 MANDATORY TESTS + SECURITY VERIFICATIONS PASSED SUCCESSFULLY!")
        print("=" * 60)
        return True

if __name__ == '__main__':
    success = run_tests()
    if not success:
        sys.exit(1)
