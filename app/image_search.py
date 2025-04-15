# 📄 app/image_search.py

import requests
from flask import current_app
import re

def clean_query(query):
    """
    Pixabay用クエリの調整：Pixabayが受け付けない文字を除去し、検索精度を向上
    """
    query = query.strip().lower()
    query = re.sub(r'[\"\'\(\)\[\]\{\}:;]', '', query)  # 記号除去
    query = re.sub(r'\s+', ' ', query)  # 複数スペースを1つに
    query = query.replace('　', ' ')  # 全角スペース→半角
    return query

def search_images(query, num_images=2):
    """
    与えられたクエリ（英語）をもとにPixabayから画像を検索し、画像URLを返す
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
        else:
            print(f"✅ Pixabay画像取得成功（{clean_kw}）: {len(image_urls)}件")

        return image_urls

    except requests.exceptions.RequestException as e:
        print(f"❌ Pixabay APIリクエストに失敗しました: {e}（キーワード: {clean_kw}）")
        return []
