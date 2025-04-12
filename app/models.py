from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

# データベースの初期化
db = SQLAlchemy()

# ユーザーモデル
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    is_active_flag = db.Column(db.Boolean, default=True)

    # リレーション
    sites = db.relationship('Site', backref='user', lazy=True)
    scheduled_posts = db.relationship('ScheduledPost', backref='user', lazy=True)
    prompt_templates = db.relationship('PromptTemplate', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

    @property
    def is_active(self):
        return self.is_active_flag

    def get_id(self):
        return str(self.id)

# サイトモデル
class Site(db.Model):
    __tablename__ = 'sites'

    id = db.Column(db.Integer, primary_key=True)
    site_url = db.Column(db.String(255), nullable=False)
    wp_username = db.Column(db.String(120), nullable=False)
    wp_app_password = db.Column(db.String(255), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    articles = db.relationship('Article', backref='site', lazy=True)
    scheduled_posts = db.relationship('ScheduledPost', backref='site', lazy=True)

    def __repr__(self):
        return f'<Site {self.site_url}>'

# 記事モデル
class Article(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='未投稿')
    scheduled_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    images = db.Column(db.JSON, nullable=True)

    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)

    def __repr__(self):
        return f'<Article {self.title}>'

# 自動投稿スケジュールモデル
class ScheduledPost(db.Model):
    __tablename__ = 'scheduled_posts'

    id = db.Column(db.Integer, primary_key=True)
    genre = db.Column(db.String(100), nullable=True)
    keyword = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    featured_image = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default="未投稿")
    scheduled_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    site_url = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255), nullable=False)
    app_password = db.Column(db.String(255), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)

    def __repr__(self):
        return f"<ScheduledPost {self.title} @ {self.scheduled_time}>"

# 🔹 プロンプトテンプレートモデル（ジャンルごとに保存）
class PromptTemplate(db.Model):
    __tablename__ = 'prompt_templates'

    id = db.Column(db.Integer, primary_key=True)
    genre = db.Column(db.String(100), nullable=False)
    title_prompt = db.Column(db.Text, nullable=False)
    body_prompt = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f"<PromptTemplate {self.genre}>"
