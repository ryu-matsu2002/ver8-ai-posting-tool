# 📄 run.py

from app import create_app
from app.extensions import db
from flask_migrate import Migrate, upgrade
from app.scheduler import scheduler

# Flaskアプリケーション生成
app = create_app()

# DBマイグレーション初期化
migrate = Migrate(app, db)

# マイグレーション適用（Render起動時に自動で適用）
with app.app_context():
    upgrade()  # 🔁 alembic upgrade head 相当

# APScheduler の初期化と開始（自動投稿スケジューラ）
scheduler.init_app(app)
scheduler.start()

# ローカル開発用のサーバー起動（Renderでは gunicorn 経由）
if __name__ == "__main__":
    app.run(debug=True)
