# 📄 app/auto_post.py

import os
import threading
import time
import random
from datetime import datetime, timedelta
import pytz
import traceback
import re

from flask import Blueprint, request, current_app, render_template, redirect, url_for
from flask_login import current_user, login_required
from dotenv import load_dotenv
from openai import OpenAI

from .models import db, Site, ScheduledPost, PromptTemplate, GenerationControl
from .image_search import search_images

load_dotenv()

auto_post_bp = Blueprint("auto_post", __name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def insert_images_after_headings(content, image_urls):
    headings = list(re.finditer(r'<h2.*?>.*?</h2>', content, flags=re.IGNORECASE))
    img_tags = [f'<img src="{url}" style="max-width:100%; margin-top:10px;">' for url in image_urls[:2]]

    if not headings:
        return content + "\n\n" + "\n".join(img_tags)

    new_content = content
    offset = 0
    for i in range(min(2, len(headings), len(img_tags))):
        end = headings[i].end() + offset
        new_content = new_content[:end] + "\n\n" + img_tags[i] + new_content[end:]
        offset += len(img_tags[i]) + 2
    return new_content

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
        app_password = site.app_password
        site_url = site.site_url

        jst = pytz.timezone("Asia/Tokyo")
        now = datetime.now(jst).replace(hour=0, minute=0, second=0, microsecond=0)

        schedule_times = []
        for day in range(30):
            base = now + timedelta(days=day)
            num_posts = random.choices([1, 2, 3, 4, 5], weights=[1, 2, 4, 6, 2])[0]
            hours = random.sample(range(10, 22), k=min(num_posts, 11))
            for h in sorted(hours):
                minute = random.randint(0, 59)
                post_time = base.replace(hour=h, minute=minute)
                schedule_times.append(post_time.astimezone(pytz.utc))

        for i, keyword in enumerate(keywords[:120]):
            if is_generation_stopped(user_id):
                print("🛑 停止フラグが検出されたため、記事生成を中断します。")
                break

            try:
                print(f"▶ [{i+1}/{len(keywords)}] 記事生成開始: {keyword}")

                title_full_prompt = title_prompt.replace("{{keyword}}", keyword)
                body_full_prompt = body_prompt.replace("{{title}}", keyword)

                title_response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "あなたはSEOに強い記事タイトルの専門家です。"},
                        {"role": "user", "content": title_full_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=200
                )
                title = title_response.choices[0].message.content.strip().split("\n")[0]
                print(f"✅ タイトル生成成功: {title}")

                content_response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "あなたはSEO記事ライターです。"},
                        {"role": "user", "content": body_full_prompt.replace("{{title}}", title)}
                    ],
                    temperature=0.7,
                    max_tokens=3000
                )
                content = content_response.choices[0].message.content.strip()

                image_urls = search_images(keyword, num_images=3)
                featured_image = image_urls[0] if image_urls else None

                if len(image_urls) > 1:
                    content = insert_images_after_headings(content, image_urls[1:3])

                post = ScheduledPost(
                    title=title,
                    body=content,
                    keyword=keyword,
                    featured_image=featured_image,
                    status="生成完了",
                    scheduled_time=schedule_times[i],
                    created_at=datetime.utcnow(),
                    site_url=site_url,
                    username=username,
                    app_password=app_password,
                    user_id=user_id,
                    site_id=site_id
                )
                db.session.add(post)
                db.session.commit()
                print(f"✅ 保存成功: {title}")
                time.sleep(5)

            except Exception as e:
                print(f"❌ エラー発生（{keyword}）: {e}")
                traceback.print_exc()
                db.session.rollback()

@auto_post_bp.route('/auto-post', methods=['GET', 'POST'])
@login_required
def auto_post():
    sites = Site.query.filter_by(user_id=current_user.id).all()
    templates = PromptTemplate.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        keywords = request.form.get('keywords', '').splitlines()
        site_id = int(request.form.get('site_id'))
        title_prompt = request.form.get('title_prompt')
        body_prompt = request.form.get('body_prompt')

        # 停止フラグをFalseに初期化
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

    return render_template('auto_post.html', sites=sites, prompt_templates=templates)
