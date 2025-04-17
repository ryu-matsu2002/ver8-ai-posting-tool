# 📁 app/auto_post.py

import random
from datetime import datetime, timedelta, time as dtime
import pytz
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from flask_login import login_required, current_user

from .models import db, ScheduledPost, Site, PromptTemplate, GenerationControl
from .forms import AutoPostForm

auto_post_bp = Blueprint("auto_post", __name__)

@auto_post_bp.route("/auto-post", methods=["GET", "POST"])
@login_required
def auto_post():
    form = AutoPostForm()
    sites = Site.query.filter_by(user_id=current_user.id).all()
    form.site_id.choices = [(site.id, site.site_url) for site in sites]

    if form.validate_on_submit():
        # 🔹 入力データの取得
        site_id = form.site_id.data
        title_prompt = form.title_prompt.data.strip()
        body_prompt = form.body_prompt.data.strip()
        keywords = [kw.strip() for kw in form.keywords.data.strip().splitlines() if kw.strip()]

        # 🔸 スケジュール生成（30日分、1日1〜5件、JST 10〜21時）
        jst = pytz.timezone("Asia/Tokyo")
        now = datetime.now(jst)
        base_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        schedule_times = []
        for day in range(30):
            date_only = (base_start + timedelta(days=day)).date()
            num_posts = random.choices([1, 2, 3, 4, 5], weights=[1, 2, 4, 6, 2])[0]
            times = []
            while len(times) < num_posts:
                h = random.randint(10, 21)
                m = random.randint(0, 59)
                candidate = jst.localize(datetime.combine(date_only, dtime(hour=h, minute=m)))
                if all(abs((candidate - t).total_seconds()) >= 7200 for t in times):  # 2時間間隔
                    times.append(candidate)
            schedule_times.extend(sorted(times))  # ✅ JSTのまま保存

        # 🔸 対象サイト
        site = Site.query.filter_by(id=site_id, user_id=current_user.id).first()
        if not site:
            flash("サイト情報が見つかりません", "error")
            return redirect(url_for("routes.auto_post"))

        # 🔸 生成停止フラグOFF
        control = GenerationControl.query.filter_by(user_id=current_user.id).first()
        if not control:
            control = GenerationControl(user_id=current_user.id, stop_flag=False)
            db.session.add(control)
        else:
            control.stop_flag = False
        db.session.commit()

        # 🔸 DB登録処理（記事生成は非同期処理で対応）
        scheduled_index = 0
        for kw in keywords:
            article_count = random.choice([2, 3])
            for _ in range(article_count):
                scheduled_time = schedule_times[scheduled_index] if scheduled_index < len(schedule_times) else now + timedelta(days=1)
                scheduled_index += 1

                post = ScheduledPost(
                    keyword=kw,
                    title="生成中...",
                    body="",
                    featured_image=None,
                    status="生成待ち",  # ✅ 正しく「生成待ち」に設定
                    scheduled_time=scheduled_time,
                    created_at=datetime.utcnow(),
                    site_url=site.site_url,
                    username=site.wp_username,
                    app_password=site.wp_app_password,
                    user_id=current_user.id,
                    site_id=site.id,
                    genre="",  # 使用しないため空文字
                    prompt_title=title_prompt,
                    prompt_body=body_prompt
                )
                db.session.add(post)

        db.session.commit()
        flash("✅ キーワードをもとに記事スケジュールを保存しました。生成処理が開始されます。", "success")
        return redirect(url_for("routes.admin_log", site_id=site.id))

    return render_template("auto_post.html", form=form, sites=sites)
