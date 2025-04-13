from flask import Flask
from .extensions import db, login_manager
from .models import User
from .routes import routes_bp
from .auth import auth_bp
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
