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
                now_utc = datetime.utcnow()

                # ✅ ① 記事生成対象を「生成中」に変更（ワーカーに拾わせる）
                generate_targets = ScheduledPost.query.filter(
                    ScheduledPost.status == "生成待ち",
                    ScheduledPost.scheduled_time <= now_utc
                ).order_by(ScheduledPost.scheduled_time).limit(3).all()

                for post in generate_targets:
                    try:
                        control = GenerationControl.query.filter_by(user_id=post.user_id).first()
                        if control and control.stop_flag:
                            print(f"⏸ 停止フラグ中: {post.keyword}")
                            continue

                        print(f"🔁 ステータス変更 → 生成中: {post.keyword}")
                        post.status = "生成中"
                        db.session.commit()

                    except Exception as e:
                        print(f"❌ ステータス更新エラー: {post.id} → {e}")
                        db.session.rollback()

                # ✅ ② 投稿処理
                post_targets = ScheduledPost.query.filter(
                    ScheduledPost.status == "生成完了",
                    ScheduledPost.scheduled_time <= now_utc
                ).all()

                for post in post_targets:
                    try:
                        print(f"📤 投稿処理中: {post.title}（予定: {post.scheduled_time}）")

                        success = post_to_wordpress(
                            site_url=post.site_url,
                            wp_username=post.username,
                            wp_app_password=post.app_password,
                            title=post.title,
                            content=post.body,
                            images=[post.featured_image] if post.featured_image else []
                        )

                        if success:
                            post.status = "投稿済み"
                            db.session.commit()
                            print(f"✅ 投稿成功: {post.title}")
                        else:
                            print(f"❌ 投稿失敗: {post.title}")

                    except Exception as e:
                        print(f"❌ 投稿処理エラー: {post.id} → {e}")
                        db.session.rollback()

            except Exception as e:
                print(f"🔥 スケジューラー全体エラー: {e}")
