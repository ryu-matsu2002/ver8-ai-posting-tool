import openai
from flask import current_app

# OpenAI APIキーを設定（環境変数から読み込む方法もあり）
openai.api_key = current_app.config['OPENAI_API_KEY']

def generate_article(title, body_prompt):
    """
    記事タイトルと本文プロンプトに基づいて記事を生成する関数
    """
    prompt = f"タイトル: {title}\n本文: {body_prompt}\n\nこの内容に基づいてSEOに強い記事を生成してください。"

    response = openai.Completion.create(
        engine="gpt-4",  # GPT-4を使用
        prompt=prompt,
        max_tokens=2000,  # 記事の最大長（必要に応じて調整）
        n=1,  # 1回だけ生成
        stop=None,  # 終了トークン
        temperature=0.7  # 出力のランダム性
    )

    # 生成した記事の内容を取得
    generated_article = response.choices[0].text.strip()
    
    return generated_article
