# 📄 app/auto_post.py

import os
import random
from datetime import datetime, timedelta
import pytz

from flask import Blueprint, current_app, render_template, redirect, url_for
from flask_login import current_user, login_required
from dotenv import load_dotenv

from .models import db, Site, ScheduledPost, PromptTemplate, GenerationControl
from .forms import AutoPostForm

auto_post_bp = Blueprint("auto_post", __name__)
load_dotenv()

@auto_post_bp.route('/auto-post', methods=['GET', 'POST'])
@login_required
def auto_post():
    form = AutoPostForm()
    sites = Site.query.filter_by(user_id=current_user.id).all()
    templates = PromptTemplate.query.filter_by(user_id=current_user.id).all()
    form.site_id.choices = [(site.id, site.site_url) for site in sites]
    form.template_id.choices = [(tpl.id, tpl.genre) for tpl in templates]

    if form.validate_on_submit():
        keywords = form.keywords.data.strip().splitlines()
        site_id = form.site_id.data
        template_id = form.template_id.data

        site = Site.query.filter_by(id=site_id, user_id=current_user.id).first()
        template = PromptTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
        if not site or not template:
            print("❌ サイトまたはテンプレートが見つかりません。")
            return redirect(url_for('auto_post.auto_post'))

        title_prompt = template.title_prompt
        body_prompt = template.body_prompt

        # 停止フラグを初期化
        control = GenerationControl.query.filter_by(user_id=current_user.id).first()
        if not control:
            control = GenerationControl(user_id=current_user.id, stop_flag=False)
            db.session.add(control)
        else:
            control.stop_flag = False
        db.session.commit()

        # 投稿スケジュール生成（30日間でランダム分配）
        jst = pytz.timezone("Asia/Tokyo")
        now = datetime.now(jst)
        base_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        schedule_times = []
        for day in range(30):
            base = base_start + timedelta(days=day)
            num_posts = random.choices([1, 2, 3, 4, 5], weights=[1, 2, 4, 6, 2])[0]
            times = []
            while len(times) < num_posts:
                h = random.randint(10, 21)
                m = random.randint(0, 59)
                candidate = base.replace(hour=h, minute=m)
                if all(abs((candidate - t).total_seconds()) >= 7200 for t in times):
                    times.append(candidate)
            schedule_times.extend(sorted([t.astimezone(pytz.utc) for t in times]))

        scheduled_index = 0
        for keyword in keywords:
            article_count = random.choice([2, 3])
            for _ in range(article_count):
                schedule_time = schedule_times[scheduled_index] if scheduled_index < len(schedule_times) else now + timedelta(days=1)
                scheduled_index += 1

                post = ScheduledPost(
                    title="",
                    body="",
                    keyword=keyword.strip(),
                    featured_image=None,
                    status="生成待ち",  # ← Workerが処理対象と認識する
                    scheduled_time=schedule_time,
                    created_at=datetime.utcnow(),
                    site_url=site.site_url,
                    username=site.wp_username,
                    app_password=site.wp_app_password,
                    user_id=current_user.id,
                    site_id=site.id,
                    prompt_title=title_prompt,
                    prompt_body=body_prompt
                )
                db.session.add(post)

        db.session.commit()
        return redirect(url_for('routes.admin_log', site_id=site.id))

    return render_template('auto_post.html', form=form, sites=sites, prompt_templates=templates)
