# 📄 app/image_search.py

import requests
from flask import current_app
import re

def clean_query(query):
    """
    Pixabay用クエリの整形：
    記号・全角文字・番号などを除去し、検索に適した形へ変換。
    """
    query = query.strip().lower()
    query = re.sub(r'[\"\'\(\)\[\]\{\}:;]', '', query)       # 記号除去
    query = re.sub(r'[。、，・！!？?\-＝＝…]', '', query)     # 全角記号除去
    query = re.sub(r'\d+\.', '', query)                      # 番号（1. など）除去
    query = re.sub(r'[^\w\s]', '', query)                    # 英数字・空白以外除去
    query = re.sub(r'\s+', ' ', query)                       # 複数スペースを1つに
    words = query.split()
    query = '+'.join(words[:3])                              # 3語まで

    return query[:100]  # 文字数制限（Pixabay推奨）

def search_images(query, num_images=2):
    """
    Pixabay APIを使って画像URLリストを返す。
    - query: 日本語または英語の検索語（英語推奨）
    - num_images: 必要な画像枚数（最大3程度）
    """
    PIXABAY_API_KEY = current_app.config.get('PIXABAY_API_KEY')
    PIXABAY_API_URL = "https://pixabay.com/api/"

    if not PIXABAY_API_KEY:
        print("❌ Pixabay APIキーが設定されていません")
        return []

    clean_kw = clean_query(query)

    params = {
        'key': PIXABAY_API_KEY,
        'q': clean_kw,
        'image_type': 'photo',
        'per_page': num_images,
        'safesearch': 'true',
        'lang': 'en'
    }

    try:
        response = requests.get(PIXABAY_API_URL, params=params, timeout=10)
        if response.status_code != 200:
            print(f"❌ Pixabay APIリクエスト失敗: {response.status_code} - {response.text}")
            return []

        data = response.json()
        image_urls = [hit['webformatURL'] for hit in data.get('hits', [])]

        if not image_urls:
            print(f"⚠️ 画像が見つかりませんでした（検索語: {clean_kw}）")

        return image_urls

    except requests.exceptions.RequestException as e:
        print(f"❌ Pixabay API例外発生: {e}")
        return []
