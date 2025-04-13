# app/__init__.py

from flask import Flask
from .extensions import db, login_manager
from .models import User
from .routes import routes_bp
from .auth import auth_bp  # 🔹 追加：auth Blueprint のインポート

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # DBとログインマネージャーの初期化
    db.init_app(app)
    login_manager.init_app(app)

    # login_view（未ログイン時のリダイレクト先）を設定
    login_manager.login_view = 'auth.login'

    # Blueprint登録
    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')  # 🔹 追加：authルートを /auth/ で登録

    # Userロード関数
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
