from flask import Blueprint, request, render_template, redirect, flash, url_for, session
from models import db, User
from werkzeug.security import check_password_hash, generate_password_hash
from decorators import auth_required


auth_bp = Blueprint('auth', __name__)


# --------------------------
# Authorization - Register
# --------------------------
@auth_bp.route('/register', methods=['GET'])
def register():
    email = request.args.get('email', '').strip()
    full_name = request.args.get('full_name', '').strip()
    return render_template('auth/register.html', email=email, full_name=full_name)

@auth_bp.route('/register', methods=['POST'])
def register_post():
    email = request.form.get('email').strip()
    full_name = request.form.get('full_name').strip()
    password = request.form.get('password').strip()
    cpassword = request.form.get('cpassword').strip()

    if not email or not password or not cpassword:
        flash('Please fill the required fields.','danger')
        return redirect(url_for('auth.register'))
    
    user = User.query.filter_by(email=email).first()

    if user:
        flash('Email already taken! Please use another Email ID.', 'danger')
        return redirect(url_for('auth.register'))
    
    if password != cpassword:
        flash('Password mismatched!', 'danger')
        return redirect(url_for('auth.register', email=email, full_name=full_name))
    
    password_hash = generate_password_hash(password)

    user = User(email=email, password=password_hash, full_name=full_name)
    db.session.add(user)
    db.session.commit()
    
    session['user_id'] = user.id
    session['is_admin'] = user.is_admin

    flash('User registered successfully!', 'success')
    return redirect(url_for('user.index'))


# --------------------------
# Authorization - Login
# --------------------------
@auth_bp.route('/login', methods=['GET'])
def login():
    email = request.args.get('email', '').strip()
    return render_template('auth/login.html', email=email)

@auth_bp.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email').strip()
    password = request.form.get('password').strip()

    if not email or not password:
        flash('Please fill the required fields.', 'danger')
        return redirect(url_for('auth.login'))
    
    user = User.query.filter_by(email=email).first()

    if not user:
        flash('Email not registered! Please use valid Email ID.', 'danger')
        return redirect(url_for('auth.login'))
    
    if not check_password_hash(user.password, password):
        flash('Incorrect Password! Please enter the correct password.', 'danger')
        return redirect(url_for('auth.login', email=email))
    
    session['user_id'] = user.id
    session['is_admin'] = user.is_admin

    if user.is_admin:
        flash('Admin logged in successfully!', 'success')
        return redirect(url_for('admin.index'))

    flash('User logged in successfully!', 'success')
    return redirect(url_for('user.index'))


# --------------------------
# Authorization - Logout
# --------------------------
@auth_bp.route('/logout', methods=['GET'])
@auth_required
def logout():
    session.pop('user_id', None)
    session.pop('is-admin', None)
    flash('You have been logged out.', 'danger')
    return redirect(url_for('user.index'))