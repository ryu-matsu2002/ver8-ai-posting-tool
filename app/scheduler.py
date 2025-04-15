# app/scheduler.py

from flask_apscheduler import APScheduler
from datetime import datetime
import pytz
from app.models import db, ScheduledPost
from app.wordpress_post import post_to_wordpress

scheduler = APScheduler()

def init_app(app):
    scheduler.init_app(app)
    scheduler.start()

    # app context 付きで scheduler 関数を呼べるようにしておく
    @scheduler.task('interval', id='auto_post_task', seconds=60)
    def auto_post_task():
        with app.app_context():
            try:
                now_utc = datetime.utcnow()

                posts = ScheduledPost.query.filter(
                    ScheduledPost.status == '生成完了',
                    ScheduledPost.scheduled_time <= now_utc
                ).all()

                for post in posts:
                    print(f"🔄 投稿チェック中: {post.title}（予定時刻: {post.scheduled_time}）")

                    success = post_to_wordpress(
                        site_url=post.site_url,
                        wp_username=post.username,
                        wp_app_password=post.app_password,
                        title=post.title,
                        content=post.body,
                        images=[post.featured_image] if post.featured_image else []
                    )

                    if success:
                        post.status = '投稿済み'
                        db.session.commit()
                        print(f"✅ 投稿成功: {post.title}")
                    else:
                        print(f"❌ 投稿失敗: {post.title}")

            except Exception as e:
                print(f"🔥 スケジューラーエラー: {e}")
