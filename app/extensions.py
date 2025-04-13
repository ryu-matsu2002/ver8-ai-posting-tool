# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# これらは1回しか定義してはいけない
db = SQLAlchemy()
login_manager = LoginManager()
