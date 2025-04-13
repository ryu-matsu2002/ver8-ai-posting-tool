from app import create_app
from app.extensions import db
from flask_migrate import Migrate
from app.scheduler import scheduler

app = create_app()
migrate = Migrate(app, db)

scheduler.init_app(app)
scheduler.start()
