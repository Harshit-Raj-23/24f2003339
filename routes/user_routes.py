from flask import Blueprint, request, render_template, redirect, flash, url_for, session
from models import db, User, Vehicle, Address, ParkingLot, ParkingSpot, Reservation
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from werkzeug.security import check_password_hash, generate_password_hash
from decorators import auth_required
from math import ceil


user_bp = Blueprint('user', __name__)


# --------------------------
# Home Page
# --------------------------
@user_bp.route('/', methods=['GET'])
def index():
    user_logged_in = 'user_id' in session
    current_time = datetime.utcnow()
    query = request.args.get('query', '').strip()

    if query:
        search = f'%{query}%'
        parking_lots = (
                        ParkingLot.query
                        .join(ParkingLot.address)
                        .filter(
                            or_(
                                ParkingLot.prime_location_name.ilike(search),
                                Address.address.ilike(search),
                                Address.city.ilike(search),
                                Address.state.ilike(search),
                                Address.pincode.ilike(search)
                            )
                        ).all()
        )
    else:
        parking_lots = ParkingLot.query.all()
    
    if user_logged_in:
        all_reservations = (
            Reservation.query
            .filter_by(user_id=session['user_id'])
            .order_by(Reservation.parking_timestamp.desc())
            .limit(4)
            .all()
        )

        active_reservations = (
            Reservation.query
            .filter_by(user_id=session['user_id'], status="A")
            .order_by(Reservation.parking_timestamp.desc())
            .all()
        )

        return render_template('user/index.html',
                            user_logged_in=user_logged_in,
                            parking_lots=parking_lots,
                            all_reservations=all_reservations,
                            active_reservations=active_reservations,
                            current_time=current_time,
                            query=query
                            )
    
    return render_template('user/index.html',
                            user_logged_in=user_logged_in,
                            parking_lots=parking_lots,
                            current_time=current_time
                            )



# --------------------------
# View slot Page
# --------------------------
@user_bp.route('/<int:lot_id>/view_slot', methods=['GET'])
@auth_required
def view_slot(lot_id):
    user_logged_in = 'user_id' in session
    lot = ParkingLot.query.get(lot_id)
    vehicles = Vehicle.query.filter_by(user_id=session['user_id'], is_parked_in=False).all()

    return render_template('user/view_spot.html', user_logged_in=user_logged_in, lot=lot, vehicles=vehicles)


# --------------------------
# Spot Booking Page
# --------------------------
@user_bp.route('/book_spot/<int:spot_id>', methods=['POST'])
@auth_required
def book_spot_post(spot_id):
    spot = ParkingSpot.query.get(spot_id)
    vehicle_id = request.form.get('vehicle_id')
    vehicle = Vehicle.query.get(vehicle_id)

    if not spot:
        flash('Spot does not exist.', 'danger')
        return redirect(url_for('user.view_spot'))
    
    if spot.status != 'A':
        flash('Spot is not available.', 'danger')
        return redirect(url_for('user.view_spot'))
    
    if not vehicle or vehicle.is_parked_in:
        flash('Invalid or already parked vehicle selected.', 'danger')
        return redirect(url_for('user.view_spot'))

    spot.status = 'O'
    vehicle.is_parked_in = True

    new_reservation = Reservation(
        user_id=session['user_id'],
        spot_id=spot.id,
        vehicle_id=vehicle.id,
        parking_timestamp=datetime.utcnow(),
        status='A'
    )

    db.session.add(new_reservation)
    db.session.commit()

    flash('Spot booked successfully.', 'success')
    return redirect(url_for('user.index'))



# --------------------------
# Slot Releasing Page
# --------------------------
@user_bp.route('/<int:booking_id>/release_slot', methods=['POST'])
@auth_required
def release_slot(booking_id):
    booking = Reservation.query.get(booking_id)

    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('user.index'))
    
    if booking.leaving_timestamp:
        flash('Slot already released.', 'danger')
        return redirect(url_for('user.index'))

    now = datetime.utcnow()

    price = booking.spot.lot.price_per_hour
    duration = ceil((now - booking.parking_timestamp).total_seconds() / 3600)
    total_cost = duration * price

    booking.spot.status = 'A'  # 'A' for available
    
    if booking.vehicle:
        booking.vehicle.is_parked_in = False
    
    booking.status = 'R'  # 'R' for released
    
    booking.leaving_timestamp = now
    booking.parking_cost = total_cost

    db.session.commit()

    flash(f'Slot released successfully. Total cost: ₹{total_cost}', 'success')
    return redirect(url_for('user.index'))


# --------------------------
# Profile Page
# --------------------------
@user_bp.route('/profile', methods=['GET'])
@auth_required
def profile():
    user_logged_in = 'user_id' in session

    user = User.query.get(session['user_id'])

    return render_template('user/profile.html', 
                           user_logged_in=user_logged_in,
                           user=user
                           )


# --------------------------
# Add Vehicle Page
# --------------------------
@user_bp.route('/add_vehicle', methods=['POST'])
@auth_required
def add_vehicle():

    vehicle_number = request.form.get('vehicle_number')
    vehicle_type = request.form.get('vehicle_type')

    vehicle = Vehicle.query.filter_by(vehicle_number=vehicle_number).first()

    if vehicle:
        flash('Vehicle already exists. Add another vehicle.', 'danger')
        return redirect(url_for('user.add_vehicle'))
    
    new_vehicle = Vehicle(vehicle_number=vehicle_number,
                          vehicle_type=vehicle_type,
                          user_id=session['user_id']
                          )
    
    db.session.add(new_vehicle)
    db.session.commit()

    flash('Vehicle added successfully.', 'success')
    return redirect(url_for('user.profile'))


# --------------------------
# Edit Vehicle Page
# --------------------------
@user_bp.route('/edit_vehicle/<int:vehicle_id>', methods=['POST'])
@auth_required
def edit_vehicle(vehicle_id):

    vehicle_number = request.form.get('vehicle_number')
    vehicle_type = request.form.get('vehicle_type')

    if not vehicle_number or not vehicle_type:
        flash('Please fill all details.', 'danger')
        return redirect(url_for('user.edit_vehicle'))

    vehicle = Vehicle.query.get(vehicle_id)

    vehicle.vehicle_number = vehicle_number
    vehicle.vehicle_type = vehicle_type

    db.session.commit()

    flash('Vehicle updated successfully.', 'success')
    return redirect(url_for('user.profile'))


# --------------------------
# Delete Vehicle Page
# --------------------------
@user_bp.route('/delete_vehicle/<int:vehicle_id>', methods=['POST'])
@auth_required
def delete_vehicle(vehicle_id):
    vehicle = Vehicle.query.get(vehicle_id)

    if not vehicle:
        flash('Cannot delete vehicle. Vehicle does not exist.', 'danger')
        return redirect(url_for('user.profile'))
    
    db.session.delete(vehicle)
    db.session.commit()

    flash('Vehicle deleted successfully.', 'success')
    return redirect(url_for('user.profile'))


# --------------------------
# Add Address Page
# --------------------------
@user_bp.route('/add_address', methods=['POST'])
@auth_required
def add_address():

    house_number = request.form.get('house_number')
    address = request.form.get('address')
    city = request.form.get('city')
    district = request.form.get('district')
    pincode = request.form.get('pincode')
    state = request.form.get('state')
    country = request.form.get('country')

    if not house_number or not address or not city or not district or not pincode or not state:
        flash('Please fill all details.', 'danger')
        return redirect(url_for('user.add_address'))
    
    new_address = Address(house_number=house_number,
                          address=address,
                          city=city,
                          district=district,
                          pincode=pincode,
                          state=state,
                          country=country)
    
    db.session.add(new_address)

    user = User.query.get(session['user_id'])

    user.address_id = new_address.id

    db.session.commit()

    flash('Address added successfully.', 'success')
    return redirect(url_for('user.profile'))


# --------------------------
# Edit Address Page
# --------------------------
@user_bp.route('/edit_address', methods=['POST'])
@auth_required
def edit_address():

    house_number = request.form.get('house_number')
    address = request.form.get('address')
    city = request.form.get('city')
    district = request.form.get('district')
    pincode = request.form.get('pincode')
    state = request.form.get('state')
    country = request.form.get('country')

    if not house_number or not address or not city or not district or not pincode or not state:
        flash('Please fill all details.', 'danger')
        return redirect(url_for('user.edit_address'))
    
    user = User.query.get(session['user_id'])

    user.address.house_number = house_number
    user.address.address = address
    user.address.city = city
    user.address.district = district
    user.address.pincode = pincode
    user.address.state = state
    user.address.country = country

    db.session.commit()

    flash('Address updated successfully.', 'success')
    return redirect(url_for('user.profile'))


# --------------------------
# Update Profile
# --------------------------
@user_bp.route('/update_profile', methods=['POST'])
@auth_required
def update_profile():

    full_name = request.form.get('full_name')
    email = request.form.get('email')

    if not full_name or not email:
        flash('Please fill all details.', 'danger')
        return redirect(url_for('user.profile'))
    
    user = User.query.filter_by(email=email).first()

    if user and user.id != session['user_id']:
        flash('Email already taken! Please use another Email ID.', 'danger')
        return redirect(url_for('user.profile'))
    
    user = User.query.get(session['user_id'])

    user.full_name = full_name
    user.email = email
    
    db.session.commit()

    flash('Profile updated successfully.', 'success')
    return redirect(url_for('user.profile'))


# --------------------------
# Update Password
# --------------------------
@user_bp.route('/update_password', methods=['POST'])
@auth_required
def update_password():
    
    user = User.query.get(session['user_id'])

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_new_password = request.form.get('confirm_new_password')

    if not current_password or not new_password or not confirm_new_password:
        flash('Please fill all details.', 'danger')
        return redirect(url_for('user.profile'))
    
    if not check_password_hash(user.password, current_password):
        flash('Incorrect current password.', 'danger')
        return redirect(url_for('user.profile'))
    
    if new_password != confirm_new_password:
        flash('Password mismatched!', 'danger')
        return redirect(url_for('user.profile'))
    
    if current_password == new_password:
        flash('New password is same as current passsword.', 'danger')
        return redirect(url_for('user.profile'))

    user.password = generate_password_hash(new_password)

    db.session.commit()

    flash('Password changed successfully.', 'success')
    return redirect(url_for('user.profile'))


# --------------------------
# History Page
# --------------------------
@user_bp.route('/history', methods=['GET'])
@auth_required
def history():
    user_logged_in = 'user_id' in session
    current_time = datetime.utcnow()
    query = request.args.get('query', '').strip()

    if query:
        search = f'%{query}%'
        reservations = (
                        Reservation.query
                        .join(ParkingSpot, Reservation.spot)
                        .join(Vehicle, Reservation.vehicle)
                        .filter_by(user_id=session['user_id'])
                        .filter(
                            or_(
                                ParkingSpot.spot_number.ilike(search),
                                Vehicle.vehicle_number.ilike(search),
                                Vehicle.vehicle_type.ilike(search),
                            )
                        )
                        .order_by(Reservation.parking_timestamp.desc())
                        .all()
        )
    else:
        reservations = (
                    Reservation.query
                    .filter_by(user_id=session['user_id'])
                    .order_by(Reservation.parking_timestamp.desc())
                    .all()
                )

    return render_template('user/history.html', user_logged_in=user_logged_in, reservations=reservations, current_time=current_time, query=query)

# --------------------------
# Summary Page
# --------------------------
@user_bp.route('/summary', methods=['GET'])
@auth_required
def summary():
    user_logged_in = 'user_id' in session
    user = User.query.get(session['user_id'])

    total_bookings = Reservation.query.filter_by(user_id=user.id).count()
    active_bookings = Reservation.query.filter_by(user_id=user.id, leaving_timestamp=None).count()
    total_vehicles = Vehicle.query.filter_by(user_id=user.id).count()
    all_costs = [r.parking_cost for r in Reservation.query.filter_by(user_id=user.id).filter(Reservation.parking_cost != None).all()]
    total_spent = sum(all_costs)

    favourite_lot = db.session.query(
        ParkingLot.prime_location_name,
        func.count(Reservation.id).label('count')
    ).join(ParkingLot.spots).join(ParkingSpot.reservations).filter(Reservation.user_id == user.id).group_by(ParkingLot.id).order_by(func.count(Reservation.id).desc()).first()

    favourite_lot_name = favourite_lot[0] if favourite_lot else None

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
    spending_labels = [d.strftime('%d-%b') for d in dates]
    bookings_labels = spending_labels.copy()

    spending_data = []
    bookings_data = []

    for d in dates:
        next_day = d + timedelta(days=1)

        day_spending = db.session.query(func.coalesce(func.sum(Reservation.parking_cost), 0)).filter(
            Reservation.user_id == user.id,
            Reservation.parking_timestamp >= d,
            Reservation.parking_timestamp < next_day,
        ).scalar()

        day_bookings = db.session.query(func.count(Reservation.id)).filter(
            Reservation.user_id == user.id,
            Reservation.parking_timestamp >= d,
            Reservation.parking_timestamp < next_day,
        ).scalar()

        spending_data.append(float(day_spending))
        bookings_data.append(day_bookings)

    recent_bookings = Reservation.query.filter_by(user_id=user.id).order_by(Reservation.parking_timestamp.desc()).limit(3).all()

    return render_template(
                           'user/summary.html',
                           user_logged_in=user_logged_in,
                           user_name=user.full_name,
                           total_bookings=total_bookings,
                           active_bookings=active_bookings,
                           total_vehicles=total_vehicles,
                           total_spent=f"{total_spent:.2f}",
                           favourite_lot=favourite_lot_name,
                           spending_labels=spending_labels,
                           spending_data=spending_data,
                           bookings_labels=bookings_labels,
                           bookings_data=bookings_data,
                           recent_bookings=recent_bookings
                        )