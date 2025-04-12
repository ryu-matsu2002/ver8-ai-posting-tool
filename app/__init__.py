from flask import Flask
from .models import db
from .routes import routes_bp
from flask_migrate import Migrate
from flask import Flask, render_template


migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_secret_key'

    db.init_app(app)
    migrate.init_app(app, db)
    # Blueprint登録
    app.register_blueprint(routes_bp)

    # エラーハンドラー
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500


    return app
__all__ = ['create_app', 'db']
