# app/__init__.py
from flask import Flask
from dotenv import load_dotenv
from .extensions import db, login_manager
from .models import User
from .routes import routes_bp
from .auth import auth_bp
from config import Config
import os

def create_app():
    # 環境変数読み込み（.env用）
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    # DB 初期化
    db.init_app(app)

    # Flask-Login 初期化
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # user_loader 設定
    @login_manager.user_loader
    def load_user(user_id):
        with app.app_context():
            return User.query.get(int(user_id))

    # Blueprint 登録
    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app
