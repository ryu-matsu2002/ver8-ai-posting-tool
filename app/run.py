from app import create_app
from app.extensions import db
from flask_migrate import Migrate
from app.scheduler import scheduler
from flask_migrate import upgrade

app = create_app()
migrate = Migrate(app, db)

with app.app_context():
    upgrade()

scheduler.init_app(app)
scheduler.start()
