import os
import openai
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.models import User
from app.routes import routes_bp
from app.auto_post import auto_post_bp

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # 拡張初期化
    db.init_app(app)
    login_manager.init_app(app)
    Migrate(app, db)

    # Blueprints
    app.register_blueprint(routes_bp)
    app.register_blueprint(auto_post_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
