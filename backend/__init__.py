# This file makes the backend directory a Python package
from .models import db, Article
from .fetcher import fetch_and_store_articles, validate_api_key
