import requests
from flask import current_app

def search_images(query, num_images=2):
    """
    記事に関連する画像をPixabayから検索して取得する関数
    """
    PIXABAY_API_KEY = current_app.config['PIXABAY_API_KEY']
    PIXABAY_API_URL = "https://pixabay.com/api/"
    
    params = {
        'key': PIXABAY_API_KEY,
        'q': query,  # 検索キーワード
        'image_type': 'photo',
        'per_page': num_images,
        'safesearch': 'true',
    }
    
    response = requests.get(PIXABAY_API_URL, params=params)
    data = response.json()

    # 画像のURLをリストとして取得
    image_urls = []
    for hit in data.get('hits', []):
        image_urls.append(hit['webformatURL'])

    return image_urls
