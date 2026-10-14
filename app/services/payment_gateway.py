import os
import hmac
import hashlib
import uuid
from datetime import datetime
from flask import current_app

class PaymentGatewayService:
    @staticmethod
    def get_credentials():
        """Retrieve sandbox payment gateway credentials securely from environment configuration."""
        from flask import current_app, has_app_context
        if has_app_context():
            key_id = current_app.config.get('PAYMENT_KEY_ID') or os.environ.get('PAYMENT_KEY_ID') or 'rzp_test_rento_sandbox_key_99'
            key_secret = current_app.config.get('PAYMENT_KEY_SECRET') or os.environ.get('PAYMENT_KEY_SECRET') or 'rento_test_secret_hmac_auth_88'
        else:
            key_id = os.environ.get('PAYMENT_KEY_ID') or 'rzp_test_rento_sandbox_key_99'
            key_secret = os.environ.get('PAYMENT_KEY_SECRET') or 'rento_test_secret_hmac_auth_88'
        return key_id, key_secret

    @classmethod
    def create_payment_order(cls, booking):
        """
        Step 2: Create a secure Payment Order with the payment gateway.
        Generates a unique order ID and returns order metadata without exposing the secret key.
        """
        key_id, key_secret = cls.get_credentials()
        order_id = f"order_rento_{booking.id}_{uuid.uuid4().hex[:10]}"
        amount_in_paise = int(round(booking.total_amount * 100))
        
        # Create server signature token for order integrity
        order_token = hmac.new(
            key_secret.encode('utf-8'),
            f"{order_id}:{booking.id}:{amount_in_paise}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return {
            'order_id': order_id,
            'booking_id': booking.id,
            'amount': booking.total_amount,
            'amount_in_paise': amount_in_paise,
            'currency': 'INR',
            'key_id': key_id, # Public key ID is safe to share with frontend
            'order_token': order_token
        }

    @classmethod
    def simulate_gateway_processing(cls, order_id, method='Test Card'):
        """
        Step 3: Sandbox Payment Gateway simulator.
        Simulates the gateway receiving payment details, authorizing the transaction,
        and producing a cryptographically signed payment result.
        """
        key_id, key_secret = cls.get_credentials()
        payment_id = f"pay_rento_{uuid.uuid4().hex[:14].upper()}"

        # Standard gateway signature algorithm: HMAC-SHA256(order_id + "|" + payment_id, secret)
        payload = f"{order_id}|{payment_id}"
        signature = hmac.new(
            key_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return {
            'order_id': order_id,
            'payment_id': payment_id,
            'signature': signature,
            'method': method,
            'status': 'captured',
            'timestamp': datetime.utcnow().isoformat()
        }

    @classmethod
    def verify_payment_signature(cls, order_id, payment_id, signature):
        """
        Step 5: Backend Verification.
        Crucial security check: Recomputes the HMAC-SHA256 signature using the secret key
        stored on the server and verifies that it exactly matches the gateway response.
        Never trust frontend success alone!
        """
        if not order_id or not payment_id or not signature:
            return False

        key_id, key_secret = cls.get_credentials()
        payload = f"{order_id}|{payment_id}"
        expected_signature = hmac.new(
            key_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, str(signature).strip())
