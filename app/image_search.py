# 📄 app/image_search.py

import requests
from flask import current_app

def search_images(query, num_images=2):
    """
    英語キーワードでPixabayから画像を検索し、画像URLを返す関数
    """
    PIXABAY_API_KEY = current_app.config.get('PIXABAY_API_KEY')
    PIXABAY_API_URL = "https://pixabay.com/api/"

    if not PIXABAY_API_KEY:
        print("❌ Pixabay APIキーが設定されていません")
        return []

    params = {
        'key': PIXABAY_API_KEY,
        'q': query,
        'image_type': 'photo',
        'per_page': num_images,
        'safesearch': 'true',
        'lang': 'en',  # 英語キーワード前提
    }

    try:
        response = requests.get(PIXABAY_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        image_urls = [hit['webformatURL'] for hit in data.get('hits', [])]
        if not image_urls:
            print(f"⚠️ 画像が見つかりませんでした: {query}")

        return image_urls

    except requests.exceptions.RequestException as e:
        print(f"❌ Pixabay APIリクエストに失敗しました: {e}")
        return []
