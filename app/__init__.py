from flask import Flask
from config import Config
from app.models import db
from flask_migrate import Migrate
from flask_login import LoginManager

migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    from app.models.user import User
    @login.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # Register blueprints
    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.routes.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.vehicle import bp as vehicle_bp
    app.register_blueprint(vehicle_bp, url_prefix='/vehicles')

    from app.routes.booking import bp as booking_bp
    app.register_blueprint(booking_bp, url_prefix='/bookings')

    from app.routes.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app
