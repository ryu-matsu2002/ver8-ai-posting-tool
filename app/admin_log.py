# app/admin_log.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import ScheduledPost, Site
from app import db
from datetime import timezone, timedelta

admin_log_bp = Blueprint('admin_log', __name__)

# 投稿ログページ（指定サイトの投稿一覧を表示）
@admin_log_bp.route('/admin/log/<int:site_id>')
@login_required
def admin_log(site_id):
    site = Site.query.filter_by(id=site_id, user_id=current_user.id).first()
    if not site:
        return "サイトが見つかりません", 404

    posts = ScheduledPost.query.filter_by(site_id=site.id, user_id=current_user.id).order_by(ScheduledPost.scheduled_time.asc()).all()
    jst = timezone(timedelta(hours=9))  # 日本時間（JST）
    return render_template('admin_log.html', posts=posts, site_id=site_id, jst=jst)

# 投稿削除処理
@admin_log_bp.route('/admin/log/<int:site_id>/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(site_id, post_id):
    post = ScheduledPost.query.filter_by(id=post_id, site_id=site_id, user_id=current_user.id).first()
    if post:
        db.session.delete(post)
        db.session.commit()
        flash('投稿を削除しました。')
    return redirect(url_for('admin_log.admin_log', site_id=site_id))

# 投稿ステータス手動変更（例："投稿済み"に切り替え）
@admin_log_bp.route('/admin/log/<int:site_id>/status/<int:post_id>', methods=['POST'])
@login_required
def update_status(site_id, post_id):
    post = ScheduledPost.query.filter_by(id=post_id, site_id=site_id, user_id=current_user.id).first()
    if post:
        post.status = request.form.get('status', post.status)
        db.session.commit()
        flash('ステータスを更新しました。')
    return redirect(url_for('admin_log.admin_log', site_id=site_id))

# プレビュー表示
@admin_log_bp.route('/admin/log/<int:site_id>/preview/<int:post_id>')
@login_required
def preview_post(site_id, post_id):
    post = ScheduledPost.query.filter_by(id=post_id, site_id=site_id, user_id=current_user.id).first()
    if not post:
        return "記事が見つかりません", 404
    return render_template('preview.html', post=post)
