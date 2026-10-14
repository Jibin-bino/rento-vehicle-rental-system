from app.models import db

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    vehicles = db.relationship('Vehicle', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'
