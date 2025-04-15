# app/auth.py

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from .models import db, User
from .forms import LoginForm, SignupForm  # ✅ SignupForm をインポート

auth_bp = Blueprint('auth', __name__)

# ログイン
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('ログイン成功しました！')
            return redirect(url_for('routes.dashboard'))
        else:
            flash('メールアドレスまたはパスワードが間違っています。')
    return render_template('login.html', form=form)

# ログアウト
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ログアウトしました。')
    return redirect(url_for('auth.login'))

# 新規登録
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password.data

        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            flash('既に登録済みのメールアドレスまたはユーザー名です。')
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(password)
        new_user = User(email=email, username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('ユーザー登録が完了しました。ログインしてください。')
        return redirect(url_for('auth.login'))

    return render_template('register.html', form=form)
