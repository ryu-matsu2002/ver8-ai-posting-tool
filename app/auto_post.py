# 📄 app/auto_post.py

import os
import threading
import time
import random
from datetime import datetime, timedelta
import pytz
import traceback
import re

from flask import Blueprint, current_app, render_template, redirect, url_for
from flask_login import current_user, login_required
from dotenv import load_dotenv
from openai import OpenAI
from deep_translator import GoogleTranslator

from .models import db, Site, ScheduledPost, PromptTemplate, GenerationControl
from .image_search import search_images
from .forms import AutoPostForm

load_dotenv()
auto_post_bp = Blueprint("auto_post", __name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ユーザー入力がメイン、ベースは補助的なガイド
title_base_prompt = """以下のキーワードに対して質問形式のSEOタイトルを1つ考えてください：
キーワード：「{{keyword}}」"""

body_base_prompt = """🔧執筆ガイド（参考ルール）
- 問題提起 → 共感 → 解決策
- 読者は「あなた」呼び（皆さん禁止）
- 敬語、親友に語るように
- 段落内改行なし、段落間に2行空ける
- 見出し（hタグ）で構成整理"""

def enhance_h2_tags(content):
    return re.sub(r'(<h2.*?>)', r'\1<span style="font-size: 1.5em; font-weight: bold;">', content).replace("</h2>", "</span></h2>")

def clean_title(title):
    return re.sub(r'^[0-9\.\-ー①-⑩]+[\.\s）)]*|[「」\"]', '', title).strip()

def is_generation_stopped(user_id):
    control = GenerationControl.query.filter_by(user_id=user_id).first()
    return control and control.stop_flag

def generate_and_save_articles(app, keywords, title_prompt, body_prompt, site_id, user_id):
    with app.app_context():
        site = Site.query.filter_by(id=site_id, user_id=user_id).first()
        if not site:
            print("[エラー] サイト情報が見つかりません。")
            return
        username = site.wp_username
        app_password = site.wp_app_password
        site_url = site.site_url

        jst = pytz.timezone("Asia/Tokyo")
        now = datetime.now(jst)
        base_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        # ⏰ 30日分の投稿スケジュール（10時～21時、30分以上間隔）
        schedule_times = []
        used_times = set()
        for day in range(30):
            base = base_start + timedelta(days=day)
            num_posts = random.choices([1, 2, 3, 4, 5], weights=[1, 2, 4, 6, 2])[0]
            day_schedule = []
            attempts = 0
            while len(day_schedule) < num_posts and attempts < 100:
                h = random.randint(10, 21)
                m = random.randint(0, 59)
                candidate = base.replace(hour=h, minute=m)
                if all(abs((candidate - t).total_seconds()) >= 1800 for t in day_schedule):
                    day_schedule.append(candidate)
                attempts += 1
            schedule_times.extend([dt.astimezone(pytz.utc) for dt in sorted(day_schedule)])

        scheduled_index = 0
        for keyword in keywords:
            article_count = random.choice([2, 3])
            for n in range(article_count):
                if is_generation_stopped(user_id):
                    print("🛑 停止フラグ検出 → 中断")
                    return
                try:
                    print(f"\n▶ キーワード: {keyword}（{n+1}/{article_count}）")

                    title_input = title_base_prompt.replace("{{keyword}}", keyword.strip())
                    if title_prompt:
                        title_input += f"\n\n{title_prompt.strip()}"

                    title_res = client.chat.completions.create(
                        model="gpt-4-turbo",
                        messages=[
                            {"role": "system", "content": "あなたはSEOの専門家です。"},
                            {"role": "user", "content": title_input}
                        ],
                        temperature=0.7,
                        max_tokens=100
                    )
                    raw_title = title_res.choices[0].message.content.strip().split("\n")[0]
                    title = clean_title(raw_title)
                    print("✅ タイトル生成:", title)

                    body_input = ""
                    if body_prompt:
                        body_input += body_prompt.strip() + "\n\n"
                    body_input += body_base_prompt + f"\n\nタイトル：「{title}」に基づいて本文を生成してください。"

                    body_res = client.chat.completions.create(
                        model="gpt-4-turbo",
                        messages=[
                            {"role": "system", "content": "あなたはSEOライターです。"},
                            {"role": "user", "content": body_input}
                        ],
                        temperature=0.7,
                        max_tokens=4096
                    )
                    content = body_res.choices[0].message.content.strip()
                    content = enhance_h2_tags(content)

                    en_keyword = GoogleTranslator(source='ja', target='en').translate(keyword)
                    image_urls = search_images(en_keyword, num_images=1)
                    featured_image = image_urls[0] if image_urls else None

                    scheduled_time = schedule_times[scheduled_index] if scheduled_index < len(schedule_times) else now + timedelta(days=1)
                    scheduled_index += 1

                    post = ScheduledPost(
                        title=title,
                        body=content,
                        keyword=keyword,
                        featured_image=featured_image,
                        status="生成完了",
                        scheduled_time=scheduled_time,
                        created_at=datetime.utcnow(),
                        site_url=site_url,
                        username=username,
                        app_password=app_password,
                        user_id=user_id,
                        site_id=site_id
                    )
                    db.session.add(post)
                    db.session.commit()
                    print(f"✅ 保存完了: {title}")
                    time.sleep(5)

                except Exception as e:
                    print(f"❌ 例外発生（{keyword}）: {e}")
                    traceback.print_exc()
                    db.session.rollback()

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
        selected_template = PromptTemplate.query.filter_by(id=template_id, user_id=current_user.id).first()
        if not selected_template:
            print("❌ テンプレートが見つかりません。")
            return redirect(url_for('auto_post.auto_post'))

        title_prompt = selected_template.title_prompt
        body_prompt = selected_template.body_prompt

        control = GenerationControl.query.filter_by(user_id=current_user.id).first()
        if not control:
            control = GenerationControl(user_id=current_user.id, stop_flag=False)
            db.session.add(control)
        else:
            control.stop_flag = False
        db.session.commit()

        app_instance = current_app._get_current_object()
        thread = threading.Thread(
            target=generate_and_save_articles,
            args=(app_instance, keywords, title_prompt, body_prompt, site_id, current_user.id)
        )
        thread.start()
        return redirect(url_for('routes.admin_log', site_id=site_id))

    return render_template('auto_post.html', form=form, sites=sites, prompt_templates=templates)
