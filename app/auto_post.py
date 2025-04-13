# 📄 app/auto_post.py

import os
import threading
import time
import random
from datetime import datetime, timedelta
import pytz

from flask import Blueprint, request, current_app, render_template, redirect, url_for
from flask_login import current_user, login_required
from dotenv import load_dotenv
from openai import OpenAI

from models import db, Site, ScheduledPost, PromptTemplate
from image_search import search_images

load_dotenv()

auto_post_bp = Blueprint("auto_post", __name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_and_save_articles(app, keywords, title_prompt, body_prompt, site_id, user_id):
    with app.app_context():
        site = Site.query.filter_by(id=site_id, user_id=user_id).first()
        if not site:
            return

        jst = pytz.timezone("Asia/Tokyo")
        now = datetime.now(jst).replace(hour=0, minute=0, second=0, microsecond=0)

        schedule_times = []
        for day in range(30):
            base = now + timedelta(days=day)
            num_posts = random.choices([1, 2, 3, 4, 5], weights=[1, 2, 4, 6, 2])[0]
            hours = random.sample(range(10, 21), k=min(num_posts, 11))
            for h in sorted(hours):
                minute = random.randint(0, 59)
                post_time = base.replace(hour=h, minute=minute)
                schedule_times.append(post_time.astimezone(pytz.utc))

        for i, keyword in enumerate(keywords[:120]):
            try:
                # ユーザー入力プロンプトを適用
                title_full_prompt = title_prompt.replace("{{keyword}}", keyword)
                body_full_prompt = body_prompt.replace("{{title}}", keyword)

                # タイトル生成
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

                # 本文生成
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

                # 画像検索
                image_keywords = keyword
                image_urls = search_images(image_keywords, num_images=3)
                featured_image = image_urls[0] if image_urls else None

                post = ScheduledPost(
                    title=title,
                    body=content,
                    keyword=keyword,
                    featured_image=featured_image,
                    images=image_urls,
                    status="生成完了",
                    scheduled_time=schedule_times[i],
                    site_id=site_id,
                    user_id=user_id
                )
                db.session.add(post)
                db.session.commit()
                time.sleep(5)

            except Exception as e:
                print(f"キーワード {keyword} の生成中にエラーが発生しました: {e}")

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

        app_instance = current_app._get_current_object()
        thread = threading.Thread(
            target=generate_and_save_articles,
            args=(app_instance, keywords, title_prompt, body_prompt, site_id, current_user.id)
        )
        thread.start()
        return redirect(url_for('routes.dashboard'))  # 必要なら admin_log に変更

    return render_template('auto_post.html', sites=sites, prompt_templates=templates)
