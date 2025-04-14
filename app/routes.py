from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from .models import db, Article, Site, ScheduledPost, PromptTemplate, GenerationControl
from datetime import datetime
import pytz
import threading
from .wordpress_post import post_to_wordpress

from .auto_post import generate_and_save_articles  # 🔸追加ポイント

routes_bp = Blueprint('routes', __name__)

# ✅ ダッシュボード
@routes_bp.route('/dashboard', endpoint='dashboard')
@login_required
def dashboard():
    user_sites = Site.query.filter_by(user_id=current_user.id).all()
    user_articles = Article.query.join(Site).filter(Site.user_id == current_user.id).all()
    return render_template('dashboard.html', username=current_user.username, sites=user_sites, articles=user_articles)

# ✅ Article系：編集
@routes_bp.route('/edit_article/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_article(post_id):
    post = Article.query.get_or_404(post_id)
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        db.session.commit()
        flash('記事を更新しました。')
        return redirect(url_for('routes.dashboard'))
    return render_template('edit_article.html', article=post)

# ✅ Article系：削除
@routes_bp.route('/delete_article/<int:post_id>', methods=['GET'])
@login_required
def delete_article(post_id):
    post = Article.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('記事を削除しました。')
    return redirect(url_for('routes.dashboard'))

# ✅ Article系：プレビュー
@routes_bp.route('/preview_article/<int:post_id>')
@login_required
def preview_article(post_id):
    post = Article.query.get_or_404(post_id)
    return render_template('preview_article.html', article=post)


# ✅ 全記事削除
@routes_bp.route('/delete_all_posts/<int:site_id>', methods=['POST'])
@login_required
def delete_all_posts(site_id):
    posts = Article.query.filter_by(site_id=site_id).all()
    for post in posts:
        db.session.delete(post)
    db.session.commit()
    flash('すべての記事を削除しました。')
    return redirect(url_for('routes.dashboard'))

# ✅ 自動投稿ページ
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

        app_instance = current_app._get_current_object()
        thread = threading.Thread(
            target=generate_and_save_articles,
            args=(app_instance, keywords, title_prompt, body_prompt, site_id, current_user.id)
        )
        thread.start()

        flash("記事生成を開始しました。生成状況はログで確認してください。")
        return redirect(url_for('routes.admin_log', site_id=site_id))

    return render_template('auto_post.html', sites=sites, prompt_templates=templates)

# ✅ 投稿ログ
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

# ✅ テンプレート登録/一覧
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

# ✅ テンプレート削除
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

# ✅ トップページ
@routes_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

# ✅ サイト追加
@routes_bp.route('/add-site', methods=['GET', 'POST'], endpoint='add_site')
@login_required
def add_site():
    if request.method == 'POST':
        site_url = request.form['site_url']
        wp_username = request.form['wp_username']
        wp_app_password = request.form['wp_app_password']

        new_site = Site(
            site_url=site_url,
            wp_username=wp_username,
            wp_app_password=wp_app_password,
            user_id=current_user.id
        )
        db.session.add(new_site)
        db.session.commit()
        flash('サイトを追加しました。')
        return redirect(url_for('routes.dashboard'))

    return render_template('add_site.html')

# ✅ ScheduledPost：プレビュー
@routes_bp.route('/preview_post/<int:post_id>')
@login_required
def preview_scheduled_post(post_id):
    post = ScheduledPost.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        flash('閲覧権限がありません')
        return redirect(url_for('routes.dashboard'))
    return render_template('preview_article.html', article=post)

# ✅ ScheduledPost：編集
@routes_bp.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_scheduled_post(post_id):
    post = ScheduledPost.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        flash('編集権限がありません')
        return redirect(url_for('routes.dashboard'))

    if request.method == 'POST':
        post.title = request.form['title']
        post.body = request.form['body']
        scheduled_time = request.form.get('scheduled_time')
        if scheduled_time:
            post.scheduled_time = datetime.strptime(scheduled_time, '%Y-%m-%d %H:%M')
        db.session.commit()
        flash('記事を更新しました')
        return redirect(url_for('routes.admin_log', site_id=post.site_id))

    return render_template('edit_article.html', post=post)

# ✅ ScheduledPost：削除
@routes_bp.route('/delete_post/<int:post_id>')
@login_required
def delete_scheduled_post(post_id):
    post = ScheduledPost.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        flash('削除権限がありません')
        return redirect(url_for('routes.dashboard'))

    db.session.delete(post)
    db.session.commit()
    flash('記事を削除しました')
    return redirect(url_for('routes.admin_log', site_id=post.site_id))

# ✅ ScheduledPost：即時投稿
@routes_bp.route('/publish_now/<int:post_id>')
@login_required
def publish_scheduled_now(post_id):
    post = ScheduledPost.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        return "権限がありません", 403

    success = post_to_wordpress(
        site_url=post.site_url,
        wp_username=post.username,
        wp_app_password=post.app_password,
        title=post.title,
        content=post.body,
        images=[post.featured_image] if post.featured_image else []
    )
    if success:
        post.status = '投稿済み'
        db.session.commit()
        flash('投稿が完了しました', 'success')
    else:
        flash('投稿に失敗しました', 'error')

    return redirect(url_for('routes.admin_log', site_id=post.site_id))

@routes_bp.route('/stop_generation', methods=['POST'])
@login_required
def stop_generation():
    control = GenerationControl.query.filter_by(user_id=current_user.id).first()
    if not control:
        control = GenerationControl(user_id=current_user.id, stop_flag=True)
        db.session.add(control)
    else:
        control.stop_flag = True
    db.session.commit()
    flash('記事生成を停止しました。')
    return redirect(url_for('routes.dashboard'))
