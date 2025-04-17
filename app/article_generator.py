# app/article_generation.py

import openai
from flask import current_app
from .models import db, ScheduledPost

def generate_article_for_post(post_id):
    """
    指定された投稿IDのScheduledPostに対して記事生成を行い、
    生成された本文を保存し、ステータスを「生成完了」に更新する。
    """

    # 対象記事をDBから取得
    post = ScheduledPost.query.get(post_id)
    if not post or post.status != "生成待ち":
        return False  # 対象がない、または状態が不適切

    try:
        # アプリケーションコンテキストを明示的に使用
        openai.api_key = current_app.config['OPENAI_API_KEY']

        # ステータス更新：生成中
        post.status = "生成中"
        db.session.commit()

        # プロンプト生成
        prompt = f"タイトル: {post.title}\n\n{post.prompt_body}\n\nこの内容に基づいてSEOに強い日本語の記事を3000文字で書いてください。"

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたはSEOに強い日本語のライターです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3200,
        )

        generated_text = response.choices[0].message.content.strip()

        # 結果保存
        post.body = generated_text
        post.status = "生成完了"
        db.session.commit()

        return True

    except Exception as e:
        print(f"❌ 記事生成失敗: {e}")
        post.status = "生成失敗"
        db.session.commit()
        return False
