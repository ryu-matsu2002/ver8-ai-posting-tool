from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from .models import db, Article, Site, ScheduledPost, PromptTemplate, GenerationControl
from datetime import datetime, timedelta, time as dtime
import pytz
import random
from .wordpress_post import post_to_wordpress
from .forms import AddSiteForm, PromptTemplateForm

routes_bp = Blueprint('routes', __name__)

@routes_bp.route('/dashboard', endpoint='dashboard')
@login_required
def dashboard():
    user_sites = Site.query.filter_by(user_id=current_user.id).all()
    user_articles = Article.query.join(Site).filter(Site.user_id == current_user.id).all()
    return render_template('dashboard.html', username=current_user.username, sites=user_sites, articles=user_articles)

@routes_bp.route('/admin/log/<int:site_id>')
@login_required
def admin_log(site_id):
    filter_status = request.args.get("status", None)
    query = ScheduledPost.query.filter_by(site_id=site_id, user_id=current_user.id)
    if filter_status:
        query = query.filter_by(status=filter_status)
    posts = query.order_by(ScheduledPost.created_at.desc()).all()
    jst = pytz.timezone("Asia/Tokyo")
    return render_template('admin_log.html', posts=posts, jst=jst, site_id=site_id, filter_status=filter_status)

@routes_bp.route('/preview_post/<int:post_id>', endpoint='preview_scheduled_post')
@login_required
def preview_scheduled_post(post_id):
    post = ScheduledPost.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        flash('閲覧権限がありません')
        return redirect(url_for('routes.dashboard'))
    return render_template('preview_article.html', article=post)

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

@routes_bp.route('/prompt-templates', methods=['GET', 'POST'])
@login_required
def prompt_templates():
    form = PromptTemplateForm()
    if form.validate_on_submit():
        genre = form.genre.data.strip()
        title_prompt = form.title_prompt.data.strip()
        body_prompt = form.body_prompt.data.strip()
        if "{{keyword}}" not in title_prompt:
            title_prompt = "{{keyword}}\n\n" + title_prompt
        if "{{title}}" not in body_prompt:
            body_prompt = "{{title}}\n\n" + body_prompt
        template = PromptTemplate(
            genre=genre,
            title_prompt=title_prompt,
            body_prompt=body_prompt,
            user_id=current_user.id
        )
        db.session.add(template)
        db.session.commit()
        flash("テンプレートを保存しました", "success")
        return redirect(url_for('routes.prompt_templates'))
    templates = PromptTemplate.query.filter_by(user_id=current_user.id).all()
    return render_template('prompt_templates.html', form=form, prompt_templates=templates)

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

@routes_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@routes_bp.route('/add-site', methods=['GET', 'POST'], endpoint='add_site')
@login_required
def add_site():
    form = AddSiteForm()
    if form.validate_on_submit():
        site_url = form.site_url.data.strip()
        wp_username = form.wp_username.data.strip()
        wp_app_password = form.wp_app_password.data.strip()
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
    return render_template('add_site.html', form=form)

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
