# 📄 app/image_search.py

import requests
from flask import current_app
import re

def clean_query(query):
    """
    Pixabay用クエリの調整：引用符や記号などPixabayが受け入れない文字を除去
    """
    query = query.strip().lower()
    query = re.sub(r'[\"\'\(\)\[\]\{\}:;]', '', query)  # 記号除去
    query = re.sub(r'[^\w\s]', '', query)              # 英数字・空白以外を削除
    query = re.sub(r'\s+', '+', query)                 # 空白を + に変換（Pixabay仕様）
    query = query[:100]                                # 長すぎる検索語をカット
    return query

def search_images(query, num_images=2):
    """
    Pixabayから画像URLを取得（整形済みクエリ使用）
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
        'lang': 'en',
    }

    try:
        response = requests.get(PIXABAY_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        image_urls = [hit['webformatURL'] for hit in data.get('hits', [])]

        if not image_urls:
            print(f"⚠️ 画像が見つかりませんでした: {clean_kw}")

        return image_urls

    except requests.exceptions.RequestException as e:
        print(f"❌ Pixabay APIリクエストに失敗しました: {e}")
        return []
