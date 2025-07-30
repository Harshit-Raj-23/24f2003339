from .auth_routes import auth_bp
from .admin_routes import admin_bp
from .user_routes import user_bp



def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp)