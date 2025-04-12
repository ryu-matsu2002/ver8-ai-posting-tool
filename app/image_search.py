import requests
from flask import current_app

# Pixabay APIの設定
PIXABAY_API_KEY = current_app.config['PIXABAY_API_KEY']
PIXABAY_API_URL = "https://pixabay.com/api/"

def search_images(query, num_images=2):
    """
    記事に関連する画像をPixabayから検索して取得する関数
    """
    params = {
        'key': PIXABAY_API_KEY,
        'q': query,  # 検索キーワード
        'image_type': 'photo',  # 写真タイプ
        'per_page': num_images,  # 取得する画像の枚数
        'safeSearch': 'true',  # 安全検索を有効化
    }
    
    response = requests.get(PIXABAY_API_URL, params=params)
    data = response.json()

    # 画像のURLをリストとして取得
    image_urls = []
    for hit in data.get('hits', []):
        image_urls.append(hit['webformatURL'])  # 画像URLを取得

    return image_urls
