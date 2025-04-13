import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-default-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    PIXABAY_API_KEY = os.environ.get('PIXABAY_API_KEY')
