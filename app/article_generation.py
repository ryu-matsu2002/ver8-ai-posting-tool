import openai
from flask import current_app
from .models import db, ScheduledPost

openai.api_key = current_app.config['OPENAI_API_KEY']

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
        # ステータス更新：生成中
        post.status = "生成中"
        db.session.commit()

        # プロンプト生成
        prompt = f"タイトル: {post.title}\n\n{post.prompt_body}\n\nこの内容に基づいてSEOに強い日本語の記事を3000文字程度で作成してください。"

        # ChatGPT API呼び出し
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたはSEOに詳しいプロのライターです。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.7
        )

        # 本文を取得し保存
        generated_body = response.choices[0].message['content'].strip()
        post.body = generated_body
        post.status = "生成完了"
        db.session.commit()

        return True

    except Exception as e:
        post.status = "生成失敗"
        db.session.commit()
        print(f"❌ 生成エラー: {e}")
        return False
