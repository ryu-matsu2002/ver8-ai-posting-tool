# 📄 app/article_worker.py

import os
import time
import re
import traceback
from datetime import datetime
import pytz
from openai import OpenAI

from app import create_app
from app.models import db, ScheduledPost, GenerationControl
from app.image_search import search_images

# Flaskアプリ生成
app = create_app()

# 🔧 タイトル整形
def clean_title(title):
    return re.sub(r'^[0-9\.\-ー①-⑩]+[\.\s）)]*|[「」\"]', '', title).strip()

# 🔧 h2タグに強調スタイルを追加
def enhance_h2_tags(content):
    return re.sub(r'(<h2.*?>)', r'\1<span style="font-size: 1.5em; font-weight: bold;">', content).replace("</h2>", "</span></h2>")

# 🔧 Pixabay用の画像キーワード生成
def generate_image_keyword_from_title(title, client):
    prompt = f"""
以下の日本語タイトルに対して、
Pixabayで画像を探すのに最適な英語の2〜3語の検索キーワードを生成してください。
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
        print("❌ 画像キーワード生成エラー:", e)
        return "nature"

# 🔁 記事生成ワーカー処理
def run_worker():
    with app.app_context():
        print("🚀 Worker 実行中...")
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        now = datetime.utcnow()

        posts = ScheduledPost.query.filter_by(status="生成中").order_by(ScheduledPost.created_at).limit(5).all()

        if not posts:
            print("✅ 生成対象の投稿はありません")
            return

        for post in posts:
            try:
                print(f"📝 生成処理開始: {post.keyword}")

                control = GenerationControl.query.filter_by(user_id=post.user_id).first()
                if control and control.stop_flag:
                    print("🛑 停止フラグ検出 → スキップ")
                    continue

                # タイトル生成
                title_prompt = post.prompt_title.replace("{{keyword}}", post.keyword)
                title_res = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "あなたはSEOの専門家です。"},
                        {"role": "user", "content": title_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                raw_title = title_res.choices[0].message.content.strip().split("\n")[0]
                title = clean_title(raw_title)
                print("✅ タイトル生成成功:", title)

                # 本文生成
                body_prompt = post.prompt_body.replace("{{title}}", title)
                body_res = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "あなたはSEOライターです。"},
                        {"role": "user", "content": body_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=3200
                )
                content = enhance_h2_tags(body_res.choices[0].message.content.strip())
                print("✅ 本文生成成功")

                # 画像検索
                image_kw = generate_image_keyword_from_title(title, client)
                image_urls = search_images(image_kw, num_images=1)
                featured_image = image_urls[0] if image_urls else None
                print("✅ 画像取得成功:", featured_image or "なし")

                # DB更新
                post.title = title
                post.body = content
                post.featured_image = featured_image
                post.status = "生成完了"
                db.session.commit()
                print("✅ 保存完了")

                time.sleep(2)

            except Exception as e:
                print("❌ エラー発生:", e)
                traceback.print_exc()
                db.session.rollback()

# 🔁 Renderでの永続ワーカー処理
if __name__ == "__main__":
    while True:
        run_worker()
        print("⏳ 次回チェックまで30秒待機...")
        time.sleep(30)
