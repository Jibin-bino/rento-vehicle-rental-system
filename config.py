import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'rento.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PAYMENT_KEY_ID = os.environ.get('PAYMENT_KEY_ID') or os.environ.get('PAYMENT_KEY') or 'rzp_test_rento_sandbox_key_99'
    PAYMENT_KEY_SECRET = os.environ.get('PAYMENT_KEY_SECRET') or os.environ.get('PAYMENT_SECRET') or 'rento_test_secret_hmac_auth_88'
