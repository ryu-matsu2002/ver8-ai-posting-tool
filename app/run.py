# 📄 run.py

from app import create_app
from app.extensions import db
from flask_migrate import Migrate, upgrade
from app.scheduler import scheduler

# Flaskアプリの生成
app = create_app()

# DBマイグレーション初期化
migrate = Migrate(app, db)

# アプリケーションコンテキスト内でマイグレーション適用
with app.app_context():
    upgrade()

# APScheduler を初期化・起動（⏰ 60秒ごとの自動投稿確認）
scheduler.init_app(app)
scheduler.start()

# アプリ起動（Renderではgunicorn経由なので不要かも）
if __name__ == "__main__":
    app.run()
