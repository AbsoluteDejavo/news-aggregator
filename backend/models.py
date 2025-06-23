from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    url = db.Column(db.String(512), unique=True, nullable=False)
    source = db.Column(db.String(128))
    author = db.Column(db.String(128))
    category = db.Column(db.String(64))
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    image_url = db.Column(db.String(512))
    is_bookmarked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'source': self.source,
            'author': self.author,
            'category': self.category,
            'published_at': self.published_at.isoformat(),
            'description': self.description,
            'content': self.content,
            'image_url': self.image_url,
            'is_bookmarked': self.is_bookmarked,
            'created_at': self.created_at.isoformat()
        }
