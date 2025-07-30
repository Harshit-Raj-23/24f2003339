from flask import redirect, session, flash, url_for
from functools import wraps
from models import User


def auth_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash('Please login to continue.')
            return redirect(url_for('auth.login'))
    return inner


def admin_required(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.')
            return redirect(url_for('auth.login'))
        if not session.get('is_admin'):
            flash('You are not authorized to visit this page.')
            return redirect(url_for('admin.index'))
        return func(*args, **kwargs)
    return inner