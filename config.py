# config.py

import os
from dotenv import load_dotenv

load_dotenv()

def clean_database_url(raw_url):
    if raw_url.startswith("DATABASE_URL="):
        return raw_url.replace("DATABASE_URL=", "")
    return raw_url

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key")
    SQLALCHEMY_DATABASE_URI = clean_database_url(os.environ.get("DATABASE_URL", "sqlite:///default.db"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
