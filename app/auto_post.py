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
from .forms import AutoPostForm

load_dotenv()
auto_post_bp = Blueprint("auto_post", __name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ ベースプロンプト定義
title_base_prompt = """あなたはSEOとコンテンツマーケティングの専門家です。

次のキーワードに基づいてWEBサイト用のQ&A形式の「記事タイトル」を1つ考えてください。

キーワード：「{{keyword}}」

条件：
- キーワードの順番は変えない
- 必ずそのままキーワードを使う
- 文末は「？」にしてください
"""

body_base_prompt = """🔧執筆ルール（必ず守ること）

1. 構成：問題提起 → 共感 → 解決策
2. 読者は「あなた」と呼ぶこと（「皆さん」禁止）
3. 親友に語りかけるように、ただし敬語で
4. 改行は段落の終わりのみ、1〜3行で段落、段落間は2行空ける
5. 記事は2500〜3500文字程度
6. 適切な見出し（hタグ）を付けて構成する

次のタイトルに基づいて本文を生成してください：

タイトル：「{{title}}」
"""

def insert_images_after_headings_random(content, image_urls):
    headings = list(re.finditer(r'<h2.*?>.*?</h2>', content, flags=re.IGNORECASE))
    if not headings or not image_urls:
        return content

    insert_positions = random.sample(headings, min(2, len(headings), len(image_urls)))
    insert_positions.sort(key=lambda x: x.start())
    new_content = content
    offset = 0

    for heading in insert_positions:
        img_url = image_urls.pop(0)
        img_tag = f'<img src="{img_url}" style="max-width:100%; margin: 15px 0;">'
        insert_at = heading.end() + offset
        new_content = new_content[:insert_at] + "\n\n" + img_tag + new_content[insert_at:]
        offset += len(img_tag) + 2
        if not image_urls:
            break

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
        app_password = site.wp_app_password
        site_url = site.site_url

        jst = pytz.timezone("Asia/Tokyo")
        now = datetime.now(jst)
        base_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        schedule_times = []
        for day in range(30):
            base = base_start + timedelta(days=day)
            num_posts = random.choices([1, 2, 3, 4, 5], weights=[1, 2, 4, 6, 2])[0]
            hours = sorted(random.sample(range(10, 22), k=num_posts))
            for h in hours:
                minute = random.randint(0, 59)
                post_time = base.replace(hour=h, minute=minute)
                if post_time < now:
                    post_time = now + timedelta(minutes=5)
                schedule_times.append(post_time.astimezone(pytz.utc))

        scheduled_index = 0
        for keyword in keywords:
            article_count = random.choice([2, 3])
            for n in range(article_count):
                if is_generation_stopped(user_id):
                    print("🛑 停止フラグ検出。中断。")
                    return
                try:
                    print(f"\n▶ キーワード: {keyword}（{n+1}/{article_count}）")

                    title_full_prompt = title_base_prompt.replace("{{keyword}}", keyword.strip())
                    if title_prompt:
                        title_full_prompt += f"\n\n#補足:\n{title_prompt.strip()}"

                    print("📤 GPTへのタイトルプロンプト送信内容：")
                    print(title_full_prompt)

                    title_response = client.chat.completions.create(
                        model="gpt-4-turbo",
                        messages=[
                            {"role": "system", "content": "あなたはSEOに強い記事タイトルの専門家です。"},
                            {"role": "user", "content": title_full_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=100
                    )
                    title = title_response.choices[0].message.content.strip().split("\n")[0]
                    print("✅ タイトル生成:", title)

                    body_full_prompt = body_base_prompt.replace("{{title}}", title.strip())
                    if body_prompt:
                        body_full_prompt += f"\n\n#補足:\n{body_prompt.strip()}"

                    print("📤 GPTへの本文プロンプト送信内容：")
                    print(body_full_prompt)

                    content_response = client.chat.completions.create(
                        model="gpt-4-turbo",
                        messages=[
                            {"role": "system", "content": "あなたはSEO記事ライターです。"},
                            {"role": "user", "content": body_full_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=2000
                    )
                    content = content_response.choices[0].message.content.strip()
                    if len(content) < 100:
                        print("❌ 本文が短すぎる → スキップ")
                        continue

                    image_urls = search_images(keyword, num_images=3)
                    featured_image = image_urls[0] if image_urls else None
                    if len(image_urls) > 1:
                        content = insert_images_after_headings_random(content, image_urls[1:3])

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
