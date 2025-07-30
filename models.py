from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from app import app
from werkzeug.security import generate_password_hash

db = SQLAlchemy(app)

# --------------------------
# USER TABLE
# --------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)  # Store hashed passwords
    is_admin = db.Column(db.Boolean, default=False)  # Flag to identify admin

    full_name = db.Column(db.String(128), nullable=False)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), nullable=True)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    address = db.relationship('Address', backref='residents', lazy=True)
    vehicles = db.relationship('Vehicle', backref='owner', lazy=True, cascade='all, delete-orphan')
    reservations = db.relationship('Reservation', backref='user', lazy=True, cascade='all, delete-orphan')


#---------------------------
# ADDRESS TABLE
#---------------------------
class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    house_number = db.Column(db.String(32), nullable=True)
    address = db.Column(db.String(128), nullable=False)
    city = db.Column(db.String(64), nullable=False)
    district = db.Column(db.String(64), nullable=True)
    state = db.Column(db.String(64), nullable=False)
    country = db.Column(db.String(64), nullable=False, default="India")
    pincode = db.Column(db.String(6), nullable=False)


# --------------------------
# VEHICLE TABLE
# --------------------------
class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_number = db.Column(db.String(10), nullable=False, unique=True)
    vehicle_type = db.Column(db.String(32), nullable=False)  # e.g., 'Car', 'Bike'
    is_parked_in = db.Column(db.Boolean, default=False)
    
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# --------------------------
# PARKING LOT TABLE
# --------------------------
class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(128), nullable=False)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id'), unique=True, nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    max_spots = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    spots = db.relationship('ParkingSpot', backref='lot', lazy=True, cascade='all, delete-orphan')
    address = db.relationship('Address', backref=db.backref('parking_lot', uselist=False), lazy=True)



# --------------------------
# PARKING SPOT TABLE
# --------------------------
class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    spot_number = db.Column(db.String(16), nullable=False)
    status = db.Column(db.String(1), default='A', nullable=False)  # 'A' for available, 'O' for occupied
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    reservations = db.relationship('Reservation', backref='spot', lazy=True, cascade='all, delete-orphan')


# --------------------------
# RESERVATION TABLE
# --------------------------
class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)

    status = db.Column(db.String(1), default='A', nullable=False)  # 'A' for available, 'R' for released
    parking_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    leaving_timestamp = db.Column(db.DateTime, nullable=True)
    parking_cost = db.Column(db.Float, nullable=True)  # Can be calculated

    vehicle = db.relationship('Vehicle', backref='reservations', lazy=True)


with app.app_context():
    db.create_all()
    # If admin already exists
    admin = User.query.filter_by(is_admin=True).first()

    if not admin:
        password_hash = generate_password_hash('admin')

        admin_address = Address(address='AdminHouse', city='AdminCity', state='AdminState', country='India', pincode='000000')
        db.session.add(admin_address)
        db.session.commit()

        admin = User(email='admin@gmail.com', password=password_hash, full_name='Admin', is_admin=True, address_id=admin_address.id)
        db.session.add(admin)
        db.session.commit()