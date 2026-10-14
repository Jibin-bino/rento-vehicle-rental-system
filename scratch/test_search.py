import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app.models.booking import Booking
from datetime import datetime, date

app = create_app()

with app.app_context():
    # 1. Test location search
    with app.test_client() as client:
        response = client.get('/vehicles/?location=Kochi')
        assert response.status_code == 200
        print("Location search Kochi works (200 OK)")

    # 2. Test date search
    with app.test_client() as client:
        response = client.get('/vehicles/?start_date=2024-12-01&return_date=2024-12-05')
        assert response.status_code == 200
        print("Date search works (200 OK)")

    # 3. Test location and date search
    with app.test_client() as client:
        response = client.get('/vehicles/?location=Mumbai&start_date=2024-12-01&return_date=2024-12-05')
        assert response.status_code == 200
        print("Location + Date search works (200 OK)")

print("Search route tests completed successfully.")
