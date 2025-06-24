from flask import Flask, jsonify, request
from flask_cors import CORS
from models import db, Article
from fetcher import fetch_and_store_articles
from apscheduler.schedulers.background import BackgroundScheduler
import os
from datetime import datetime, timedelta

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Flask app with static files configuration
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(os.path.dirname(current_dir), 'frontend')
app = Flask(__name__)  # Remove static folder configuration as Vercel will handle static files
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///articles.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['NEWS_API_KEY'] = 'YOUR NEWS API KEY'  # Your API key

logging.info(f"Static folder path: {app.static_folder}")
logging.info(f"Static URL path: {app.static_url_path}")

# Create frontend directory if it doesn't exist
os.makedirs(frontend_dir, exist_ok=True)
db.init_app(app)

# Ensure the instance folder exists
os.makedirs('instance', exist_ok=True)

# Serve frontend
@app.route('/')
def serve_frontend():
    try:
        return app.send_static_file('index.html')
    except Exception as e:
        logging.error(f"Error serving frontend: {str(e)}")
        return f"""
        <html>
            <body>
                <h1>Error loading application</h1>
                <p>There was an error loading the application. Please check the following:</p>
                <ul>
                    <li>Make sure all files are in the correct location</li>
                    <li>Check that the static files are accessible</li>
                    <li>Verify that the server has proper permissions</li>
                </ul>
                <p>Error details: {str(e)}</p>
            </body>
        </html>
        """, 500

# Additional route to serve static files explicitly
@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        logging.info(f"Serving static file: {filename}")
        return app.send_static_file(filename)
    except Exception as e:
        logging.error(f"Error serving static file {filename}: {str(e)}")
        return jsonify({"error": f"File not found: {filename}"}), 404

# API Routes
@app.route('/api/articles')
def get_articles():
    try:
        # Log request details
        logging.info(f"Received request for articles with params: {dict(request.args)}")
        
        # Check if we have any articles
        article_count = Article.query.count()
        logging.info(f"Current article count in database: {article_count}")
        
        if article_count == 0:
            # Fetch articles if database is empty
            logging.info("No articles found in database, fetching new articles...")
            try:
                fetch_and_store_articles(app.config['NEWS_API_KEY'])
                article_count = Article.query.count()
                logging.info(f"Fetched articles, new count: {article_count}")
            except Exception as e:
                logging.error(f"Error fetching articles: {str(e)}")
                return jsonify({"error": "Failed to fetch articles from news API"}), 500
        
        query = Article.query.order_by(Article.published_at.desc())
        
        # Filtering
        keyword = request.args.get('q')
        category = request.args.get('category')
        source = request.args.get('source')
        days = request.args.get('days', type=int, default=7)
        
        # Log filter parameters
        logging.info(f"Applying filters - keyword: {keyword}, category: {category}, source: {source}, days: {days}")
        
        if keyword:
            query = query.filter(Article.title.ilike(f'%{keyword}%'))
        if category:
            query = query.filter(Article.category == category)
        if source:
            query = query.filter(Article.source == source)
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Article.published_at >= cutoff)

        articles = query.all()
        articles_dict = [a.to_dict() for a in articles]
        logging.info(f"Returning {len(articles_dict)} articles")
        
        # Log a sample article if any exist
        if articles_dict:
            logging.info(f"Sample article: {articles_dict[0]}")
            
        return jsonify(articles_dict)
        
    except Exception as e:
        logging.error(f"Error in get_articles: {str(e)}")
        logging.exception("Full traceback:")
        return jsonify({"error": "Failed to fetch articles"}), 500

@app.route('/api/categories')
def get_categories():
    categories = db.session.query(Article.category).distinct().all()
    return jsonify([c[0] for c in categories if c[0]])

@app.route('/api/sources')
def get_sources():
    sources = db.session.query(Article.source).distinct().all()
    return jsonify([s[0] for s in sources if s[0]])

@app.route('/api/bookmarks', methods=['GET', 'POST', 'DELETE'])
def handle_bookmarks():
    if request.method == 'GET':
        bookmarked = Article.query.filter_by(is_bookmarked=True).all()
        return jsonify([a.to_dict() for a in bookmarked])
    
    article_id = request.json.get('article_id')
    if not article_id:
        return jsonify({'error': 'article_id is required'}), 400
    
    article = Article.query.get(article_id)
    if not article:
        return jsonify({'error': 'Article not found'}), 404
    
    if request.method == 'POST':
        article.is_bookmarked = True
    elif request.method == 'DELETE':
        article.is_bookmarked = False
    
    db.session.commit()
    return jsonify(article.to_dict())

def fetch_articles_job():
    """Background job to fetch articles with application context"""
    app_context = app.app_context()
    app_context.push()  # Push the context
    
    try:
        fetch_and_store_articles(app.config['NEWS_API_KEY'])
    except Exception as e:
        logging.error(f"Error in scheduled fetch: {str(e)}")
    finally:
        app_context.pop()  # Pop the context when done

if __name__ == '__main__':
    try:
        # Initialize database
        with app.app_context():
            logging.info("Initializing database...")
            db.create_all()
            
            # Check if we need to fetch initial articles
            article_count = Article.query.count()
            logging.info(f"Found {article_count} articles in database")
            
            if article_count == 0:
                logging.info("Fetching initial articles...")
                fetch_and_store_articles(app.config['NEWS_API_KEY'])
                logging.info("Initial articles fetched successfully")
        
        # Schedule periodic fetches with error handling
        try:
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                fetch_articles_job,
                'interval',
                minutes=30,
                next_run_time=datetime.now(),
                max_instances=1,  # Prevent multiple instances running at once
                coalesce=True,    # Combine missed runs
                misfire_grace_time=900  # Allow job to still run if missed by up to 15 minutes
            )
            scheduler.start()
            logging.info("Scheduler started successfully")
        except Exception as e:
            logging.error(f"Failed to start scheduler: {str(e)}")
            # Continue running the app even if scheduler fails
        
        # Run the app
        logging.info("Starting Flask application...")
        app.run(debug=True, port=5000)
        
    except Exception as e:
        logging.error(f"Error during startup: {str(e)}")
        raise
