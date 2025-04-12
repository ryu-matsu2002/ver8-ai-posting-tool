# app/wordpress_post.py

import requests
import json
import base64

def upload_featured_image(site_url, wp_username, wp_app_password, image_url):
    """Pixabay画像URLをWordPressにアップロードし、画像IDを返す"""
    try:
        image_data = requests.get(image_url).content
        filename = image_url.split("/")[-1]
        headers = {
            'Content-Disposition': f'attachment; filename={filename}',
            'Content-Type': 'image/jpeg',
        }

        response = requests.post(
            f"{site_url}/wp-json/wp/v2/media",
            headers=headers,
            auth=(wp_username, wp_app_password),
            data=image_data
        )
        if response.status_code == 201:
            media_id = response.json().get('id')
            return media_id
        else:
            print(f"画像アップロード失敗: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"画像アップロード中にエラー: {e}")
        return None


def post_to_wordpress(site_url, wp_username, wp_app_password, title, content, images):
    """WordPressへ記事を投稿し、画像も含めて反映する"""
    headers = {
        'Content-Type': 'application/json'
    }

    # アイキャッチ画像のアップロード
    featured_image_id = None
    if images:
        featured_image_id = upload_featured_image(site_url, wp_username, wp_app_password, images[0])
        # content の先頭に画像も追加
        content = f'<img src="{images[0]}" style="max-width:100%;">\n' + content

    # 投稿データ
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
            auth=(wp_username, wp_app_password),
            data=json.dumps(data)
        )
        if response.status_code == 201:
            print(f"✅ 投稿成功: {title}")
            return True
        else:
            print(f"❌ 投稿失敗: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"投稿処理エラー: {e}")
        return False
