# 📄 app/article_worker.py

import time
import traceback
from app import create_app
from app.models import db, Site, ScheduledPost, PromptTemplate, GenerationControl
from flask import current_app
from openai import OpenAI
from app.image_search import search_images
from datetime import datetime
import pytz
import os
import re

# Flaskアプリ作成
app = create_app()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def enhance_h2_tags(content):
    return re.sub(r'(<h2.*?>)', r'\1<span style="font-size: 1.5em; font-weight: bold;">', content).replace("</h2>", "</span></h2>")

def clean_title(title):
    return re.sub(r'^[0-9\.\-ー①-⑩]+[\.\s）)]*|[「」\"]', '', title).strip()

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

def run_worker():
    with app.app_context():
        print("🚀 Worker 起動中...")

        jst = pytz.timezone("Asia/Tokyo")
        now = datetime.now(jst).astimezone(pytz.utc)

        # 「生成待ち」状態の投稿を取得
        pending_posts = ScheduledPost.query.filter_by(status="生成待ち").filter(ScheduledPost.scheduled_time <= now).limit(5).all()

        if not pending_posts:
            print("✅ 処理対象なし（生成待ち記事なし）")
            return

        for post in pending_posts:
            try:
                print(f"\n📝 記事生成開始: keyword={post.keyword} | site_id={post.site_id}")

                # 停止フラグ確認
                control = GenerationControl.query.filter_by(user_id=post.user_id).first()
                if control and control.stop_flag:
                    print("🛑 停止フラグによりスキップ")
                    continue

                # タイトル生成
                title_input = post.prompt_title.replace("{{keyword}}", post.keyword) if post.prompt_title else post.keyword
                title_res = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[{"role": "system", "content": "あなたはSEOの専門家です。"},
                              {"role": "user", "content": title_input}],
                    temperature=0.7,
                    max_tokens=150
                )
                raw_title = title_res.choices[0].message.content.strip().split("\n")[0]
                title = clean_title(raw_title)
                print("✅ タイトル生成:", title)

                # 本文生成
                body_input = post.prompt_body.replace("{{title}}", title) if post.prompt_body else f"タイトル: {title}"
                body_res = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[{"role": "system", "content": "あなたはSEOライターです。"},
                              {"role": "user", "content": body_input}],
                    temperature=0.7,
                    max_tokens=3200
                )
                content = enhance_h2_tags(body_res.choices[0].message.content.strip())

                # 画像検索
                image_kw = generate_image_keyword_from_title(title)
                image_urls = search_images(image_kw, num_images=1)
                featured_image = image_urls[0] if image_urls else None

                # DB更新
                post.title = title
                post.body = content
                post.featured_image = featured_image
                post.status = "生成完了"
                db.session.commit()

                print("✅ 記事生成完了:", title)
                time.sleep(2)

            except Exception as e:
                print("❌ 記事生成中に例外発生:", e)
                traceback.print_exc()
                db.session.rollback()

if __name__ == "__main__":
    while True:
        run_worker()
        print("⏳ 次のチェックまで30秒待機...")
        time.sleep(30)
