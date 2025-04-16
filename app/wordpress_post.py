# 📄 app/wordpress_post.py

import requests
import json
import base64
from datetime import datetime

def upload_featured_image(site_url, wp_username, wp_app_password, image_url):
    """
    画像URLをWordPressにアップロードし、メディアIDを返す
    """
    try:
        response_img = requests.get(image_url, timeout=10)
        response_img.raise_for_status()
        image_data = response_img.content
        filename = image_url.split("/")[-1]

        token = base64.b64encode(f"{wp_username}:{wp_app_password}".encode()).decode('utf-8')
        headers = {
            'Authorization': f'Basic {token}',
            'User-Agent': 'Mozilla/5.0 (compatible; AI-Posting-Bot/1.0)',
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'image/jpeg'
        }

        response = requests.post(
            f"{site_url}/wp-json/wp/v2/media",
            headers=headers,
            data=image_data,
            timeout=15
        )

        if response.status_code == 201:
            print(f"✅ 画像アップロード成功: {filename}")
            return response.json().get('id')
        else:
            print(f"❌ 画像アップロード失敗: {response.status_code}")
            print("📄 レスポンス内容:", response.text)

            log_entry = (
                f"[{datetime.utcnow()}] 画像アップロード失敗\n"
                f"画像URL: {image_url}\n"
                f"サイト: {site_url}\n"
                f"ステータス: {response.status_code}\n"
                f"レスポンス: {response.text}\n\n"
            )
            with open("wp_post_errors.log", "a", encoding="utf-8") as log_file:
                log_file.write(log_entry)

            return None

    except Exception as e:
        print(f"❌ 画像アップロード中に例外発生: {e}")
        return None


def post_to_wordpress(site_url, wp_username, wp_app_password, title, content, images):
    """
    WordPressへ記事投稿（アイキャッチ画像含む）
    """
    token = base64.b64encode(f"{wp_username}:{wp_app_password}".encode()).decode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {token}',
        'User-Agent': 'Mozilla/5.0 (compatible; AI-Posting-Bot/1.0)'
    }

    # アイキャッチ画像のID取得
    featured_image_id = None
    if images and images[0]:
        featured_image_id = upload_featured_image(site_url, wp_username, wp_app_password, images[0])

    data = {
        'title': title,
        'content': content,
        'status': 'publish'
    }
    if featured_image_id:
        data['featured_media'] = featured_image_id

    try:
        response = requests.post(
            f'{site_url}/wp-json/wp/v2/posts',
            headers=headers,
            data=json.dumps(data),
            timeout=20
        )

        if response.status_code == 201:
            print(f"✅ 投稿成功: {title}")
            return True
        else:
            print(f"❌ 投稿失敗: {response.status_code}")
            print("📄 レスポンス内容:", response.text)

            log_entry = (
                f"[{datetime.utcnow()}] 投稿失敗\n"
                f"サイト: {site_url}\n"
                f"タイトル: {title}\n"
                f"ステータス: {response.status_code}\n"
                f"レスポンス: {response.text}\n\n"
            )
            with open("wp_post_errors.log", "a", encoding="utf-8") as log_file:
                log_file.write(log_entry)

            return False

    except Exception as e:
        print(f"❌ 投稿処理中に例外発生: {e}")
        return False
