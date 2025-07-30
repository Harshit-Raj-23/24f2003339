from flask import Blueprint, request, render_template, redirect, flash, url_for, session
from models import db, User, Address, Vehicle, ParkingLot, ParkingSpot, Reservation
from decorators import admin_required
from datetime import datetime, timedelta
from sqlalchemy import func, or_


admin_bp = Blueprint('admin', __name__)


# --------------------------
# Admin Page
# --------------------------
@admin_bp.route('/', methods=['GET'])
@admin_required
def index():
    user_logged_in = 'user_id' in session
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
                                Address.pincode.ilike(search),
                            )
                        ).all()
        )
    else:
        parking_lots = ParkingLot.query.all()
    return render_template(
                            'admin/index.html', 
                            user_logged_in=user_logged_in, 
                            parking_lots=parking_lots,
                            query=query
                          )


# --------------------------
# Add Parking
# --------------------------
@admin_bp.route('/addLot', methods=['GET'])
@admin_required
def add_parking_lot():
    user_logged_in = 'user_id' in session
    parking_lots = ParkingLot.query.all()
    return render_template(
                            'admin/add_parking_lot.html', 
                            user_logged_in=user_logged_in, 
                            parking_lots=parking_lots
                          )

@admin_bp.route('/addLot', methods=['POST'])
@admin_required
def add_parking_lot_post():
    locName = request.form.get('locName')
    address = request.form.get('address')
    city = request.form.get('city')
    pincode = request.form.get('pincode')
    state = request.form.get('state')
    price = request.form.get('price')
    maxSpots = request.form.get('maxSpots')

    if not locName or not address or not city or not pincode or not state or not price or not maxSpots:
        flash('Please enter all fields.', 'danger')
        return redirect(url_for('admin.add_parking_lot'))
    
    try:
        maxSpots = int(maxSpots)
        price = float(price)
    except ValueError:
        flash('Price must be a number and max spots must be an integer.', 'danger')
        return redirect(url_for('admin.add_parking_lot'))
    
    new_address = Address(
                      address=address,
                      city=city,
                      pincode=pincode,
                      state=state
    )

    db.session.add(new_address)
    db.session.commit()
    
    new_parking_lot = ParkingLot(
                             prime_location_name = locName,
                             address_id = new_address.id,
                             price_per_hour = price,
                             max_spots = maxSpots
                            )
    
    db.session.add(new_parking_lot)
    db.session.commit()

    for i in range(1, int(maxSpots) + 1):
        spot_number = f"LOT{new_parking_lot.id}-S{i:03d}"
        new_spot = ParkingSpot(
            spot_number=spot_number,
            lot_id=new_parking_lot.id,
            status='A'
        )
        db.session.add(new_spot)

    db.session.commit()

    flash('Parking lot created successfully.', 'success')
    return redirect(url_for('admin.index'))


# --------------------------
# Edit Parking
# --------------------------
@admin_bp.route('/editLot/<int:lot_id>', methods=['GET'])
@admin_required
def edit_parking_lot(lot_id):
    user_logged_in = 'user_id' in session
    parking_lot = ParkingLot.query.get(lot_id)
    return render_template('admin/edit_parking_lot.html', user_logged_in=user_logged_in, parking_lot=parking_lot)

@admin_bp.route('/editLot/<int:lot_id>', methods=['POST'])
@admin_required
def editParkingLot_post(lot_id):
    new_locName = request.form.get('locName')
    new_address = request.form.get('address')
    new_city = request.form.get('city')
    new_pincode = request.form.get('pincode')
    new_state = request.form.get('state')
    new_price = request.form.get('price')
    new_maxSpots = request.form.get('maxSpots')

    if not new_locName or not new_address or not new_city or not new_pincode or not new_state or not new_price or not new_maxSpots:
        flash('Please enter all fields.', 'danger')
        return redirect(url_for('admin.edit_parking_lot', lot_id=lot_id))
    
    try:
        maxSpots = int(new_maxSpots)
        price = float(new_price)
    except ValueError:
        flash('Price must be a number and max spots must be an integer.', 'danger')
        return redirect(url_for('admin.edit_parking_lot', lot_id=lot_id))

    existing_pl = ParkingLot.query.get(lot_id)
    old_maxSpots = existing_pl.max_spots

    if not existing_pl:
        flash('Parking Lot does not exist.', 'danger')
        return redirect(url_for('admin.edit_parking_lot', lot_id=lot_id))
    
    occupied = ParkingSpot.query.filter_by(lot_id=lot_id, status='O').count()

    if maxSpots < occupied:
        flash('Max Spot value entered is less than already occupied. Please enter larger no.', 'danger')
        return redirect(url_for('admin.edit_parking_lot', lot_id=lot_id))
    
    existing_pl.prime_location_name =new_locName
    existing_pl.price_per_hour = new_price
    existing_pl.max_spots = new_maxSpots
    existing_pl.updated_at = datetime.utcnow()
    existing_pl.address.address = new_address
    existing_pl.address.city = new_city
    existing_pl.address.pincode = new_pincode
    existing_pl.address.state = new_state

    if maxSpots > old_maxSpots:
        for i in range(old_maxSpots + 1, maxSpots + 1):
            spot_number = f"LOT{lot_id}-S{i:03d}"
            new_spot = ParkingSpot(
                spot_number=spot_number,
                lot_id=lot_id,
                status='A'
            )
            db.session.add(new_spot)
    
    if maxSpots < old_maxSpots:
        for i in range(old_maxSpots, maxSpots, -1):
            spot_number = f"LOT{lot_id}-S{i:03d}"
            spot_to_delete = ParkingSpot.query.filter_by(lot_id=lot_id, spot_number=spot_number, status='A').first()
            if spot_to_delete:
                db.session.delete(spot_to_delete)
            else:
                flash(f"Could not delete spot {spot_number} because it's occupied.", 'danger')


    db.session.commit()

    flash('Parking Lot updated successfully.', 'success')
    return redirect(url_for('admin.index'))


# --------------------------
# Delete Parking
# --------------------------
@admin_bp.route('/deleteLot/<int:lot_id>', methods=['POST'])
@admin_required
def deleteParkingLot(lot_id):
    parking_lot = ParkingLot.query.get(lot_id)

    occupied_count = ParkingSpot.query.filter_by(lot_id=lot_id, status='O').count()

    if occupied_count > 0:
        flash('Cannot delete Parking Lot. Vehicles are currently parked.', 'danger')
        return redirect(url_for('admin.index'))
    
    ParkingSpot.query.filter_by(lot_id=lot_id).delete()

    db.session.delete(parking_lot)
    db.session.commit()

    flash("Parking lot deleted successfully.", 'success')
    return redirect(url_for('admin.index'))


# --------------------------
# View Parking
# --------------------------
@admin_bp.route('/view_lot/<int:lot_id>', methods=['GET'])
@admin_required
def view_lot(lot_id):
    user_logged_in = 'user_id' in session
    lot = ParkingLot.query.get(lot_id)
    current_time = datetime.utcnow()

    return render_template('admin/view_lot.html', user_logged_in=user_logged_in, lot=lot, current_time=current_time)


# --------------------------
# All Users Page
# --------------------------
@admin_bp.route('/users', methods=['GET'])
@admin_required
def all_users():
    user_logged_in = 'user_id' in session
    query = request.args.get('query', '').strip()

    if query:
        search = f'%{query}%'
        users = (
                 User.query
                 .filter(
                     or_(
                         User.full_name.ilike(search),
                         User.email.ilike(search),
                     )
                 )
                 .order_by(User.registered_at.desc())
                 .all()
        )
    else:
        users = User.query.order_by(User.registered_at.desc()).all()

    return render_template('admin/all_users.html', user_logged_in=user_logged_in, users=users)


# --------------------------
# Delete User
# --------------------------
@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user_logged_in = 'user_id' in session

    user = User.query.get(user_id)

    if not user:
        flash('Invalid User ID! Cannot delete user.', 'danger')
        return redirect(url_for('admin.all_users'))

    if user.reservations:
        flash('User having active parking! Cannot delete user.', 'danger')
        return redirect(url_for('admin.all_users'))
    
    db.session.delete(user)
    db.session.commit()

    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin.all_users'))


# --------------------------
# All Reservations Page
# --------------------------
@admin_bp.route('/reservations', methods=['GET'])
@admin_required
def all_reservations():
    user_logged_in = 'user_id' in session
    current_time = datetime.utcnow()
    query = request.args.get('query', '')

    if query:
        search = f'%{query}%'
        reservations = (
                        Reservation.query
                        .join(User, Reservation.user)
                        .join(ParkingSpot, Reservation.spot)
                        .join(ParkingLot, ParkingSpot.lot)
                        .join(Vehicle, Reservation.vehicle)
                        .filter(
                            or_(
                                User.full_name.ilike(search),
                                ParkingLot.prime_location_name.ilike(search),
                                Vehicle.vehicle_number.ilike(search),
                                Vehicle.vehicle_type.ilike(search)
                            )
                        )
                        .order_by(Reservation.parking_timestamp.desc())
                        .all()
        )
    else:
        reservations = Reservation.query.order_by(Reservation.parking_timestamp.desc()).all()

    return render_template('admin/all_reservations.html', user_logged_in=user_logged_in, reservations=reservations, current_time=current_time, query=query)


# --------------------------
# Summary Page
# --------------------------
@admin_bp.route('/summary', methods=['GET'])
@admin_required
def summary():
    user_logged_in = 'user_id' in session

    total_users = User.query.count()
    total_lots = ParkingLot.query.count()
    total_spots = ParkingSpot.query.count()
    total_reservations = Reservation.query.count()

    all_costs = [r.parking_cost for r in Reservation.query.filter(Reservation.parking_cost != None).all()]
    total_revenue = sum(all_costs)

    booked_spots = ParkingSpot.query.filter_by(status='O').count()
    vacant_spots = ParkingSpot.query.filter_by(status='A').count()

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    dates = [(today - timedelta(days=x)) for x in range(6, -1, -1)]
    date_strs = [d.strftime('%d-%b') for d in dates]

    res_counts = []
    rev_amounts = []

    for day in dates:
        next_day = day + timedelta(days=1)

        count = Reservation.query.filter(
            Reservation.parking_timestamp >= day,
            Reservation.parking_timestamp < next_day
        ).count()

        total = (
            Reservation.query
            .with_entities(func.sum(Reservation.parking_cost))
            .filter(
                Reservation.parking_timestamp >= day,
                Reservation.parking_timestamp < next_day
            )
            .scalar()
        ) or 0

        res_counts.append(count)
        rev_amounts.append(float(total))

    recent_reservations = (
        Reservation.query
        .order_by(Reservation.parking_timestamp.desc())
        .limit(5)
        .all()
    )

    recent_users = (
        User.query
        .order_by(User.registered_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        'admin/summary.html',
        user_logged_in=user_logged_in,
        total_users=total_users,
        total_lots=total_lots,
        total_spots=total_spots,
        total_reservations=total_reservations,
        total_revenue=f"{total_revenue:.2f}",
        booked_spots=booked_spots,
        vacant_spots=vacant_spots,
        recent_reservations=recent_reservations,
        recent_users=recent_users,
        reservations_chart_labels=date_strs,
        reservations_chart_data=res_counts,
        revenue_chart_labels=date_strs,
        revenue_chart_data=rev_amounts
    )