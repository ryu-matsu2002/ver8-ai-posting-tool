from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import db, Article, Site, ScheduledPost, PromptTemplate
from datetime import datetime, timedelta
import random
import pytz

routes_bp = Blueprint('routes', __name__)

# 記事編集
@routes_bp.route('/edit_article/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Article.query.get_or_404(post_id)
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        db.session.commit()
        flash('記事を更新しました。')
        return redirect(url_for('routes.dashboard'))
    return render_template('edit_article.html', article=post)

# 記事削除
@routes_bp.route('/delete_article/<int:post_id>', methods=['GET'])
@login_required
def delete_post(post_id):
    post = Article.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('記事を削除しました。')
    return redirect(url_for('routes.dashboard'))

# 記事プレビュー
@routes_bp.route('/preview_article/<int:post_id>')
@login_required
def preview_post(post_id):
    post = Article.query.get_or_404(post_id)
    return render_template('preview_article.html', article=post)

# 即時投稿（仮処理）
@routes_bp.route('/publish_now/<int:post_id>')
@login_required
def publish_now(post_id):
    post = Article.query.get_or_404(post_id)
    post.status = "投稿済み"
    db.session.commit()
    flash('記事を即時投稿としてマークしました。')
    return redirect(url_for('routes.dashboard'))

# 記事生成を停止（仮機能）
@routes_bp.route('/stop_generation', methods=['POST'])
@login_required
def stop_generation():
    flash('記事生成処理を停止しました（仮）。')
    return redirect(url_for('routes.dashboard'))

# 全記事削除
@routes_bp.route('/delete_all_posts/<int:site_id>', methods=['POST'])
@login_required
def delete_all_posts(site_id):
    posts = Article.query.filter_by(site_id=site_id).all()
    for post in posts:
        db.session.delete(post)
    db.session.commit()
    flash('すべての記事を削除しました。')
    return redirect(url_for('routes.dashboard'))

# 自動投稿ページ（GET:表示 / POST:記事生成の開始）
@routes_bp.route('/auto-post', methods=['GET', 'POST'])
@login_required
def auto_post():
    sites = Site.query.filter_by(user_id=current_user.id).all()
    templates = PromptTemplate.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        site_id = int(request.form['site_id'])
        keywords = request.form['keywords'].strip().splitlines()
        title_prompt = request.form['title_prompt']
        body_prompt = request.form['body_prompt']

        site = Site.query.get_or_404(site_id)
        now = datetime.now()
        scheduled_count = 0

        for i, kw in enumerate(keywords[:40]):
            post_time = now + timedelta(days=i // 4, hours=random.randint(10, 21), minutes=random.randint(0, 59))

            post = ScheduledPost(
                genre=None,
                keyword=kw,
                title="",
                body="",
                featured_image=None,
                status="生成完了",
                scheduled_time=post_time,
                created_at=now,
                site_url=site.site_url,
                username=site.wp_username,
                app_password=site.wp_app_password,
                user_id=current_user.id,
                site_id=site.id
            )
            db.session.add(post)
            scheduled_count += 1

        db.session.commit()
        flash(f"{scheduled_count} 件のキーワードを登録し、生成完了として保存しました。")
        return redirect(url_for('routes.dashboard'))

    return render_template('auto_post.html', sites=sites, prompt_templates=templates)

# 投稿ログページ
@routes_bp.route('/admin/log/<int:site_id>')
@login_required
def admin_log(site_id):
    filter_status = request.args.get("status", None)
    query = ScheduledPost.query.filter_by(site_id=site_id, user_id=current_user.id)

    if filter_status:
        query = query.filter_by(status=filter_status)

    posts = query.order_by(ScheduledPost.scheduled_time.asc()).all()
    jst = pytz.timezone("Asia/Tokyo")
    return render_template('admin_log.html', posts=posts, jst=jst, site_id=site_id, filter_status=filter_status)

# プロンプトテンプレート保存＆一覧表示
@routes_bp.route('/prompt-templates', methods=['GET', 'POST'])
@login_required
def prompt_templates():
    if request.method == 'POST':
        genre = request.form['genre']
        title_prompt = request.form['title_prompt']
        body_prompt = request.form['body_prompt']

        template = PromptTemplate(
            genre=genre,
            title_prompt=title_prompt,
            body_prompt=body_prompt,
            user_id=current_user.id
        )
        db.session.add(template)
        db.session.commit()
        flash('テンプレートを保存しました')

    templates = PromptTemplate.query.filter_by(user_id=current_user.id).all()
    return render_template('prompt_templates.html', prompt_templates=templates)

# テンプレート削除
@routes_bp.route('/prompt-templates/delete/<int:template_id>', methods=['POST'])
@login_required
def delete_prompt_template(template_id):
    template = PromptTemplate.query.get_or_404(template_id)
    if template.user_id != current_user.id:
        flash('削除権限がありません')
        return redirect(url_for('routes.prompt_templates'))

    db.session.delete(template)
    db.session.commit()
    flash('テンプレートを削除しました')
    return redirect(url_for('routes.prompt_templates'))

# ✅ ダッシュボードルート（これが必要）
@routes_bp.route('/dashboard', endpoint='dashboard')
@login_required
def dashboard():
    user_sites = Site.query.filter_by(user_id=current_user.id).all()
    user_articles = Article.query.join(Site).filter(Site.user_id == current_user.id).all()
    return render_template('dashboard.html', username=current_user.username, sites=user_sites, articles=user_articles)
