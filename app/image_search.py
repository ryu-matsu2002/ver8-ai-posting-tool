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
    query = re.sub(r'[。、，・！!？?\-＝＝…]', '', query)  # 全角記号も除去
    query = re.sub(r'\d+\.', '', query)  # 「1. keyword」など番号除去
    query = re.sub(r'[^\w\s]', '', query)  # 英数字・空白以外を削除
    query = re.sub(r'\s+', ' ', query)  # 多重スペースを1つに

    # 英単語3語以内に制限
    words = query.split()
    query = '+'.join(words[:3])

    return query[:100]  # 長すぎる検索語は100文字でカット


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
        if response.status_code != 200:
            print(f"❌ Pixabay APIリクエスト失敗: {response.status_code} - {response.text}")
            return []

        data = response.json()
        image_urls = [hit['webformatURL'] for hit in data.get('hits', [])]

        if not image_urls:
            print(f"⚠️ 画像が見つかりませんでした: {clean_kw}")

        return image_urls

    except requests.exceptions.RequestException as e:
        print(f"❌ Pixabay API例外発生: {e}")
        return []
