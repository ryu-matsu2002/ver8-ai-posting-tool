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
from flask_migrate import Migrate
import openai
import os

csrf = CSRFProtect()  # ✅ CSRF保護インスタンス生成

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ✅ 環境変数からOpenAI APIキーを設定
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # ✅ 拡張機能の初期化
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    Migrate(app, db)

    login_manager.login_view = 'auth.login'

    # ✅ ルーティング登録
    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(auto_post_bp)

    # ✅ スケジューラー初期化（定期処理）
    init_app(app)

    # ✅ ログインユーザー読込関数
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
