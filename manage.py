# manage.py
from flask.cli import FlaskGroup
from app import create_app
from app.extensions import db
from flask_migrate import Migrate, upgrade

app = create_app()
cli = FlaskGroup(app)  # Flask CLI コマンドを使えるようにする

# Flask-Migrate を初期化（Flask CLI の db コマンドとして認識させる）
migrate = Migrate(app, db)

if __name__ == "__main__":
    cli()
