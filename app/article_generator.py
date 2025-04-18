# 📄 app/article_generator.py

import os
import traceback
from openai import OpenAI
from .models import db, ScheduledPost

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_article_for_post(post_id):
    """
    指定された投稿IDのScheduledPostに対して記事生成を行い、
    生成された本文を保存し、ステータスを「生成完了」に更新する。
    """
    post = ScheduledPost.query.get(post_id)

    if not post or post.status not in ["生成待ち", "生成中"]:
        print(f"⚠️ スキップ: 該当なしまたは不正なステータス → post_id={post_id}")
        return False

    try:
        # ステータス更新
        post.status = "生成中"
        db.session.commit()

        # 🔹 タイトル生成（プロンプトから）
        title_prompt = post.prompt_title.replace("{{keyword}}", post.keyword)
        title_res = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "あなたはSEOに強い日本語記事のタイトル作成者です。"},
                {"role": "user", "content": title_prompt}
            ],
            temperature=0.7,
            max_tokens=150,
        )
        title = title_res.choices[0].message.content.strip().split("\n")[0]
        post.title = title

        # 🔹 本文生成（{{title}} を埋め込み）
        body_prompt = post.prompt_body.replace("{{title}}", title)
        body_res = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "あなたはSEOに強い日本語ライターです。"},
                {"role": "user", "content": body_prompt}
            ],
            temperature=0.7,
            max_tokens=3200,
        )
        body = body_res.choices[0].message.content.strip()

        # 🔹 保存
        post.body = body
        post.status = "生成完了"
        db.session.commit()
        print(f"✅ 記事生成完了: {title}")

        return True

    except Exception as e:
        print(f"❌ 記事生成失敗（ID: {post_id}）: {e}")
        traceback.print_exc()
        post.status = "生成失敗"
        db.session.commit()
        return False
