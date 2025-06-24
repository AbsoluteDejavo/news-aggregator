from newsapi import NewsApiClient
from models import db, Article
from datetime import datetime, timedelta
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)

# Categories we want to fetch
CATEGORIES = ['business', 'technology', 'science', 'health', 'entertainment', 'sports', 'general']

def validate_api_key(api_key):
    """Validate the API key before making any requests"""
    try:
        # Make a small test request to verify the API key
        url = f'https://newsapi.org/v2/top-headlines?country=us&pageSize=1&apiKey={api_key}'
        response = requests.get(url)
        if response.status_code == 401:
            logging.error("Invalid API key")
            return False
        elif response.status_code == 429:
            logging.error("API rate limit exceeded")
            return False
        elif response.status_code != 200:
            logging.error(f"API error: {response.status_code} - {response.text}")
            return False
        return True
    except Exception as e:
        logging.error(f"Error validating API key: {str(e)}")
        return False

def fetch_and_store_articles(api_key):
    """Fetch articles from NewsAPI and store them in the database"""
    if not api_key:
        logging.error("No API key provided")
        raise ValueError("NewsAPI key is required")

    logging.info("Validating API key...")
    if not validate_api_key(api_key):
        raise ValueError("Invalid or non-functioning API key")

    logging.info(f"Starting article fetch with API key: {api_key[:4]}...")
    articles_added = 0
    
    try:
        newsapi = NewsApiClient(api_key=api_key)
        
        # Get articles for each category
        for category in CATEGORIES:
            logging.info(f"Fetching articles for category: {category}")
            try:
                # Get top headlines for the category
                response = newsapi.get_top_headlines(
                    country='us',
                    category=category,
                    language='en',
                    page_size=100
                )
                
                if 'status' not in response or response['status'] != 'ok':
                    error_msg = response.get('message', 'Unknown error')
                    logging.error(f"Error fetching articles for category {category}: {error_msg}")
                    continue

                articles = response.get('articles', [])
                if not articles:
                    logging.warning(f"No articles found for category {category}")
                    continue

                logging.info(f"Received {len(articles)} articles for category {category}")

                category_added = 0
                for article in articles:
                    try:
                        # Skip articles with missing required fields
                        if not article.get('title') or not article.get('url'):
                            continue

                        # Check if article already exists
                        existing_article = Article.query.filter_by(url=article['url']).first()
                        if existing_article:
                            continue

                        # Create new article
                        new_article = Article(
                            title=article['title'],
                            url=article['url'],
                            source=article['source']['name'] if article.get('source') else None,
                            author=article.get('author'),
                            category=category,
                            published_at=datetime.strptime(article['publishedAt'], '%Y-%m-%dT%H:%M:%SZ') if article.get('publishedAt') else datetime.utcnow(),
                            description=article.get('description'),
                            content=article.get('content'),
                            image_url=article.get('urlToImage')
                        )
                        db.session.add(new_article)
                        articles_added += 1
                        category_added += 1
                        logging.debug(f"Added article: {new_article.title[:50]}...")
                    except Exception as e:
                        logging.error(f"Error processing article: {str(e)}")
                        continue

                # Commit after each category
                db.session.commit()
                logging.info(f"Added {category_added} articles for category {category}")

            except Exception as e:
                logging.error(f"Error fetching category {category}: {str(e)}")
                db.session.rollback()
                continue    
        # Clean up old articles
        try:
            week_ago = datetime.utcnow() - timedelta(days=7)
            old_articles = Article.query.filter(
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
        
    except Exception as e:
        logging.error(f"Error in fetch_and_store_articles: {str(e)}")
        raise
    finally:
        db.session.remove()  # Final cleanup of the session
    
    logging.info(f"Finished fetching articles. Total added: {articles_added}")
    return articles_added
