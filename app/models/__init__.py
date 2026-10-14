from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User
from .category import Category
from .vehicle import Vehicle
from .booking import Booking
from .payment import Payment
