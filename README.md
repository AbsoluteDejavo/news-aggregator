# Content Aggregator

A simple news/content aggregator built with Flask (backend) and vanilla HTML/CSS/JS (frontend).

## Features
- Fetches news from NewsAPI
- Search bar
- Dark mode
- Responsive design

## Setup
1. Add your NewsAPI key in `backend/fetcher.py`.
2. Install backend dependencies:
   ```
   pip install -r backend/requirements.txt
   ```
3. Run the backend:
   ```
   python backend/app.py
   ```
4. Open `frontend/index.html` in your browser (or serve with Flask for API access).
