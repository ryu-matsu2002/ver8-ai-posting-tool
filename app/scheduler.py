# 📁 app/scheduler.py

from flask_apscheduler import APScheduler
from datetime import datetime
import pytz
from app.models import db, ScheduledPost, GenerationControl
from app.wordpress_post import post_to_wordpress
from app.article_generator import generate_article_for_post

scheduler = APScheduler()

def init_app(app):
    scheduler.init_app(app)
    scheduler.start()

    @scheduler.task('interval', id='scheduled_task', seconds=60)
    def scheduled_task():
        with app.app_context():
            try:
                jst = pytz.timezone("Asia/Tokyo")
                now = datetime.now(jst)

                # ✅ ① 記事生成処理：生成待ちかつスケジュール時刻が過ぎている
                generate_targets = ScheduledPost.query.filter(
                    ScheduledPost.status == "生成待ち",
                    ScheduledPost.scheduled_time <= now
                ).order_by(ScheduledPost.scheduled_time).limit(3).all()

                for post in generate_targets:
                    # ユーザーが停止していないか確認
                    control = GenerationControl.query.filter_by(user_id=post.user_id).first()
                    if control and control.stop_flag:
                        print(f"⏸ 生成停止中: {post.keyword}")
                        continue

                    print(f"✏️ 生成中: {post.keyword}")
                    success = generate_article_for_post(post.id)
                    if success:
                        print(f"✅ 生成完了: {post.keyword}")
                    else:
                        print(f"❌ 生成失敗: {post.keyword}")

                # ✅ ② 投稿処理：生成完了でスケジュール時刻を過ぎている
                post_targets = ScheduledPost.query.filter(
                    ScheduledPost.status == '生成完了',
                    ScheduledPost.scheduled_time <= now
                ).all()

                for post in post_targets:
                    print(f"📤 投稿チェック中: {post.title}（予定時刻: {post.scheduled_time}）")

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
