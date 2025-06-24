// State management
let currentFilters = {
    q: '',
    category: '',
    source: '',
    days: 7
};

let isBookmarksMode = false;
let loading = false;

// DOM Elements
const elements = {
    search: document.getElementById('search'),
    categoryFilter: document.getElementById('categoryFilter'),
    sourceFilter: document.getElementById('sourceFilter'),
    timeFilter: document.getElementById('timeFilter'),
    articles: document.getElementById('articles'),
    darkModeToggle: document.getElementById('darkModeToggle'),
    bookmarksButton: document.getElementById('bookmarksButton'),
    loadingIndicator: document.getElementById('loading'),
    errorMessage: document.getElementById('error-message'),
    refreshButton: document.getElementById('refreshButton')
};

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = (now - date) / 1000; // difference in seconds

    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    
    return date.toLocaleDateString();
}

function toggleLoading(show) {
    loading = show;
    if (elements.loadingIndicator) {
        elements.loadingIndicator.style.display = show ? 'flex' : 'none';
        elements.loadingIndicator.classList.toggle('hidden', !show);
    }
}

function toggleError(show, message = 'Failed to load articles. Please try again.') {
    if (elements.errorMessage) {
        elements.errorMessage.classList.toggle('hidden', !show);
        if (show) {
            const messageElement = elements.errorMessage.querySelector('p');
            if (messageElement) {
                messageElement.textContent = message;
            }
            setTimeout(() => toggleError(false), 5000); // Hide error after 5 seconds
        }
    }
}

// API calls
async function fetchArticles() {
    if (loading) {
        console.log('Already loading articles, skipping fetch');
        return;
    }
    
    try {
        toggleLoading(true);
        toggleError(false);
        console.log('Fetching articles...');
        
        const queryParams = new URLSearchParams({
            q: elements.search.value || '',
            category: elements.categoryFilter.value || '',
            source: elements.sourceFilter.value || '',
            days: elements.timeFilter.value || '7'
        });
        
        const endpoint = isBookmarksMode ? '/api/bookmarks' : `/api/articles?${queryParams}`;
        console.log('Endpoint:', endpoint);
        
        // Add more debugging info
        console.log('Current filters:', {
            search: elements.search.value,
            category: elements.categoryFilter.value,
            source: elements.sourceFilter.value,
            days: elements.timeFilter.value
        });        console.log('Making fetch request to:', endpoint);
        const res = await fetch(endpoint);
        console.log('Response status:', res.status);
        
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        
        const articles = await res.json();
        console.log(`Fetched ${articles.length} articles`);
        
        if (!Array.isArray(articles)) {
            console.error('Invalid response format:', articles);
            throw new Error('Invalid response format from server');
        }
        
        renderArticles(articles);
    } catch (error) {
        console.error('Error fetching articles:', error);
        toggleError(true);
        elements.articles.innerHTML = `
            <div class="no-results">
                <i class="fas fa-exclamation-circle"></i>
                <p>Failed to load articles</p>
                <small>Please try refreshing the page or try again later</small>
            </div>
        `;
    } finally {
        toggleLoading(false);
    }
}

async function toggleBookmark(articleId, isBookmarked) {
    try {
        const method = isBookmarked ? 'DELETE' : 'POST';
        await fetch('/api/bookmarks', {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ article_id: articleId })
        });
        
        // Refresh the articles
        fetchArticles();
    } catch (error) {
        console.error('Error toggling bookmark:', error);
    }
}

async function fetchFilters() {
    try {
        // Fetch categories
        const categoriesRes = await fetch('/api/categories');
        const categories = await categoriesRes.json();
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category.charAt(0).toUpperCase() + category.slice(1);
            elements.categoryFilter.appendChild(option);
        });

        // Fetch sources
        const sourcesRes = await fetch('/api/sources');
        const sources = await sourcesRes.json();
        sources.forEach(source => {
            const option = document.createElement('option');
            option.value = source;
            option.textContent = source;
            elements.sourceFilter.appendChild(option);
        });
    } catch (error) {
        console.error('Error fetching filters:', error);
    }
}

// Rendering
function renderArticles(articles) {
    console.log('Rendering articles:', articles);
    elements.articles.innerHTML = '';
    
    if (!articles || articles.length === 0) {
        console.log('No articles to render');
        elements.articles.innerHTML = `
            <div class="no-results">
                <i class="fas fa-search"></i>
                <p>No articles found</p>
                <small>Try adjusting your search or filters</small>
            </div>
        `;
        return;
    }
    console.log(`Rendering ${articles.length} articles`);

    articles.forEach(article => {
        const div = document.createElement('div');
        div.className = 'article';
        div.innerHTML = `
            ${article.image_url ? `
                <div class="article-image">
                    <img src="${article.image_url}" alt="${article.title}" 
                         onerror="this.parentElement.style.display='none'">
                </div>
            ` : ''}
            <div class="article-content">
                <h2>
                    <a href="${article.url}" target="_blank" rel="noopener noreferrer">
                        ${article.title}
                    </a>
                </h2>
                ${article.description ? `<p class="description">${article.description}</p>` : ''}
                <div class="article-meta">
                    <div class="meta-info">
                        <span class="source">${article.source || 'Unknown Source'}</span>
                        <span class="date">${formatDate(article.published_at)}</span>
                    </div>
                    <button class="bookmark-btn" onclick="toggleBookmark(${article.id}, ${article.is_bookmarked})">
                        <i class="fas fa-bookmark${article.is_bookmarked ? '' : '-o'}"></i>
                    </button>
                </div>
            </div>
        `;
        elements.articles.appendChild(div);
    });
}

// Event listeners
function setupEventListeners() {
    // Search input with debounce
    let searchTimeout;
    elements.search.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(fetchArticles, 300);
    });

    // Filters
    elements.categoryFilter.addEventListener('change', (e) => {
        currentFilters.category = e.target.value;
        fetchArticles();
    });

    elements.sourceFilter.addEventListener('change', (e) => {
        currentFilters.source = e.target.value;
        fetchArticles();
    });

    elements.timeFilter.addEventListener('change', (e) => {
        currentFilters.days = e.target.value;
        fetchArticles();
    });

    // Dark mode toggle
    elements.darkModeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('darkMode', isDark);
        elements.darkModeToggle.innerHTML = `<i class="fas fa-${isDark ? 'sun' : 'moon'}"></i>`;
    });

    // Bookmarks toggle
    elements.bookmarksButton.addEventListener('click', () => {
        isBookmarksMode = !isBookmarksMode;
        elements.bookmarksButton.classList.toggle('active', isBookmarksMode);
        fetchArticles();
    });

    // Refresh button handler
    elements.refreshButton.addEventListener('click', () => {
        elements.search.value = '';
        elements.categoryFilter.value = '';
        elements.sourceFilter.value = '';
        elements.timeFilter.value = '7';
        fetchArticles();
    });
}

// Initialization
async function initialize() {
    // Set up event listeners
    setupEventListeners();
    
    // Load dark mode preference
    const darkMode = localStorage.getItem('darkMode') === 'true';
    if (darkMode) {
        document.body.classList.add('dark-mode');
        elements.darkModeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    }
    
    // Fetch initial data
    await fetchFilters();
    await fetchArticles();
}

// Start the app
initialize();
