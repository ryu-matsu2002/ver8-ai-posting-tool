import os
import threading
import time
import random
from datetime import datetime, timedelta
import pytz
import traceback
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Blueprint, current_app, render_template, redirect, url_for
from flask_login import current_user, login_required
from dotenv import load_dotenv
from openai import OpenAI

from .models import db, Site, ScheduledPost, PromptTemplate, GenerationControl
from .image_search import search_images
from .forms import AutoPostForm

load_dotenv()
auto_post_bp = Blueprint("auto_post", __name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def enhance_h2_tags(content):
    return re.sub(r'(<h2.*?>)', r'\1<span style="font-size: 1.5em; font-weight: bold;">', content).replace("</h2>", "</span></h2>")

def clean_title(title):
    return re.sub(r'^[0-9\.\-ー①-⑩]+[\.\s）)]*|[「」\"]', '', title).strip()

def is_generation_stopped(user_id):
    control = GenerationControl.query.filter_by(user_id=user_id).first()
    return control and control.stop_flag

def generate_image_keyword_from_title(title):
    prompt = f"""
以下の日本語タイトルに対して、
Pixabayで画像を探すのに最適な英語の2～3語の検索キーワードを生成してください。
抽象的すぎる単語（life, business など）は避けてください。
写真としてヒットしやすい「モノ・場所・情景・体験・風景」などを選んでください。

タイトル: {title}"""
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "あなたはPixabay用の画像検索キーワード生成の専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=50
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ ChatGPTによる画像キーワード生成失敗:", e)
        return "nature"

def process_article(app, keyword, title_prompt, body_prompt, schedule_time, site, user_id):
    with app.app_context():
        if is_generation_stopped(user_id):
            print("🛑 停止フラグ検出 → 中断")
            return

        try:
            pre_post = ScheduledPost(
                title="生成中...",
                body="",
                keyword=keyword,
                featured_image=None,
                status="生成中",
                scheduled_time=schedule_time,
                created_at=datetime.utcnow(),
                site_url=site.site_url,
                username=site.wp_username,
                app_password=site.wp_app_password,
                user_id=user_id,
                site_id=site.id
            )
            db.session.add(pre_post)
            db.session.commit()

            # 🔹タイトル生成（プロンプトをそのまま渡す）
            title_input = title_prompt.replace("{{keyword}}", keyword.strip()) if title_prompt else keyword
            title_res = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "あなたはSEOの専門家です。"},
                    {"role": "user", "content": title_input}
                ],
                temperature=0.7,
                max_tokens=150
            )
            raw_title = title_res.choices[0].message.content.strip().split("\n")[0]
            title = clean_title(raw_title)
            print("✅ タイトル生成:", title)

            # 🔹本文生成（プロンプトをそのまま渡す）
            body_input = body_prompt.replace("{{title}}", title) if body_prompt else f"タイトル: {title}"
            body_res = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "あなたはSEOライターです。"},
                    {"role": "user", "content": body_input}
                ],
                temperature=0.7,
                max_tokens=3200
            )
            content = enhance_h2_tags(body_res.choices[0].message.content.strip())

            # 🔹アイキャッチ画像（本文中に挿入はしない）
            image_kw = generate_image_keyword_from_title(title)
            image_urls = search_images(image_kw, num_images=1)
            featured_image = image_urls[0] if image_urls else None

            # 🔹更新
            pre_post.title = title
            pre_post.body = content
            pre_post.featured_image = featured_image
            pre_post.status = "生成完了"
            db.session.commit()

            print(f"✅ 保存完了: {title}")
            time.sleep(2)

        except Exception as e:
            print(f"❌ 例外発生（{keyword}）: {e}")
            traceback.print_exc()
            db.session.rollback()

def generate_and_save_articles(app, keywords, title_prompt, body_prompt, site_id, user_id):
    with app.app_context():
        site = Site.query.filter_by(id=site_id, user_id=user_id).first()
        if not site:
            print("[エラー] サイト情報が見つかりません。")
            return

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

        futures = []
        scheduled_index = 0
        executor = ThreadPoolExecutor(max_workers=3)

        for keyword in keywords:
            article_count = random.choice([2, 3])
            for _ in range(article_count):
                schedule_time = schedule_times[scheduled_index] if scheduled_index < len(schedule_times) else now + timedelta(days=1)
                scheduled_index += 1

                futures.append(executor.submit(
                    process_article,
                    app,
                    keyword,
                    title_prompt,
                    body_prompt,
                    schedule_time,
                    site,
                    user_id
                ))

        for future in as_completed(futures):
            future.result()

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
