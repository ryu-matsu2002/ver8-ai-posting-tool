from flask import Flask
from dotenv import load_dotenv
from .extensions import db, login_manager
from .models import User
from .routes import routes_bp
from .auth import auth_bp
from config import Config
import os

def create_app():
    # 環境変数の読み込み（.envファイル対応）
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    # DBとLoginの初期化（必須）
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Flask-Loginのuser_loader
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))  # ← 最新の書き方推奨

    # Blueprintの登録
    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app
