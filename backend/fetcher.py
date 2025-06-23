from newsapi import NewsApiClient
from models import db, Article
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Categories we want to fetch
CATEGORIES = ['business', 'technology', 'science', 'health', 'entertainment', 'sports', 'general']

def fetch_and_store_articles(api_key):
    """Fetch articles from NewsAPI and store them in the database"""
    if not api_key:
        logging.error("No API key provided")
        raise ValueError("NewsAPI key is required")

    logging.info(f"Starting article fetch with API key: {api_key[:4]}...")
    articles_added = 0
    
    try:
        newsapi = NewsApiClient(api_key=api_key)
        
        # Get articles for each category
        for category in CATEGORIES:
            logging.info(f"Fetching articles for category: {category}")
            try:
                # Get top headlines for the category
                articles = newsapi.get_top_headlines(
                    country='us',
                    category=category,
                    language='en',
                    page_size=100
                )
                
                if articles.get('status') != 'ok':
                    logging.error(f"NewsAPI error for {category}: {articles.get('message', 'Unknown error')}")
                    continue
                
                # Store articles
                for item in articles.get('articles', []):
                    if not item['url'] or not item['title']:
                        continue
                    
                    try:
                        # Create a new session for each article check/insert
                        existing_article = db.session.query(Article).filter_by(url=item['url']).first()
                        if existing_article:
                            db.session.remove()  # Clean up the session
                            continue
                        
                        try:
                            published_at = datetime.strptime(
                                item['publishedAt'],
                                '%Y-%m-%dT%H:%M:%SZ'
                            ) if item['publishedAt'] else datetime.utcnow()
                        except ValueError:
                            published_at = datetime.utcnow()
                        
                        article = Article(
                            title=item['title'],
                            url=item['url'],
                            source=item['source']['name'] if item['source'] else None,
                            author=item['author'],
                            category=category,
                            published_at=published_at,
                            description=item['description'],
                            content=item['content'],
                            image_url=item['urlToImage']
                        )
                        db.session.add(article)
                        db.session.commit()
                        articles_added += 1
                        logging.info(f"Added article: {article.title[:50]}...")
                        
                    except Exception as e:
                        logging.error(f"Error adding article {item.get('title', '')[:50]}: {str(e)}")
                        db.session.rollback()
                    finally:
                        db.session.remove()  # Clean up the session
                
            except Exception as e:
                logging.error(f"Error processing category {category}: {str(e)}")
                continue
        
        # Clean up old articles in a new session
        try:
            week_ago = datetime.utcnow() - timedelta(days=7)
            old_articles = db.session.query(Article).filter(
                Article.published_at < week_ago,
                Article.is_bookmarked == False
            ).all()
            
            for article in old_articles:
                db.session.delete(article)
            
            db.session.commit()
            logging.info(f"Cleaned up {len(old_articles)} old articles")
            
        except Exception as e:
            logging.error(f"Error cleaning up old articles: {str(e)}")
            db.session.rollback()
        finally:
            db.session.remove()  # Clean up the session
        
    except Exception as e:
        logging.error(f"Error in fetch_and_store_articles: {str(e)}")
        raise
    
    logging.info(f"Finished fetching articles. Total added: {articles_added}")
    return articles_added
