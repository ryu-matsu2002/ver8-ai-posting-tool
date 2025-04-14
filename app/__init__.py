# 📄 app/__init__.py

from flask import Flask
from flask_wtf import CSRFProtect
from .extensions import db, login_manager
from .models import User
from .routes import routes_bp
from .auth import auth_bp
from .auto_post import auto_post_bp
from .scheduler import init_app
from config import Config

csrf = CSRFProtect()  # ✅ CSRF保護インスタンス生成

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)  # ✅ CSRF保護を初期化

    login_manager.login_view = 'auth.login'

    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(auto_post_bp)  # ✅ 忘れずに登録

    init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
