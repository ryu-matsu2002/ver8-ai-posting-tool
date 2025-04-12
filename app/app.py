import openai
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Site, Article  # Site と Article をインポート
from flask_migrate import Migrate
from article_generation import generate_article  # 記事生成を別ファイルに分ける
from image_search import search_images  # 画像検索のための関数をインポート
from dotenv import load_dotenv
import os
from flask_login import logout_user

# Blueprintのインポート
from routes import routes_bp
from auto_post import auto_post_bp

# .envファイルを読み込む
load_dotenv()

# OpenAI APIキーを設定
openai.api_key = os.getenv("OPENAI_API_KEY")

# Pixabay APIキーの設定
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

# Flaskアプリの作成
app = Flask(__name__)

# アプリケーションの設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # SQLiteデータベース
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # セッション用の秘密鍵

# データベースの初期化
db.init_app(app)

# マイグレーションの設定
migrate = Migrate(app, db)

# ログインマネージャーの設定
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ログインユーザーのロード設定
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Blueprint登録
app.register_blueprint(routes_bp)
app.register_blueprint(auto_post_bp)

# ユーザー登録処理
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# ログイン処理
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ログアウトしました。')
    return redirect(url_for('login'))

# ダッシュボードページ
@app.route('/dashboard')
@login_required
def dashboard():
    user_sites = Site.query.filter_by(user_id=current_user.id).all()
    user_articles = Article.query.filter_by(site_id=current_user.id).all()
    return render_template('dashboard.html', username=current_user.username, sites=user_sites, articles=user_articles)

# サイト登録ページ
@app.route('/add_site', methods=['GET', 'POST'])
@login_required
def add_site():
    if request.method == 'POST':
        site_url = request.form['site_url']
        wp_username = request.form['wp_username']
        wp_app_password = request.form['wp_app_password']
        new_site = Site(site_url=site_url, wp_username=wp_username, wp_app_password=wp_app_password, user_id=current_user.id)
        db.session.add(new_site)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_site.html')

# 記事生成処理
@app.route('/generate_article', methods=['POST'])
@login_required
def generate_article_for_user():
    article_title = request.form['title']
    article_body = request.form['body']
    site_id = request.form['site_id']
    generated_article = generate_article(article_title, article_body)
    images = search_images(generated_article)
    new_article = Article(title=article_title,
                          content=generated_article,
                          status='生成中',
                          site_id=site_id,
                          images=images)
    db.session.add(new_article)
    db.session.commit()
    return redirect(url_for('dashboard'))

# アプリケーション実行
if __name__ == '__main__':
    app.run(debug=True)
