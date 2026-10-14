import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app.models import db
from app.models.user import User

app = create_app()

with app.app_context():
    admin = User.query.filter_by(email='admin@rento.com').first()
    if not admin:
        admin = User(name='Admin User', email='admin@rento.com', role='ADMIN')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: admin@rento.com / admin123")
    else:
        admin.role = 'ADMIN'
        admin.set_password('admin123')
        db.session.commit()
        print("Admin user already exists, reset password to admin123 and ensured role=ADMIN.")
