from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField, FloatField, IntegerField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange
from app.models.user import User
from datetime import date

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('LOGIN')

class RegistrationForm(FlaskForm):
    name = StringField('Full Name *', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email Address *', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number')
    password = PasswordField('Password *', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password *', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('REGISTER')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email address already registered.')

class BookingForm(FlaskForm):
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    return_date = DateField('Return Date', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Book Now')

    def validate_start_date(self, start_date):
        if start_date.data and start_date.data < date.today():
            raise ValidationError('Start date cannot be in the past.')

    def validate_return_date(self, return_date):
        if self.start_date.data and return_date.data:
            if return_date.data < self.start_date.data:
                raise ValidationError('Return date cannot be before start date.')
            if (return_date.data - self.start_date.data).days < 1:
                raise ValidationError('Minimum rental period is 1 day.')

class VehicleForm(FlaskForm):
    name = StringField('Vehicle Name *', validators=[DataRequired(), Length(max=100)])
    brand = StringField('Brand *', validators=[DataRequired(), Length(max=50)])
    model = StringField('Model *', validators=[DataRequired(), Length(max=50)])
    category_id = SelectField('Category *', coerce=int, validators=[DataRequired()])
    price_per_day = FloatField('Price per Day (₹) *', validators=[DataRequired(), NumberRange(min=1)])
    fuel_type = SelectField('Fuel Type *', choices=[('Petrol', 'Petrol'), ('Diesel', 'Diesel'), ('Electric', 'Electric'), ('CNG', 'CNG'), ('Hybrid', 'Hybrid')])
    transmission = SelectField('Transmission *', choices=[('Automatic', 'Automatic'), ('Manual', 'Manual')])
    seats = IntegerField('Seats *', validators=[DataRequired(), NumberRange(min=1, max=50)])
    location = StringField('Location *', validators=[DataRequired(), Length(max=100)])
    status = SelectField('Status *', choices=[('Active', 'Active'), ('Inactive', 'Inactive'), ('Maintenance', 'Maintenance')])
    description = TextAreaField('Description')
    image = StringField('Image Filename (e.g. honda-city.jpg)')
    submit = SubmitField('Save Vehicle')

