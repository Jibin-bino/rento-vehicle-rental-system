from app import create_app
from app.models import db, Category, Vehicle

app = create_app()

def seed_data():
    with app.app_context():
        # Check if we already have data
        if Category.query.first():
            print("Database already seeded!")
            return

        print("Seeding Categories...")
        categories = ['Sedan', 'SUV', 'Scooter', 'Sports Bike', 'Van', 'Traveller']
        cat_objects = {}
        for c in categories:
            cat = Category(name=c)
            db.session.add(cat)
            cat_objects[c] = cat
        db.session.commit()

        print("Seeding Vehicles...")
        vehicles = [
            {
                "name": "Honda City", "brand": "Honda", "model": "City", 
                "category": "Sedan", "price_per_day": 1500, "fuel_type": "Petrol",
                "transmission": "Automatic", "seats": 5, "location": "Kochi",
                "image": "honda-city.jpg"
            },
            {
                "name": "Hyundai Verna", "brand": "Hyundai", "model": "Verna", 
                "category": "Sedan", "price_per_day": 1400, "fuel_type": "Petrol",
                "transmission": "Manual", "seats": 5, "location": "Mumbai",
                "image": "hyundai-verna.jpg"
            },
            {
                "name": "Hyundai Creta", "brand": "Hyundai", "model": "Creta", 
                "category": "SUV", "price_per_day": 2000, "fuel_type": "Diesel",
                "transmission": "Automatic", "seats": 5, "location": "Delhi",
                "image": "hyundai-creta.jpg"
            },
            {
                "name": "Toyota Innova", "brand": "Toyota", "model": "Innova", 
                "category": "SUV", "price_per_day": 2200, "fuel_type": "Diesel",
                "transmission": "Manual", "seats": 7, "location": "Kochi",
                "image": "toyota-innova.jpg"
            },
            {
                "name": "Honda Activa", "brand": "Honda", "model": "Activa", 
                "category": "Scooter", "price_per_day": 500, "fuel_type": "Petrol",
                "transmission": "Automatic", "seats": 2, "location": "Kochi",
                "image": "honda-activa.jpg"
            },
            {
                "name": "TVS Ntorq", "brand": "TVS", "model": "Ntorq", 
                "category": "Scooter", "price_per_day": 550, "fuel_type": "Petrol",
                "transmission": "Automatic", "seats": 2, "location": "Mumbai",
                "image": "tvs-ntorq.jpg"
            },
            {
                "name": "Yamaha R15", "brand": "Yamaha", "model": "R15", 
                "category": "Sports Bike", "price_per_day": 1000, "fuel_type": "Petrol",
                "transmission": "Manual", "seats": 2, "location": "Delhi",
                "image": "yamaha-r15.jpg"
            },
            {
                "name": "KTM Duke", "brand": "KTM", "model": "Duke", 
                "category": "Sports Bike", "price_per_day": 1200, "fuel_type": "Petrol",
                "transmission": "Manual", "seats": 2, "location": "Kochi",
                "image": "ktm-duke.jpg"
            },
            {
                "name": "Maruti Eeco", "brand": "Maruti", "model": "Eeco", 
                "category": "Van", "price_per_day": 1800, "fuel_type": "Petrol",
                "transmission": "Manual", "seats": 7, "location": "Kochi",
                "image": "maruti-eeco.jpg"
            },
            {
                "name": "Force Traveller", "brand": "Force", "model": "Traveller", 
                "category": "Traveller", "price_per_day": 3500, "fuel_type": "Diesel",
                "transmission": "Manual", "seats": 12, "location": "Kochi",
                "image": "force-traveller.jpg"
            }
        ]

        for v_data in vehicles:
            cat_name = v_data.pop('category')
            cat = cat_objects[cat_name]
            v = Vehicle(category_id=cat.id, **v_data)
            db.session.add(v)
            
        db.session.commit()
        print("Data seeded successfully!")

if __name__ == '__main__':
    seed_data()
