import requests
import json
from datetime import datetime, timedelta
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
import logging
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
import os
import tempfile
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re
import time
from newspaper import Article
import nltk
from readability import readability
import feedparser
import ssl
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import arabic_reshaper
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from jinja2 import Environment, FileSystemLoader
import boto3
from botocore.config import Config
from dotenv import load_dotenv
from custom_scrapers import fetch_all_custom_scrapers
from apify_scrapers import fetch_all_apify_scrapers
from bidi.algorithm import get_display
import arabic_reshaper
# Load environment variables from .env file
load_dotenv()

# Add MSYS2 GTK path for WeasyPrint on Windows
import sys
if sys.platform == 'win32':
    msys2_bin = r'C:\msys64\mingw64\bin'
    if os.path.isdir(msys2_bin) and msys2_bin not in os.environ.get('PATH', ''):
        os.environ['PATH'] = msys2_bin + os.pathsep + os.environ.get('PATH', '')

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except OSError:
    WEASYPRINT_AVAILABLE = False
    logging.warning("WeasyPrint (GTK) not found. PDF generation will be disabled.")
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logging.warning("WeasyPrint module not found.")

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    force=True
)
logger = logging.getLogger(__name__)

# Ensure custom_scrapers logs are visible
logging.getLogger('custom_scrapers').setLevel(logging.INFO)
cs_handler = logging.StreamHandler()
cs_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger('custom_scrapers').addHandler(cs_handler)

# Download required NLTK data (run once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Register Arabic font - register under ALL variant names so ReportLab
# never fails when looking for bold/italic variants internally
import os
try:
    font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Amiri-Regular.ttf')
    pdfmetrics.registerFont(TTFont('Amiri', font_path))
    pdfmetrics.registerFont(TTFont('Amiri-Bold', font_path))
    pdfmetrics.registerFont(TTFont('Amiri-Italic', font_path))
    pdfmetrics.registerFont(TTFont('Amiri-BoldItalic', font_path))
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily('Amiri', normal='Amiri', bold='Amiri-Bold', italic='Amiri-Italic', boldItalic='Amiri-BoldItalic')
    registerFontFamily('amiri', normal='Amiri', bold='Amiri-Bold', italic='Amiri-Italic', boldItalic='Amiri-BoldItalic')
except Exception as e:
    logger.error(f"Failed to register Arabic font: {e}")

# Usage limits configuration
USAGE_LIMITS = {
    'daily_news': 30,
    'weekly': 4,
    'monthly': 2,
    'magazine': 2
}

# Admin user IDs (add your Telegram user ID here)
ADMIN_USER_IDS = [1029062753,1245179633]  # Add admin IDs like [123456789, 987654321]

# Usage tracking file
USAGE_FILE = 'user_usage.json'

def load_usage_data():
    """Load usage data from JSON file."""
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading usage data: {e}")
            return {}
    return {}

def save_usage_data(usage_data):
    """Save usage data to JSON file."""
    try:
        with open(USAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(usage_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving usage data: {e}")

def get_user_id(update):
    """Get user ID from update."""
    if update.callback_query:
        return update.callback_query.from_user.id
    return update.message.from_user.id

def check_usage_limit(user_id, feature):
    """Check if user has reached usage limit for a feature."""
    usage_data = load_usage_data()
    user_key = str(user_id)
    
    if user_key not in usage_data:
        return True, 0  # New user, has limit
    
    user_usage = usage_data[user_key]
    feature_key = feature
    
    if feature_key not in user_usage:
        return True, 0  # Feature not used yet
    
    current_usage = user_usage[feature_key]
    limit = USAGE_LIMITS.get(feature, 0)
    
    if current_usage >= limit:
        return False, current_usage  # Limit reached
    return True, current_usage  # Still has usage left

def increment_usage(user_id, feature):
    """Increment usage count for a user and feature."""
    usage_data = load_usage_data()
    user_key = str(user_id)
    
    if user_key not in usage_data:
        usage_data[user_key] = {}
    
    if feature not in usage_data[user_key]:
        usage_data[user_key][feature] = 0
    
    usage_data[user_key][feature] += 1
    save_usage_data(usage_data)

def reset_user_usage(user_id=None):
    """Reset usage for a specific user or all users."""
    if user_id:
        usage_data = load_usage_data()
        user_key = str(user_id)
        if user_key in usage_data:
            usage_data[user_key] = {}
            save_usage_data(usage_data)
            return True
        return False
    else:
        # Reset all users
        save_usage_data({})
        return True

def get_usage_status(user_id):
    """Get current usage status for a user."""
    usage_data = load_usage_data()
    user_key = str(user_id)
    
    if user_key not in usage_data:
        return {
            'daily_news': {'used': 0, 'limit': USAGE_LIMITS['daily_news']},
            'weekly': {'used': 0, 'limit': USAGE_LIMITS['weekly']},
            'monthly': {'used': 0, 'limit': USAGE_LIMITS['monthly']},
            'magazine': {'used': 0, 'limit': USAGE_LIMITS['magazine']}
        }
    
    user_usage = usage_data[user_key]
    return {
        'daily_news': {'used': user_usage.get('daily_news', 0), 'limit': USAGE_LIMITS['daily_news']},
        'weekly': {'used': user_usage.get('weekly', 0), 'limit': USAGE_LIMITS['weekly']},
        'monthly': {'used': user_usage.get('monthly', 0), 'limit': USAGE_LIMITS['monthly']},
        'magazine': {'used': user_usage.get('magazine', 0), 'limit': USAGE_LIMITS['magazine']}
    }

# Your Telegram Bot Token (you'll need to get this from @BotFather)
# Get from environment variable or use fallback (for development only)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7993110490:AAHQ79cswsZTIiwYmBM0XuWer8JPsMDIGqI")
# API Keys - Get from environment variables for production security
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "e45f816affb84b18ace6a929b6dffa56")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "6428994f84e7d7b2faedd07b8b99be28")

# Azure AI Configuration
AZURE_API_URL = os.getenv("AZURE_API_URL", "https://transformellica-gpt5-1.services.ai.azure.com/anthropic/v1/messages")
AZURE_API_KEY = os.getenv("AZURE_API_KEY", "")
AZURE_MODEL = os.getenv("AZURE_MODEL", "opus4.5")

# Initialize Azure AI client
if not AZURE_API_KEY or AZURE_API_KEY == "your_azure_api_key_here":
    logger.warning("⚠️ AZURE_API_KEY environment variable is not set!")
    logger.warning("   Azure AI will be unavailable. AWS Bedrock will be used as fallback.")
    AZURE_API_KEY = None
else:
    logger.info(f"✅ Azure AI client initialized successfully")
    logger.info(f"   API URL: {AZURE_API_URL}")
    logger.info(f"   Model: {AZURE_MODEL}")

# --- Corporate Strategy & L&D Keyword Configuration ---

# Category 1: Corporate Strategy & Leadership
STRATEGY_LEADERSHIP_KEYWORDS = [
    "corporate strategy", "business transformation", "digital transformation", "organizational change",
    "strategic planning", "strategic management", "strategic decision-making", "corporate governance",
    "business growth", "business model innovation", "market strategy", "competitive advantage",
    "change management", "organizational culture", "executive leadership", "leadership development",
    "leadership trends", "leadership coaching", "executive coaching", "management theory",
    "leadership best practices", "organizational excellence", "organizational leadership",
    "executive strategy", "market trends", "future of work", "industry outlooks",
    "human capital trends", "strategic business insights", "market analysis"
]

# Category 2: L&D & Talent Development
LD_TALENT_KEYWORDS = [
    "talent development", "employee training", "professional development", "learning technologies",
    "upskilling", "reskilling", "learning and development", "training programs", "skill development",
    "hr development", "capability building", "workforce development", "talent development standards",
    "capability model", "learning management systems", "lms", "blended learning", "microlearning",
    "gamification", "mobile learning", "social learning", "learning experience design",
    "instructional design", "ai in l&d", "personalized learning", "data-driven l&d",
    "virtual reality", "talent management", "career development", "employee engagement",
    "performance improvement", "learning analytics", "global l&d trends", "business of learning"
]

# Unified list for general filtering
ALL_PROFESSIONAL_KEYWORDS = STRATEGY_LEADERSHIP_KEYWORDS + LD_TALENT_KEYWORDS

# RSS feeds for Corporate Strategy, Leadership, and L&D content
# Multiple fallback URLs for reliability
RSS_FEEDS = [
    # {
    #     "name": "Harvard Business Review",
    #     "urls": [
    #         "https://hbr.org/feed",  # Primary
    #         "https://hbr.org/feed/rss/"  # Fallback 1
    #         "https://feeds.hbr.org/harvardbusiness",  # Fallback 2 (original)
    #         "https://hbr.org/webinars/feed"  # Fallback 3
    #     ]
    # },
    # {
    #     "name": "Forbes Leadership",
    #     "urls": [
    #         "https://rss.app/rss-feed?keyword=McKinsey%20Insights&region=US&lang=en"
    #     ]
    # },
    # {
    #     "name": "dd,
    #     "urls": [
    #         "https://www.td.org/rss",  # Primary
    #         "https://www.td.org/rss.xml",  # Fallback 1
    #         "https://www.td.org/feed"  # Fallback 2
    #     ]
    # },
    {
        "name": "Training Industry",
        "urls": [
            "https://trainingindustry.com/feed/"  # Primary
        ]
    },
    {
        "name": "Josh Bersin",
        "urls": [
            "https://joshbersin.com/feed/"  # Primary
        ]
    }
]

KEYWORD_INPUT_INSTRUCTIONS = (
    "✍️ *إعداد الكلمات المفتاحية (بالإنجليزية)*\n"
    "أرسل الكلمات المفتاحية بالصيغة التالية (بالإنجليزية):\n"
    "`Primary Keyword | secondary keyword 1, secondary keyword 2, secondary keyword 3`\n\n"
    "مثال:\n"
    "`Corporate Strategy Excellence 2025 | corporate strategy, leadership development, talent development`\n\n"
    "أرسل كلمة *cancel* لإلغاء إدخال الكلمات المفتاحية."
)


def parse_keyword_input(raw_text):
    if not raw_text:
        return None
    parts = raw_text.split('|', 1)
    primary = parts[0].strip()
    if not primary:
        return None
    secondary = []
    if len(parts) > 1:
        secondary = [kw.strip() for kw in parts[1].split(',') if kw.strip()]
    return {"primary": primary, "secondary": secondary}


def format_secondary_keywords(secondary_list):
    if not secondary_list:
        return "لم يتم تحديد كلمات ثانوية"
    return ", ".join(secondary_list)


def build_keyword_instruction_block(keywords):
    if keywords and keywords.get("primary"):
        primary = keywords["primary"]
        secondary_text = format_secondary_keywords(keywords.get("secondary", []))
        keyword_header = (
            f'PRIMARY KEYWORD: "{primary}"\n'
            f"SECONDARY KEYWORDS / LSI: {secondary_text}\n"
        )
    else:
        keyword_header = (
            "PRIMARY KEYWORD: Not specified (infer the best fit from the quality and excellence coverage)\n"
            "SECONDARY KEYWORDS / LSI: Use related quality, excellence, and QA terms, synonyms, and supporting subtopics\n"
        )

    return f"""
{keyword_header}
SEO requirements:
- Place the primary keyword in:
  • The SEO Title
  • The H1
  • The first paragraph (within the first 100 words)
  • Naturally 2–3 times every ~300 words throughout the body
- Distribute secondary/LSI keywords across select H2/H3 headings and different paragraphs as thematic synonyms.
- Do NOT repeat the exact same keyword in every heading—use natural variations to avoid keyword stuffing.

Mandatory SEO outputs at the top of the response (before any other sections):
1. SEO Title: < 60 characters, includes the primary keyword and communicates a clear benefit.
2. Meta Description: 120–150 characters summarizing the main value, optionally includes the primary keyword once (only if it reads naturally) plus a light CTA.
3. Recommended Slug: lowercase, hyphen-separated version of the primary keyword (e.g., quality-management-excellence-2025).
4. Headings Structure: Proposed H2/H3 outline derived from the primary + secondary keywords using varied phrasing.

After listing these SEO elements, continue with the requested quality and excellence blog structure while following the keyword guidance above.
""".strip()


def keywords_summary_text(keywords):
    if not keywords or not keywords.get("primary"):
        return "لم يتم إعداد أي كلمات مفتاحية بعد."
    secondary = format_secondary_keywords(keywords.get("secondary", []))
    return f"الكلمة الأساسية: {keywords['primary']}\nالكلمات الثانوية: {secondary}"


def get_user_keywords(context):
    try:
        return context.user_data.get("blog_keywords")
    except Exception:
        return None

def is_relevant_insight(article):
    """Filter to ensure articles are genuinely about Corporate Strategy, Leadership, and L&D"""
    text = (
        (article.get("title") or "") + " " +
        (article.get("description") or "") + " " +
        (article.get("content") or "")
    ).lower()

    banned_words = [
        "accident", "killed", "dead", "poisoning", "food poisoning",
        "crime", "arrest", "flood", "storm", "earthquake",
        "film", "tv episode", "episode", "review", "movie",
        "celebrity", "gossip", "football", "soccer", "nfl", "nba", 
        "premier league", "match", "game", "championship"
    ]

    if any(b in text for b in banned_words):
        return False

    return any(w in text for w in ALL_PROFESSIONAL_KEYWORDS)

def fetch_quality_news():
    """Fetch Corporate Strategy, Leadership, and L&D news from NewsAPI"""
    url = 'https://newsapi.org/v2/everything'
    params = {
        'q': '("leadership" OR "corporate strategy" OR "talent development" OR "learning and development" OR "future of work") AND NOT (football OR match OR game)',
        'sortBy': 'publishedAt',
        'language': 'en',
        'apiKey': NEWSAPI_KEY
    }

    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        articles = resp.json().get('articles', [])

        # strict filter
        clean = [a for a in articles if is_relevant_insight(a)]
        return clean
    
    except Exception as e:
        logger.error(f"Error fetching NewsAPI articles: {e}")
        return []

def fetch_gnews_quality():
    """Fetch Corporate Strategy, Leadership, and L&D news from GNews"""
    url = 'https://gnews.io/api/v4/search'
    params = {
        'q': '("leadership" OR "corporate strategy" OR "talent development" OR "learning and development" OR "future of work") AND NOT (football OR match OR game)',
        'lang': 'en',
        'country': 'us',
        'max': 20,
        'apikey': GNEWS_API_KEY
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        articles = response.json().get('articles', [])
        # Apply quality filter
        clean = [a for a in articles if is_relevant_insight(a)]
        return clean
    except Exception as e:
        logger.error(f"Error fetching GNews articles: {e}")
        return []

def fetch_weekly_quality_news():
    """Fetch Corporate Strategy, Leadership, and L&D news from the past week using NewsAPI"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    url = 'https://newsapi.org/v2/everything'
    params = {
        'q': '("leadership" OR "corporate strategy" OR "talent development" OR "learning and development" OR "future of work") AND NOT (football OR match OR game)',
        'sortBy': 'publishedAt',
        'language': 'en',
        'from': start_date.strftime('%Y-%m-%d'),
        'to': end_date.strftime('%Y-%m-%d'),
        'apiKey': NEWSAPI_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        articles = response.json().get('articles', [])
        clean = [a for a in articles if is_relevant_insight(a)]
        return clean
    except Exception as e:
        logger.error(f"Error fetching NewsAPI articles: {e}")
        return []

def fetch_monthly_quality_news():
    """Fetch Corporate Strategy, Leadership, and L&D news from the past month using NewsAPI"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    url = 'https://newsapi.org/v2/everything'
    params = {
        'q': '("leadership" OR "corporate strategy" OR "talent development" OR "learning and development" OR "future of work") AND NOT (football OR match OR game)',
        'sortBy': 'publishedAt',
        'language': 'en',
        'from': start_date.strftime('%Y-%m-%d'),
        'to': end_date.strftime('%Y-%m-%d'),
        'apiKey': NEWSAPI_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        articles = response.json().get('articles', [])
        clean = [a for a in articles if is_relevant_insight(a)]
        return clean
    except Exception as e:
        logger.error(f"Error fetching NewsAPI articles: {e}")
        return []

def create_robust_session():
    """Create a requests session with retry logic and SSL configuration."""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,  # Total number of retries
        backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
        status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
        allowed_methods=["HEAD", "GET", "OPTIONS"]  # Retryable methods
    )
    
    # Mount HTTPAdapter with retry strategy
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def get_feed_headers():
    """Get realistic headers to avoid 403 errors."""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

def fetch_rss_quality():
    """Fetch Quality and Excellence news from configured RSS feeds with robust error handling and multiple fallback URLs."""
    articles = []
    
    # Suppress SSL warnings (for development)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Create robust session
    session = create_robust_session()
    
    # Process feeds with rate limiting
    for i, feed in enumerate(RSS_FEEDS):
        try:
            feed_name = feed['name']
            feed_urls = feed.get('urls', [])
            
            if not feed_urls:
                logger.warning(f"⚠️ No URLs configured for {feed_name}")
                continue
            
            logger.info(f"Fetching RSS feed {i+1}/{len(RSS_FEEDS)}: {feed_name}")
            logger.info(f"   Available URLs: {len(feed_urls)}")
            
            # Rate limiting: wait between feeds
            if i > 0:
                time.sleep(2)  # Increased delay between feeds to avoid rate limiting
            
            parsed = None
            successful_url = None
            
            # Try each URL in the fallback list
            for url_idx, feed_url in enumerate(feed_urls, 1):
                try:
                    logger.info(f"   🔄 Trying URL {url_idx}/{len(feed_urls)}: {feed_url}")
                    
                    # Method 1: Try with requests session (best for 403 handling)
                    try:
                        headers = get_feed_headers()
                        response = session.get(
                            feed_url,
                            headers=headers,
                            timeout=20,  # Increased timeout
                            verify=False  # Disable SSL verification for problematic feeds
                        )
                        
                        if response.status_code == 200:
                            logger.info(f"   ✅ Successfully fetched {feed_name} via requests session")
                            parsed = feedparser.parse(response.content)
                            successful_url = feed_url
                            break  # Success! Stop trying other URLs
                        elif response.status_code == 429:
                            logger.warning(f"   ⚠️ Rate limited (429) for {feed_name}, waiting 10 seconds...")
                            time.sleep(10)
                            # Retry once after rate limit wait
                            response = session.get(feed_url, headers=headers, timeout=20, verify=False)
                            if response.status_code == 200:
                                parsed = feedparser.parse(response.content)
                                successful_url = feed_url
                                break
                            else:
                                logger.warning(f"   ⚠️ Still rate limited for {feed_name}, trying next URL...")
                                continue
                        elif response.status_code == 404:
                            logger.warning(f"   ⚠️ URL not found (404), trying next URL...")
                            continue
                        elif response.status_code == 403:
                            logger.warning(f"   ⚠️ Forbidden (403), trying direct parse fallback...")
                            # Don't continue - fall through to Method 2 (direct feedparser)
                        else:
                            logger.warning(f"   ⚠️ Failed to fetch via requests: {response.status_code}")
                            # Fall through to direct parse
                    except requests.exceptions.SSLError as ssl_err:
                        logger.warning(f"   ⚠️ SSL error: {ssl_err}")
                        # Fall through to direct parse
                    except requests.exceptions.RequestException as req_err:
                        logger.warning(f"   ⚠️ Requests failed: {req_err}")
                        # Fall through to direct parse
                    except Exception as e:
                        logger.warning(f"   ⚠️ Unexpected error: {e}")
                        # Fall through to direct parse
                    
                    # Method 2: Fallback to direct feedparser.parse (handles SSL issues better)
                    if not parsed or not hasattr(parsed, 'entries'):
                        try:
                            logger.info(f"   🔄 Trying direct feedparser.parse for {feed_name}")
                            parsed = feedparser.parse(feed_url)
                            
                            if hasattr(parsed, 'entries') and parsed.entries:
                                logger.info(f"   ✅ Successfully fetched {feed_name} via direct parse")
                                successful_url = feed_url
                                break  # Success! Stop trying other URLs
                        except Exception as direct_err:
                            logger.warning(f"   ❌ Direct parse failed: {direct_err}")
                            continue
                    
                except Exception as url_err:
                    logger.warning(f"   ❌ Error with URL {url_idx}: {url_err}")
                    continue
            
            # Check if we successfully parsed any URL
            if not parsed or not hasattr(parsed, 'entries'):
                logger.warning(f"⚠️ All {len(feed_urls)} URLs failed for {feed_name}")
                continue
            
            # Parse entries
            entries = parsed.entries if hasattr(parsed, 'entries') else []
            
            if not entries:
                logger.warning(f"⚠️ No entries found in {feed_name}")
                continue
            
            logger.info(f"📰 Found {len(entries)} articles in {feed_name}")
            
            for entry in entries:
                try:
                    title = getattr(entry, 'title', '') or ''
                    summary = getattr(entry, 'summary', '') or getattr(entry, 'description', '') or ''
                    link = getattr(entry, 'link', '') or ''
                    published = getattr(entry, 'published', '') or getattr(entry, 'updated', '') or ''
                    
                    # Normalize date to ISO if possible
                    published_parsed = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
                    if published_parsed:
                        try:
                            published_dt = datetime(*published_parsed[:6])
                            published_iso = published_dt.isoformat()
                        except Exception:
                            published_iso = published
                    else:
                        published_iso = published
                    
                    article = {
                        'title': title,
                        'description': summary,
                        'url': link,
                        'publishedAt': published_iso,
                        'source': {'name': feed_name}
                    }
                    articles.append(article)
                except Exception as inner_e:
                    logger.warning(f"⚠️ Error parsing RSS entry from {feed_name}: {inner_e}")
                    continue
            
            logger.info(f"✅ Successfully processed {feed_name}: {len([a for a in articles if a['source']['name'] == feed_name])} articles added")
            
        except Exception as e:
            logger.error(f"❌ Error fetching RSS feed {feed.get('name', 'Unknown')}: {e}")
            continue
    
    # Log summary
    logger.info(f"📊 RSS fetching complete: Total {len(articles)} articles from {len(RSS_FEEDS)} feeds")
    
    # Apply quality filter to RSS articles
    clean = [a for a in articles if is_relevant_insight(a)]
    logger.info(f"✨ After filtering: {len(clean)} relevant articles")
    
    return clean

def filter_relevant_articles(articles, extra_keywords=None):
    """Filter articles to keep only Corporate Strategy, Leadership, and L&D relevant content"""
    if not articles:
        logger.warning("No articles provided to filter_relevant_articles")
        return []

    # Use the new professional keyword lists
    professional_keywords = ALL_PROFESSIONAL_KEYWORDS.copy()

    # Add user-supplied extra keywords if any
    if extra_keywords:
        professional_keywords.extend([k.lower() for k in extra_keywords])

    # Compile regex pattern for efficiency
    pattern = re.compile(r"|".join([re.escape(k) for k in professional_keywords]), flags=re.IGNORECASE)

    filtered_articles = []
    for article in articles:
        if not article:
            continue

        # Gather searchable text fields
        text_parts = [
            article.get("title", "") or "",
            article.get("description", "") or "",
            article.get("content", "") or ""
        ]
        combined_text = " ".join(text_parts).lower()

        # Match with regex and apply strict filter
        if pattern.search(combined_text) and is_relevant_insight(article):
            filtered_articles.append(article)

    return filtered_articles

def filter_recent_articles(articles, days=7):
    """Filter articles to only include those from the past specified days"""
    if not articles:
        return []
    
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_articles = []
    
    for article in articles:
        if not article:
            continue
        published_at = article.get('publishedAt') or article.get('published_at')
        if published_at:
            try:
                # Handle different date formats
                if 'T' in published_at:
                    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                else:
                    pub_date = datetime.strptime(published_at, '%Y-%m-%d')
                
                if pub_date.replace(tzinfo=None) >= cutoff_date:
                    recent_articles.append(article)
            except Exception as e:
                # If date parsing fails, include the article anyway
                recent_articles.append(article)
        else:
            # If no date available, include the article
            recent_articles.append(article)
    
    return recent_articles

def categorize_articles(articles):
    """Categorize articles by Corporate Strategy & Leadership vs L&D based on keyword frequency"""
    if not articles:
        logger.warning("No articles provided to categorize_articles")
        return {
            'Corporate Strategy & Leadership': [],
            'L&D & Talent Development': []
        }
    
    categories = {
        'Corporate Strategy & Leadership': [],
        'L&D & Talent Development': []
    }
    
    for article in articles:
        if not article:
            continue
        
        title = article.get('title', '') or ''
        description = article.get('description', '') or ''
        full_content = article.get('full_content', '') or ''
        
        # Combine all text for analysis
        combined_text = f"{title.lower()} {description.lower()} {full_content.lower()}"
        
        # Count keyword frequency for each category
        strategy_count = sum(1 for keyword in STRATEGY_LEADERSHIP_KEYWORDS if keyword in combined_text)
        ld_count = sum(1 for keyword in LD_TALENT_KEYWORDS if keyword in combined_text)
        
        # Categorize based on higher frequency
        if strategy_count >= ld_count:
            categories['Corporate Strategy & Leadership'].append(article)
        else:
            categories['L&D & Talent Development'].append(article)
    
    return categories

def extract_article_content(url, max_retries=3):
    """Extract full article content from URL using multiple methods"""
    if not url or url.strip() == '':
        return None
    
    content = None

    # Method 1: Try newspaper3k first (most reliable for news articles)
    try:
        article = Article(url)
        article.download()
        article.parse()
        
        if article.text and len(article.text.strip()) > 200:
            content = {
                'text': article.text.strip(),
                'title': article.title or '',
                'authors': article.authors or [],
                'publish_date': article.publish_date,
                'method': 'newspaper3k'
            }
            logger.info(f"Successfully extracted content using newspaper3k for {url}")
            return content
    except Exception as e:
        logger.warning(f"Newspaper3k failed for {url}: {str(e)}")
    
    # Method 2: Manual web scraping with BeautifulSoup
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'ads']):
                element.decompose()
            
            # Try multiple content selectors
            content_selectors = [
                'article',
                '[role="main"]',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content',
                'main',
                '.story-body',
                '.article-body',
                '.post-body'
            ]
            
            article_text = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        text = element.get_text(strip=True, separator=' ')
                        if len(text) > len(article_text):
                            article_text = text
                    break
            
            # Fallback: extract all paragraphs
            if not article_text or len(article_text) < 200:
                paragraphs = soup.find_all('p')
                article_text = ' '.join([p.get_text(strip=True) for p in paragraphs])
            
            # Clean up the text
            article_text = re.sub(r'\s+', ' ', article_text)
            article_text = article_text.strip()
            
            if article_text and len(article_text) > 200:
                content = {
                    'text': article_text,
                    'title': soup.find('title').get_text(strip=True) if soup.find('title') else '',
                    'method': 'beautifulsoup'
                }
                logger.info(f"Successfully extracted content using BeautifulSoup for {url}")
                return content
                
        except requests.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}) for {url}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            logger.error(f"Unexpected error extracting content from {url}: {str(e)}")
            break
    
    logger.error(f"Failed to extract content from {url} after all attempts")
    return None

def enhance_articles_with_content(articles, max_articles=15, weekly_mode=False, monthly_mode=False):
    """Enhance articles with full content extraction"""
    if not articles:
        logger.warning("No articles provided to enhance_articles_with_content")
        return []
    
    enhanced_articles = []
    
    # Hard caps — prevent runaway content extraction
    if weekly_mode:
        max_articles = min(max_articles, 50)
        delay = 0.2
    elif monthly_mode:
        max_articles = min(max_articles, 50)
        delay = 0.2
    else:
        max_articles = min(max_articles, 10)
        delay = 0.2
    
    logger.info(f"Starting content extraction for {min(len(articles), max_articles)} articles")
    
    for i, article in enumerate(articles[:max_articles]):
        try:
            url = article.get('url', '') if article else ''
            if not url:
                continue
            
            # Skip articles that already have full_content from custom scrapers
            if article.get('full_content') and len(article.get('full_content', '')) > 200:
                logger.info(f"Skipping content extraction {i+1}/{min(len(articles), max_articles)} (already has content): {url[:60]}...")
                enhanced_articles.append(article)
                continue
                
            logger.info(f"Extracting content {i+1}/{min(len(articles), max_articles)}: {url}")
            
            # Extract full content
            content_data = extract_article_content(url)
            
            # Enhance article with extracted content
            enhanced_article = article.copy()
            if content_data and content_data.get('text'):
                enhanced_article['full_content'] = content_data['text']
                enhanced_article['extraction_method'] = content_data['method']
                enhanced_article['content_length'] = len(content_data['text'])
                
                # Use extracted title if original is missing/short
                extracted_title = content_data.get('title', '')
                original_title = article.get('title', '')
                if extracted_title and original_title and len(extracted_title) > len(original_title):
                    enhanced_article['enhanced_title'] = extracted_title
            else:
                description = article.get('description', 'No content available')
                enhanced_article['full_content'] = description or 'No content available'
                enhanced_article['extraction_method'] = 'fallback'
                enhanced_article['content_length'] = len(description) if description else 0
            
            enhanced_articles.append(enhanced_article)
            
            # Respectful delay
            time.sleep(delay)
            
        except Exception as e:
            logger.error(f"Error processing article {i+1}: {str(e)}")
            # Add original article without enhancement
            enhanced_articles.append(article)
            continue
    
    logger.info(f"Content extraction completed. Enhanced {len([a for a in enhanced_articles if a.get('full_content')])} articles")
    return enhanced_articles

async def get_news(update: Update, context: ContextTypes.DEFAULT_TYPE, page=1, category=None):
    """Get today's enhanced Quality and Excellence news with presenter-style summary."""
    user_id = get_user_id(update)
    
    # Check usage limit
    has_limit, current_usage = check_usage_limit(user_id, 'daily_news')
    if not has_limit:
        limit_message = (
            f"❌ *تم الوصول إلى الحد الأقصى*\n\n"
            f"لقد استخدمت جميع المحاولات المتاحة للأخبار اليومية ({USAGE_LIMITS['daily_news']}/{USAGE_LIMITS['daily_news']}).\n\n"
        )
        if update.callback_query:
            await update.callback_query.answer("تم الوصول إلى الحد الأقصى", show_alert=True)
            await update.callback_query.message.reply_text(limit_message, parse_mode='Markdown')
        else:
            await update.message.reply_text(limit_message, parse_mode='Markdown')
        return
    
    # Increment usage
    increment_usage(user_id, 'daily_news')
    
    # Send initial message
    if update.callback_query:
        await update.callback_query.answer()
        message = await update.callback_query.message.reply_text(
            "🌟 جارٍ تجهيز موجز أخبار الاستراتيجية المؤسسية والقيادة والتعلم والتطوير...\n📖 يتم الآن جمع تغطية شاملة من مصادر HBR وMcKinsey وATD وForbes...\n⏳ يرجى الانتظار للحظات.",
            parse_mode='Markdown'
        )
    else:
        message = await update.message.reply_text(
            "🌟 جارٍ تجهيز موجز أخبار الاستراتيجية المؤسسية والقيادة والتعلم والتطوير...\n📖 يتم الآن جمع تغطية شاملة من مصادر HBR وMcKinsey وATD وForbes...\n⏳ يرجى الانتظار للحظات.",
            parse_mode='Markdown'
        )
    
    try:
        # Update progress message
        await message.edit_text(
            "🌍 *الخطوة 1/3:* جلب الأخبار من عدة مصادر...",
            parse_mode='Markdown'
        )
        
        #  Fetch news from APIs, RSS feeds, and custom scrapers
        newsapi_articles = fetch_quality_news() or []
        gnews_articles = fetch_gnews_quality() or []
        rss_articles = fetch_rss_quality() or []
        try:
            custom_articles = await fetch_all_custom_scrapers(max_articles_per_source=50)
        except Exception as e:
            logger.warning(f"Custom scrapers failed: {e}")
            custom_articles = []

        logger.info(f"Fetched {len(newsapi_articles)} NewsAPI, {len(gnews_articles)} GNews, {len(rss_articles)} RSS and {len(custom_articles)} custom scraper articles.")
        # Filter relevant articles
        filtered_newsapi = filter_relevant_articles(newsapi_articles) or []
        filtered_gnews = filter_relevant_articles(gnews_articles) or []
        filtered_rss = filter_relevant_articles(rss_articles) or []
        filtered_custom = filter_relevant_articles(custom_articles) or []

        # Recency filter with fallback
        recent_newsapi = filter_recent_articles(filtered_newsapi, days=60) or []
        recent_gnews = filter_recent_articles(filtered_gnews, days=60) or []
        recent_rss = filter_recent_articles(filtered_rss, days=60) or []
        recent_custom = filter_recent_articles(filtered_custom, days=60) or []

        # Fallback: if nothing within 60 days, use the most relevant filtered articles
        if not (recent_newsapi or recent_gnews or recent_rss or recent_custom):
            logger.warning("No articles within 60 days — falling back to filtered articles regardless of date")
            recent_newsapi = filtered_newsapi[:20]
            recent_gnews = filtered_gnews[:20]
            recent_rss = filtered_rss[:20]
            recent_custom = filtered_custom[:20]
        
        await message.edit_text(
            "🌍 *الخطوة 2/3:* استخراج المحتوى الكامل للمقالات للتحليل...\n📖 قد يستغرق هذا من 30 إلى 60 ثانية...",
            parse_mode='Markdown'
        )
        
        # Enhance articles with full content (daily)
        enhanced_newsapi = enhance_articles_with_content(recent_newsapi, max_articles=50) or []
        enhanced_gnews = enhance_articles_with_content(recent_gnews, max_articles=50) or []
        enhanced_rss = enhance_articles_with_content(recent_rss, max_articles=50) or []
        enhanced_custom = enhance_articles_with_content(recent_custom, max_articles=50) or []
        all_enhanced_articles = enhanced_newsapi + enhanced_gnews + enhanced_rss + enhanced_custom
        
        with open("all_enhanced_quality_articles.txt", "w", encoding="utf-8") as f:
            json.dump(all_enhanced_articles, f, ensure_ascii=False, indent=2)
        
        await message.edit_text(
            "🌍 *الخطوة 3/3:* إنهاء إعداد موجز الأخبار...",
            parse_mode='Markdown'
        )
        
        # Format the message
        news_message, total_pages, current_category, relevant_articles = format_news_message(
            enhanced_newsapi, enhanced_gnews, enhanced_rss, page, category
        )
        
        # Update message header for presenter style
        if category:
            news_message = f"🌟 *موجز أخبار الاستراتيجية المؤسسية والقيادة والتعلم والتطوير - {category}*\n" + news_message[news_message.find('\n')+1:]
        else:
            news_message = f"🌟 *موجز أخبار الاستراتيجية المؤسسية والقيادة والتعلم والتطوير اليومي*\n" + news_message[news_message.find('\n')+1:]
        
        # Create keyboard based on context
        keyboard = []
        
        if category:
            # Category view with pagination
            if total_pages > 1:
                nav_row = []
                if page > 1:
                    nav_row.append(InlineKeyboardButton("⬅️ السابق", callback_data=f'category_{category}_{page-1}'))
                if page < total_pages:
                    nav_row.append(InlineKeyboardButton("التالي ➡️", callback_data=f'category_{category}_{page+1}'))
                if nav_row:
                    keyboard.append(nav_row)
            
            # Add PDF download button for category
            keyboard.append([InlineKeyboardButton("📄 تحميل تقرير الأخبار", callback_data=f'pdf_{category}')])
            keyboard.extend([
                [InlineKeyboardButton("🔄 تحديث جديد", callback_data=f'category_{category}_1')],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu')]
            ])
        else:
            # Main view
            keyboard = [
                [InlineKeyboardButton("📄 تحميل التقرير الكامل", callback_data='pdf_all')],
                [InlineKeyboardButton("🔄 تحديث جديد", callback_data='get_news')],
                [InlineKeyboardButton("📝 توليد تقارير أسبوعية", callback_data='generate_weekly')],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu')]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update the message with final results
        await message.edit_text(
            news_message,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
            
    except Exception as e:
        error_message = f"❌ حدث خطأ أثناء إعداد موجز أخبار الاستراتيجية والقيادة والتعلم والتطوير: {str(e)}"
        logger.error(f"News briefing error: {str(e)}")
        await message.edit_text(error_message)

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show category selection menu."""
    categories_message = """
🌟 *تصنيفات الاستراتيجية المؤسسية والقيادة والتعلم والتطوير*

اختر تصنيفًا لاستكشاف الأخبار مع استخراج المحتوى الكامل:

• 📊 **الاستراتيجية المؤسسية والقيادة** - استراتيجية الأعمال، التحول الرقمي، التخطيط الاستراتيجي، الحوكمة المؤسسية، مستقبل العمل
• 📚 **التعلم والتطوير وتنمية المواهب** - تطوير المواهب، التدريب المهني، التعلم المستمر، تقنيات التعلم، تنمية الكفاءات

*🆕 مزايا محسّنة لكل تصنيف:*
📖 استخراج المحتوى الكامل للمقالات
🧠 ملخصات ذكية مخصصة لكل تصنيف
📄 تقارير PDF مفصلة مع محتوى كامل
📊 إحصائيات حول نجاح استخراج المحتوى
🔍 فلترة ذكية اعتمادًا على النص الكامل

*جودة المحتوى:*
كل تصنيف يحلل المقالات الكاملة من HBR وMcKinsey وATD وForbes بدل العناوين فقط، مما يوفر رؤية أعمق وملخصات أدق.
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 الاستراتيجية المؤسسية والقيادة", callback_data='category_Corporate Strategy & Leadership_1')],
        [InlineKeyboardButton("📚 التعلم والتطوير وتنمية المواهب", callback_data='category_L&D & Talent Development_1')],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Always send a new message instead of editing
    if update.callback_query:
        await update.callback_query.message.reply_text(
            categories_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            categories_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

def format_news_message(newsapi_articles, gnews_articles, rss_articles, page=1, category=None):
    """Format news for Telegram message with pagination and categories"""
    articles_per_page = 6
    all_articles = (newsapi_articles or []) + (gnews_articles or []) + (rss_articles or [])
    if category and category in ['Corporate Strategy & Leadership', 'L&D & Talent Development']:
        # Show articles from specific category
        categorized = categorize_articles(all_articles)
        category_articles = categorized.get(category, [])
        total_pages = (len(category_articles) + articles_per_page - 1) // articles_per_page if category_articles else 1
        start_idx = (page - 1) * articles_per_page
        end_idx = start_idx + articles_per_page
        page_articles = category_articles[start_idx:end_idx]
        
        # Arabic names for categories
        arabic_category_names = {
            'Corporate Strategy & Leadership': 'الاستراتيجية المؤسسية والقيادة',
            'L&D & Talent Development': 'التعلم والتطوير وتنمية المواهب',
        }
        category_label = arabic_category_names.get(category, category)

        message = f"🌟 *أخبار الاستراتيجية المؤسسية والقيادة والتعلم والتطوير - {category_label}*\n"
        message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        message += f"📄 الصفحة {page} من {total_pages} | عدد المقالات: {len(category_articles)}\n"
        
        # Show content extraction stats
        enhanced_count = len([a for a in category_articles if a and a.get('full_content')])
        message += f"📚 مقالات تم استخراج محتواها بالكامل: {enhanced_count}/{len(category_articles)}\n\n"
        
        message += f"📰 *المقالات (الصفحة {page}):*\n"
        for i, article in enumerate(page_articles, start_idx + 1):
            if not article:
                continue
            title = article.get('title', 'No title')
            source = article.get('source', {}).get('name', 'Unknown') if article.get('source') else 'Unknown'
            url = article.get('url', '')
            extraction_method = article.get('extraction_method', 'N/A')
            content_length = article.get('content_length', 0)
            
            if len(title) > 65:
                title = title[:62] + "..."
            
            message += f"{i}. {title}\n"
            message += f"   🏢 المصدر: {source} | 🔧 طريقة الاستخراج: {extraction_method}\n"
            message += f"   📊 طول المحتوى: {content_length} حرفًا\n"
            if url:
                message += f"   🔗 [قراءة التفاصيل]({url})\n"
            message += "\n"
        
        return message, total_pages, category, category_articles
    
    else:
        # Show main summary with top articles
        message = f"🌟 *تحديث أخبار الاستراتيجية المؤسسية والقيادة والتعلم والتطوير*\n"
        message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        # Summary Statistics
        total_articles = len(newsapi_articles or []) + len(gnews_articles or []) + len(rss_articles or [])
        enhanced_count = len([a for a in all_articles if a and a.get('full_content')])       
        # Top Articles Preview
        message += f"📰 *أفضل المقالات اليوم من HBR وMcKinsey وATD وForbes:*\n"
        
        # Show top 10 articles total
        top_articles = all_articles[:10]
        for i, article in enumerate(top_articles, 1):
            if not article:
                continue
            title = article.get('title', 'No title')
            source = article.get('source', {}).get('name', 'Unknown') if article.get('source') else 'Unknown'
            url = article.get('url', '')
            extraction_method = article.get('extraction_method', 'N/A')
            content_length = article.get('content_length', 0)
            
            if len(title) > 65:
                title = title[:62] + "..."
            
            message += f"{i}. {title}\n"
            if url:
                message += f"   🔗 [قراءة التفاصيل]({url})\n"
            message += "\n"
        
        return message, 1, None, all_articles

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    
    if query.data == 'get_news':
        await get_news(update, context)
    elif query.data == 'generate_weekly':
        await generate_weekly_blogs(update, context)
    elif query.data == 'generate_monthly':
        await generate_monthly_blogs(update, context)
    elif query.data == 'generate_magazine':
        await generate_magazine(update, context)
    elif query.data == 'show_categories':
        await show_categories(update, context)
    elif query.data == 'help':
        await help_command(update, context)
    elif query.data == 'main_menu':
        await start(update, context)
    elif query.data.startswith('pdf_'):
        # Handle PDF generation
        category = query.data.replace('pdf_', '')
        if category == 'all':
            await generate_pdf_report(update, context, None)
        else:
            await generate_pdf_report(update, context, category)
    elif query.data.startswith('category_'):
        # Handle category navigation
        parts = query.data.split('_')
        if len(parts) >= 3:
            category = '_'.join(parts[1:-1])  # Reconstruct category name
            page = int(parts[-1])
            await get_news(update, context, page, category)

async def keywords_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow the user to set or clear quality and excellence-specific keywords."""
    message = update.message or update.effective_message
    if not message:
        return
    
    user_input = ''
    if context.args:
        user_input = ' '.join(context.args).strip()
    
    if user_input:
        lowered = user_input.lower()
        if lowered in ('clear', 'reset', 'remove', 'none'):
            context.user_data.pop('blog_keywords', None)
            context.user_data.pop('awaiting_keywords_input', None)
            await message.reply_text("🧹 تم مسح الكلمات المفتاحية المحفوظة. استخدم الأمر /keywords لإضافة كلمات جديدة في أي وقت.")
            return
        
        parsed_kw = parse_keyword_input(user_input)
        if parsed_kw:
            context.user_data['blog_keywords'] = parsed_kw
            context.user_data.pop('awaiting_keywords_input', None)
            await message.reply_text(f"✅ تم حفظ الكلمات المفتاحية!\n{keywords_summary_text(parsed_kw)}")
        else:
            await message.reply_text(
                "⚠️ يرجى استخدام الصيغة التالية (بالإنجليزية):\n"
                "`Primary Keyword | secondary keyword 1, secondary keyword 2`\n"
                "مثال:\n"
                "`Quality Management Excellence 2025 | quality assurance, ISO certification, continuous improvement`",
                parse_mode='Markdown'
            )
        return
    
    context.user_data['awaiting_keywords_input'] = True
    await message.reply_text(KEYWORD_INPUT_INSTRUCTIONS, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    raw_text = (update.message.text or '').strip()
    if not raw_text:
        return
    
    if context.user_data.get('awaiting_keywords_input'):
        lowered = raw_text.lower()
        if lowered in ('cancel', 'stop', 'skip', 'exit'):
            context.user_data.pop('awaiting_keywords_input', None)
            await update.message.reply_text("تم إلغاء إدخال الكلمات المفتاحية. استخدم الأمر /keywords عندما تكون جاهزًا.")
            return
        parsed_kw = parse_keyword_input(raw_text)
        if parsed_kw:
            context.user_data['blog_keywords'] = parsed_kw
            context.user_data.pop('awaiting_keywords_input', None)
            await update.message.reply_text(f"✅ تم حفظ الكلمات المفتاحية!\n{keywords_summary_text(parsed_kw)}")
        else:
            await update.message.reply_text(
                "⚠️ لم أتمكن من فهم الصيغة.\n"
                "يرجى الإرسال بالشكل التالي (بالإنجليزية):\n"
                "`Primary Keyword | secondary keyword 1, secondary keyword 2`\n"
                "مثال: `Quality Management Excellence 2025 | quality assurance, ISO certification, continuous improvement`",
                parse_mode='Markdown'
            )
        return
    
    if '|' in raw_text and not raw_text.startswith('/'):
        parsed_kw = parse_keyword_input(raw_text)
        if parsed_kw:
            context.user_data['blog_keywords'] = parsed_kw
            context.user_data.pop('awaiting_keywords_input', None)
            await update.message.reply_text(f"✅ تم حفظ الكلمات المفتاحية!\n{keywords_summary_text(parsed_kw)}")
            return
        else:
            await update.message.reply_text(
                "⚠️ يبدو أن هذه صيغة كلمات مفتاحية، لكن لم أتمكن من تحليلها.\n"
                "يرجى الإرسال بهذه الصيغة (بالإنجليزية): `Primary Keyword | secondary keyword 1, secondary keyword 2` "
                "أو استخدم الأمر /keywords.",
                parse_mode='Markdown'
            )
            return
    
    text = raw_text.lower()
    
    # Good Morning greeting
    if any(word in text for word in ['صباح الخير', 'صباح', 'good morning', 'morning', 'مرحبا', 'أهلاً', 'اهلا']):
        keyboard = [
            [InlineKeyboardButton("📰 الملخص اليومي", callback_data='get_news')],
            [InlineKeyboardButton("📊 الملخص الأسبوعي", callback_data='generate_weekly'),
             InlineKeyboardButton("📅 الملخص الشهري", callback_data='generate_monthly')],
            [InlineKeyboardButton("📰 المجلة", callback_data='generate_magazine')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🌅 صباح الخير عبدالرحمن! 👋\n\n"
            "أنا ستراتيجي، جاهز لتقديم أحدث رؤى الاستراتيجية المؤسسية والقيادة والتعلم والتطوير.\n"
            "اختر ما تريد من القائمة أدناه:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    elif any(word in text for word in ['news', 'strategy', 'leadership', 'update', 'أخبار', 'استراتيجية', 'قيادة', 'تطوير', 'تعلم']):
        await get_news(update, context)
    elif any(word in text for word in ['weekly', 'week', 'أسبوع', 'أسبوعي']):
        await generate_weekly_blogs(update, context)
    elif any(word in text for word in ['monthly', 'month', 'شهر', 'شهري']):
        await generate_monthly_blogs(update, context)
    elif any(word in text for word in ['magazine', 'مجلة', 'مجلات']):
        await generate_magazine(update, context)
    elif any(word in text for word in ['categories', 'category', 'topics', 'تصنيفات', 'تصنيف']):
        await show_categories(update, context)
    elif any(word in text for word in ['help', 'start', 'menu', 'مساعدة', 'بداية', 'قائمة']):
        await start(update, context)
    else:
        keyboard = [
        [InlineKeyboardButton("📰 الملخص اليومي", callback_data='get_news')],
        [InlineKeyboardButton("📊 الملخص الأسبوعي", callback_data='generate_weekly'),
         InlineKeyboardButton("📅 الملخص الشهري", callback_data='generate_monthly')],
        [InlineKeyboardButton("📰 المجلة", callback_data='generate_magazine')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🌟 أهلاً! أنا **ستراتيجي** — بوت أخبار الاستراتيجية المؤسسية والقيادة والتعلم والتطوير.\n\n"
            "اختر أحد الخيارات في الأسفل أو استخدم هذه الأوامر:\n"
            "• /news - أحدث أخبار الاستراتيجية والقيادة والتعلم والتطوير\n"
            "• /weekly - توليد تقارير أسبوعية\n"
            "• /monthly - توليد تقارير شهرية\n"
            "• /magazine - توليد مجلة Corporate Strategy & L&D الشهرية (PDF)\n"
            "• /keywords - إعداد الكلمات المفتاحية (بالإنجليزية) لتحسين محركات البحث\n"
            "• /categories - تصفح الأخبار حسب التصنيف\n"
            "• /help - المزيد من المعلومات",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = """
🌟 صباح الخير عبدالرحمن! 👋

أنا **ستراتيجي** — محرر محتوى متخصص في الاستراتيجية المؤسسية والقيادة والتعلم والتطوير.
أتابع أحدث الرؤى والمستجدات من أبرز المصادر العالمية كـ HBR وMcKinsey وATD وForbes،
وألخّصها بأسلوب احترافي يحافظ على دقتها ومعناها،
لتصلك المعلومة واضحة، مختصرة، ومباشرة.

🤖 تنويه
أستخدم تقنيات الذكاء الاصطناعي للمساعدة في جمع المحتوى، تنظيمه، وتلخيصه.
المحتوى مخصص للمتابعة والاطلاع فقط، وليس بديلاً عن المصادر الرسمية أو القرارات المهنية.

✨ ماذا أقدّم لك؟

📰 أخبار الاستراتيجية المؤسسية والقيادة يوميًا
📚 رؤى التعلم والتطوير وتنمية المواهب
📊 تقارير أسبوعية وشهرية معمّقة
📰 مجلة Corporate Strategy & L&D الشهرية الاحترافية
⏱️ توفير وقت وجهد المتابعة اليومية

🎯 كيف يمكن الاستفادة مني؟
متابعة أحدث اتجاهات الاستراتيجية والقيادة يوميًا
مشاركة ملخصات الأخبار مع فريق العمل والإدارة
استخدام التقارير في الاجتماعات الاستراتيجية
فهم مستقبل العمل وتنمية المواهب بشكل أوضح
الاعتماد على محتوى جاهز بدون مجهود

📰 المجلة الشهرية للاستراتيجية المؤسسية والقيادة
📘 مجلة شهرية متكاملة باللغة الإنجليزية
📄 بصيغة PDF وجاهزة للاستخدام
🧭 تشمل:
أبرز أخبار الشهر في الاستراتيجية والقيادة
رؤى التعلم والتطوير وتنمية المواهب
اتجاهات مستقبل العمل
تقارير McKinsey وHBR وATD وForbes
مناسبة للإدارة التنفيذية، فرق HR، والمديرين.

🚀 كيف تستخدم ستراتيجي؟
اكتب الكلمة اللي تحتاجها، وأنا أقدّم لك المحتوى فورًا.
تم التطوير التقني بالاشتراك مع شركة ترانسفورمكس
    """
    
    keyboard = [
        [InlineKeyboardButton("⭐ الملخص اليومي", callback_data='get_news')],
        [InlineKeyboardButton("📊 التصنيفات", callback_data='show_categories')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Handle both regular messages and callback queries
    if update.callback_query:
        await update.callback_query.message.reply_text(
            welcome_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

def call_claude_api(system_message, user_message, api_key=None, model=None, max_tokens=16384, temperature=0.7, use_cache=True, use_long_timeout=False):
    """
    Helper function to call AI API (AWS Bedrock or Azure).
    Uses boto3 with AWS SigV4 authentication for Bedrock.

    Args:
        system_message: The system prompt
        user_message: The user prompt
        api_key: Not used (kept for compatibility)
        model: Not used (kept for compatibility)
        max_tokens: Maximum tokens in response (default: 16384)
        temperature: Temperature setting (0.0-1.0)
        use_cache: Not used (kept for compatibility)
        use_long_timeout: If True, use 600s timeout (for long operations)

    Returns:
        tuple: (response_text, error_message) - error_message is None if successful
    """
    try:
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        inference_profile = os.getenv("AWS_BEDROCK_INFERENCE_PROFILE_ID", "")

        if aws_access_key and aws_secret_key:
            # Use AWS Bedrock with boto3 SigV4 authentication
            logger.info(f"Making AWS Bedrock API call - Profile: {inference_profile}")

            import botocore.config as boto_config
            
            timeout_config = boto_config.Config(
                connect_timeout=600 if use_long_timeout else 60,
                read_timeout=600 if use_long_timeout else 60,
                retries={'max_attempts': 2}
            )

            client = boto3.client(
                service_name='bedrock-runtime',
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                config=timeout_config
            )

            # Build the request body for Anthropic Claude on Bedrock
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "user", "content": user_message}
                ]
            }
            if system_message:
                body["system"] = system_message

            # Use inference profile ID if available, otherwise use model ID
            model_id = inference_profile if inference_profile else "anthropic.claude-sonnet-4-20250514"

            logger.info(f"   Model ID: {model_id}")
            logger.info(f"   Using: AWS Bedrock (boto3 SigV4)")

            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType='application/json',
                accept='application/json'
            )

            response_data = json.loads(response['body'].read())

            # Parse Anthropic response format
            if response_data.get("content") and len(response_data["content"]) > 0:
                content_text = response_data["content"][0].get("text", "")
                stop_reason = response_data.get("stop_reason", "unknown")
                logger.info(f"Bedrock response stop_reason: {stop_reason}")

                if not content_text:
                    return None, "Bedrock returned empty content"

                if stop_reason == "max_tokens":
                    logger.warning("⚠️ Response was truncated due to max_tokens limit!")

                return content_text, None
            else:
                logger.error(f"❌ No content in Bedrock response. Keys: {list(response_data.keys())}")
                return None, "Bedrock returned no content"

        elif AZURE_API_KEY:
            # Fallback to Azure API
            api_url = AZURE_API_URL.rstrip('/')
            if '/v1/' not in api_url and '/anthropic' not in api_url:
                api_url = api_url.rstrip('/') + '/anthropic/v1/messages'

            headers = {
                "Content-Type": "application/json",
                "x-api-key": AZURE_API_KEY,
                "anthropic-version": "2023-06-01"
            }

            body = {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "user", "content": user_message}
                ]
            }
            if system_message:
                body["system"] = system_message

            timeout_duration = 600 if use_long_timeout else 60
            logger.info(f"Making Azure API call - Model: {AZURE_MODEL}")

            response = requests.post(api_url, headers=headers, json=body, timeout=timeout_duration)

            if response.status_code != 200:
                return None, f"Azure API Error: {response.status_code} - {response.text[:200]}"

            response_data = response.json()

            if response_data.get("content") and len(response_data["content"]) > 0:
                content_text = response_data["content"][0].get("text", "")
                return content_text, None

            choices = response_data.get("choices", [])
            if choices:
                content_text = choices[0].get("message", {}).get("content", "")
                return content_text, None

            return None, "Azure API returned no content"
        else:
            return None, "No AI API credentials configured (neither AWS Bedrock nor Azure)"

    except Exception as e:
        error_type = type(e).__name__
        error_str = str(e)
        logger.error(f"AI API error: {error_type}: {error_str}")
        return None, f"AI API Error ({error_type}): {error_str}"

def categorize_articles_for_blogs(articles):
    """Categorize articles into two main blog themes: Strategy & Leadership vs L&D"""
    
    if not articles:
        logger.warning("No articles provided to categorize_articles_for_blogs")
        return {
            'strategy': [],
            'ld': []
        }
    
    # Blog 1: Corporate Strategy & Leadership
    # Blog 2: L&D & Talent Development
    
    strategy_articles = []
    ld_articles = []
    general_articles = []
    
    for article in articles:
        if not article:
            continue
        title = article.get('title', '') or ''
        description = article.get('description', '') or ''
        full_content = article.get('full_content', '') or ''
        content = f"{title.lower()} {description.lower()} {full_content.lower()[:1000]}"
        
        # Count keyword frequency for each category
        strategy_score = sum(1 for keyword in STRATEGY_LEADERSHIP_KEYWORDS if keyword in content)
        ld_score = sum(1 for keyword in LD_TALENT_KEYWORDS if keyword in content)
        
        if strategy_score > ld_score and strategy_score > 0:
            strategy_articles.append(article)
        elif ld_score > 0:
            ld_articles.append(article)
        else:
            general_articles.append(article)
    
    # Distribute general articles
    half_general = len(general_articles) // 2
    strategy_articles.extend(general_articles[:half_general])
    ld_articles.extend(general_articles[half_general:])
    
    return {
        'strategy': strategy_articles,
        'ld': ld_articles
    }

def parse_blog_sections(blog_content):
    """Parse blog content and return structured sections, preserving paragraph breaks."""
    if not blog_content:
        logger.warning("No blog content provided to parse_blog_sections")
        return []

    sections = []
    current_section = {"title": "", "content": "", "level": 0}

    lines = blog_content.split('\n')

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('#'):
            if current_section["content"].strip():
                sections.append(current_section.copy())
            level = len(stripped) - len(stripped.lstrip('#'))
            title = stripped.lstrip('#').strip()
            current_section = {"title": title, "content": "", "level": level}
        elif not stripped:
            # Preserve paragraph break
            current_section["content"] += "\n\n"
        else:
            current_section["content"] += stripped + " "

    if current_section["content"].strip():
        sections.append(current_section)

    return sections


def strip_markdown(text):
    """Remove Markdown syntax for clean PDF rendering."""
    import re
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^===+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\-\*]\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _escape_html(text):
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))


def _inline_markdown(text):
    """Convert inline Markdown (bold, italic) to HTML inside an already-escaped string."""
    import re
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<em>\1</em>', text)
    return text


def extract_og_image(url, timeout=5):
    """Extract Open Graph (or twitter / first article) image URL from a webpage."""
    if not url or not url.startswith('http'):
        return None
    try:
        import urllib3
        urllib3.disable_warnings()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        }
        resp = requests.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=True)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.content, 'html.parser')
        for sel in [
            ('meta', {'property': 'og:image'}),
            ('meta', {'property': 'og:image:url'}),
            ('meta', {'name': 'twitter:image'}),
            ('meta', {'name': 'twitter:image:src'}),
        ]:
            tag = soup.find(*sel[:1], **{'attrs': sel[1]})
            if tag and tag.get('content'):
                img = tag['content']
                if img.startswith('//'):
                    img = 'https:' + img
                if img.startswith('http'):
                    return img
        # Last resort: first big article image
        for img in soup.find_all('img', src=True):
            src = img['src']
            if src.startswith('//'):
                src = 'https:' + src
            if src.startswith('http') and not any(x in src.lower() for x in ['logo', 'icon', 'avatar', 'sprite', 'pixel']):
                return src
    except Exception as e:
        logger.debug(f"og:image extraction failed for {url}: {e}")
    return None


def fetch_images_for_articles(articles, max_articles=15, timeout=5):
    """Fetch og:images for a batch of source articles in parallel."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    images = []
    urls = [a.get('url') for a in articles[:max_articles] if a and a.get('url')]
    if not urls:
        return images
    logger.info(f"Fetching og:images for {len(urls)} source articles (parallel)...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_url = {executor.submit(extract_og_image, url, timeout): url for url in urls}
        try:
            for future in as_completed(future_to_url, timeout=timeout * 3):
                try:
                    img = future.result(timeout=timeout)
                    if img:
                        images.append(img)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Image fetching wait timed out: {e}")
    logger.info(f"Got {len(images)} valid og:images out of {len(urls)} URLs")
    return images


def strip_seo_preamble(text):
    """Remove SEO metadata block (English labels) the AI prepends before the actual Arabic content."""
    if not text:
        return text
    import re
    seo_markers = [
        'SEO Title', 'Meta Description', 'Recommended Slug', 'Headings Structure',
        'Slug:', 'Meta:', 'Title:', 'العناصر الإلزامية', 'SEO العناصر',
    ]
    lines = text.split('\n')
    # Find first horizontal rule
    for i, line in enumerate(lines):
        s = line.strip()
        if s in ('---', '***', '___') or (len(s) >= 3 and set(s) <= {'-', '=', '*', '_'}):
            preamble = '\n'.join(lines[:i])
            if any(m in preamble for m in seo_markers):
                logger.info(f"Stripped SEO preamble ({i} lines)")
                return '\n'.join(lines[i+1:]).lstrip()
            break
    # Fallback: remove leading lines that are SEO-labeled
    cleaned = []
    skipping = True
    for line in lines:
        s = line.strip()
        if skipping:
            if not s:
                continue
            # Skip lines that are SEO metadata or English-labeled bullet/header
            if any(m in s for m in seo_markers):
                continue
            if s.startswith('#') and any(m in s for m in seo_markers):
                continue
            # Skip "H1:", "H2:" outline lines
            if re.match(r'^[\-\*•]\s*H[1-6]\s*:', s):
                continue
            skipping = False
        cleaned.append(line)
    return '\n'.join(cleaned).lstrip()


def remove_english_lines(text):
    """Remove lines that are predominantly English (more than 60% Latin characters)."""
    if not text:
        return text
    out = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            out.append(line)
            continue
        # Strip markdown chars first
        plain = ''.join(c for c in stripped if c.isalpha())
        if not plain:
            out.append(line)
            continue
        latin = sum(1 for c in plain if c.isascii() and c.isalpha())
        ratio = latin / len(plain)
        # If >60% Latin and the line has at least 4 Latin chars, drop it
        if ratio > 0.6 and latin >= 4:
            logger.debug(f"Dropping English line: {stripped[:60]}")
            continue
        out.append(line)
    return '\n'.join(out)


def markdown_to_html(text):
    """Convert blog Markdown to safe HTML for WeasyPrint rendering."""
    if not text:
        return ""
    out = []
    in_list = False
    in_olist = False

    def close_lists():
        nonlocal in_list, in_olist
        if in_list:
            out.append('</ul>')
            in_list = False
        if in_olist:
            out.append('</ol>')
            in_olist = False

    for raw in text.split('\n'):
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            close_lists()
            continue

        # Horizontal rules
        if stripped in ('---', '***', '___') or (len(stripped) >= 3 and set(stripped) <= {'-', '=', '*', '_'}):
            close_lists()
            out.append('<hr>')
            continue

        # Headers
        if stripped.startswith('#'):
            close_lists()
            level = len(stripped) - len(stripped.lstrip('#'))
            level = min(max(level, 1), 4)
            content = stripped.lstrip('#').strip()
            content = _inline_markdown(_escape_html(content))
            out.append(f'<h{level}>{content}</h{level}>')
            continue

        # Numbered list
        import re
        num_match = re.match(r'^(\d+)[\.\)]\s+(.+)$', stripped)
        if num_match:
            if in_list:
                out.append('</ul>')
                in_list = False
            if not in_olist:
                out.append('<ol>')
                in_olist = True
            item = _inline_markdown(_escape_html(num_match.group(2)))
            out.append(f'<li>{item}</li>')
            continue

        # Bullet list
        if stripped.startswith(('- ', '* ', '• ', '+ ')):
            if in_olist:
                out.append('</ol>')
                in_olist = False
            if not in_list:
                out.append('<ul>')
                in_list = True
            item = _inline_markdown(_escape_html(stripped[2:].strip()))
            out.append(f'<li>{item}</li>')
            continue

        # Blockquote
        if stripped.startswith('> '):
            close_lists()
            content = _inline_markdown(_escape_html(stripped[2:].strip()))
            out.append(f'<blockquote>{content}</blockquote>')
            continue

        # Regular paragraph
        close_lists()
        content = _inline_markdown(_escape_html(stripped))
        out.append(f'<p>{content}</p>')

    close_lists()
    return '\n'.join(out)


def process_arabic_text(text):
    """Reshape and reorder Arabic text for correct display in PDF."""
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def create_quality_blog_pdf(blog_content, blog_title, is_temp_file=True):
    """Render blog PDF via WeasyPrint — proper Arabic + mixed-language support."""
    if not blog_content or not blog_title:
        logger.warning("No blog content or title provided to create_quality_blog_pdf")
        return None

    if not WEASYPRINT_AVAILABLE:
        logger.error("WeasyPrint not available — cannot generate blog PDF")
        return None

    if is_temp_file:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        filename = temp_file.name
        temp_file.close()
    else:
        filename = f"{blog_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"

    try:
        import pathlib as _pathlib
        template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

        date_str = datetime.now().strftime('%Y-%m-%d')
        if 'يومي' in blog_title:
            meta_text = f"تقرير يومي • {date_str}"
        elif 'أسبوعي' in blog_title:
            meta_text = f"تقرير أسبوعي • {date_str}"
        elif 'شهري' in blog_title:
            meta_text = f"تقرير شهري • {date_str}"
        else:
            meta_text = f"تقرير • {date_str}"

        logo_path_fs = os.path.join(template_dir, 'images', 'logo.png')
        logo_uri = _pathlib.Path(logo_path_fs).as_uri() if os.path.exists(logo_path_fs) else None

        cleaned = strip_seo_preamble(blog_content)
        cleaned = remove_english_lines(cleaned)
        content_html = markdown_to_html(cleaned)

        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('blog.html')
        html_out = template.render(
            title=blog_title,
            meta_text=meta_text,
            content_html=content_html,
            logo_path=logo_uri,
        )

        css_path = os.path.join(template_dir, 'blog.css')
        HTML(string=html_out, base_url=template_dir).write_pdf(
            filename,
            stylesheets=[CSS(css_path)]
        )
        logger.info(f"Successfully created blog PDF via WeasyPrint: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error creating blog PDF via WeasyPrint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def _create_quality_blog_pdf_DEPRECATED_REPORTLAB(blog_content, blog_title, is_temp_file=True):
    """Old ReportLab implementation kept for reference; not used."""
    if not blog_content or not blog_title:
        return None
    if is_temp_file:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        filename = temp_file.name
        temp_file.close()
    else:
        filename = f"{blog_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"

    doc = SimpleDocTemplate(filename, pagesize=A4,
                          topMargin=0.75*inch, bottomMargin=0.75*inch,
                          leftMargin=0.75*inch, rightMargin=0.75*inch)
    
    # Define comprehensive blog styles
    styles = getSampleStyleSheet()
    
    # Blog title style (main headline) - use Normal parent to avoid bold font lookup
    blog_title_style = ParagraphStyle(
        'BlogTitle',
        parent=styles['Normal'],
        fontSize=28,
        spaceAfter=15,
        spaceBefore=0,
        alignment=TA_CENTER,
        textColor=HexColor('#1a1a1a'),
        fontName='Amiri',
        leading=32
    )
    
    # Blog metadata style (date, info)
    blog_meta_style = ParagraphStyle(
        'BlogMeta',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=HexColor('#666666'),
        fontName='Amiri'
    )
    
    # Section header style (H2)
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontSize=18,
        spaceAfter=12,
        spaceBefore=24,
        alignment=TA_RIGHT,
        textColor=HexColor('#2c3e50'),
        fontName='Amiri',
        leading=26,
        borderPad=4,
        borderWidth=0,
        borderColor=HexColor('#2c3e50'),
    )

    # Subsection header style (H3)
    subsection_header_style = ParagraphStyle(
        'SubsectionHeader',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=8,
        spaceBefore=16,
        alignment=TA_RIGHT,
        textColor=HexColor('#34495e'),
        fontName='Amiri',
        leading=22,
    )

    # Blog paragraph style — TA_RIGHT required for bidi-processed Arabic
    blog_paragraph_style = ParagraphStyle(
        'BlogParagraph',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=10,
        spaceBefore=0,
        alignment=TA_RIGHT,
        leading=22,
        textColor=HexColor('#222222'),
        fontName='Amiri',
        wordWrap='RTL',
    )
    
    # Build the document content
    content = []
    
    # Add logo at the top right corner if available
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logo_path = os.path.join(template_dir, 'images', 'logo.png')
    if os.path.exists(logo_path):
        try:
            # Calculate available width (A4 width - left margin - right margin)
            available_width = A4[0] - (0.75*inch * 2)  # A4 width minus margins
            # Add logo with bigger size (5 inches wide, maintain aspect ratio) in top right corner
            logo = Image(logo_path, width=5*inch, height=1.25*inch, kind='proportional')
            # Use Table to position logo in top right corner
            logo_table = Table([[logo]], colWidths=[available_width])
            logo_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            content.append(logo_table)
            content.append(Spacer(1, 10))
        except Exception as e:
            logger.warning(f"Could not add logo to PDF: {str(e)}")
    
    # Add blog title
    content.append(Paragraph(process_arabic_text(blog_title), blog_title_style))
    
    # Add metadata
    date_str = datetime.now().strftime('%B %d, %Y')
    week_range = f"{(datetime.now() - timedelta(days=7)).strftime('%B %d')} - {datetime.now().strftime('%B %d, %Y')}"
    month_range = f"{(datetime.now() - timedelta(days=30)).strftime('%B %d')} - {datetime.now().strftime('%B %d, %Y')}"
    
    if 'يومي' in blog_title:
        meta_text = f"تقرير الاستراتيجية والقيادة والتعلم والتطوير اليومي • تم الإنشاء في {date_str}"
    elif 'أسبوعي' in blog_title:
        meta_text = f"تقرير الاستراتيجية والقيادة والتعلم والتطوير الأسبوعي • {week_range} • تم الإنشاء في {date_str}"
    elif 'شهري' in blog_title:
        meta_text = f"تقرير الاستراتيجية والقيادة والتعلم والتطوير الشهري • {month_range} • تم الإنشاء في {date_str}"
    else:
        meta_text = f"تقرير الاستراتيجية المؤسسية والقيادة والتعلم والتطوير • تم الإنشاء في {date_str}"
    content.append(Paragraph(process_arabic_text(meta_text), blog_meta_style))
    
    content.append(Spacer(1, 10))
    
    # Parse the blog content into sections
    sections = parse_blog_sections(blog_content)
    
    for section in sections:
        title = section['title']
        section_content = section['content'].strip()
        level = section['level']
        
        # Skip empty sections
        if not section_content:
            continue
        
        # Add section header based on level
        if level == 1:
            continue  # Main title already added
        elif level == 2:
            if title:
                content.append(Paragraph(process_arabic_text(title), section_header_style))
        elif level == 3:
            if title:
                content.append(Paragraph(process_arabic_text(title), subsection_header_style))
        
        # Add section content — split by paragraph breaks, not by sentence
        if section_content:
            import re
            raw_paragraphs = re.split(r'\n\n+', section_content)
            for para in raw_paragraphs:
                para = strip_markdown(para.replace('\n', ' ').strip())
                if para and len(para) > 10:
                    content.append(Paragraph(process_arabic_text(para), blog_paragraph_style))
    
    # Build the PDF
    try:
        doc.build(content)
        logger.info(f"Successfully created quality blog PDF: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error creating quality blog PDF: {str(e)}")
        return None

async def generate_pdf_report(update: Update, context: ContextTypes.DEFAULT_TYPE, category=None):
    """Generate and send enhanced PDF report with full content in daily blog style."""
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass  # Callback may already be answered
    
    # Send status message
    status_message = await query.message.reply_text(
        "📄 جارٍ توليد تقرير PDF محسّن...\n📖 يتم الآن استخراج المحتوى الكامل لتحليل أكثر تفصيلاً...\n⏳ يرجى الانتظار من 1 إلى 2 دقيقة.",
        parse_mode='Markdown'
    )
    
    try:
        await status_message.edit_text(
            "📄 *الخطوة 1/2:* توليد محتوى تقريري بأسلوب مدونة الاستراتيجية والقيادة والتعلم...",
            parse_mode='Markdown'
        )
        
        # Load articles from saved file
        if not os.path.exists("all_enhanced_quality_articles.txt"):
            await status_message.edit_text(
                "❌ لا توجد مقالات متاحة حاليًا. يرجى تشغيل الأمر /news أولاً لجلب المقالات.",
                parse_mode='Markdown'
            )
            return
        
        with open("all_enhanced_quality_articles.txt", "r", encoding="utf-8") as f:
            all_articles = json.load(f)
        
        # Prepare articles according to scope
        user_keywords = get_user_keywords(context)
        if category and category != 'all':
            categorized = categorize_articles(all_articles)
            articles_for_report = categorized.get(category, [])
            blog_title = f"تقرير الاستراتيجية المؤسسية والقيادة والتعلم والتطوير اليومي – {category}"
            blog_content = generate_daily_quality_blog_with_ai(articles_for_report, category, keywords=user_keywords)
        else:
            articles_for_report = all_articles
            blog_title = "تقرير الاستراتيجية المؤسسية والقيادة والتعلم والتطوير اليومي"
            blog_content = generate_daily_quality_blog_with_ai(articles_for_report, None, keywords=user_keywords)

        # Fallback if model returned too-short, empty content, or error message
        if not blog_content or len(blog_content.strip()) < 100 or (blog_content.startswith("# التقرير اليومي للاستراتيجية") and "Error" in blog_content):
            logger.warning("Model returned empty/short content or error. Using fallback blog content.")
            blog_content = build_fallback_quality_blog_content(articles_for_report, category)
        
        # Build PDF using blog formatter for consistent look
        pdf_filename = create_quality_blog_pdf(blog_content, blog_title, is_temp_file=True)
        report_title = blog_title
        
        await status_message.edit_text(
            "📄 *الخطوة 2/2:* إنشاء ملف PDF...",
            parse_mode='Markdown'
        )
        
        # Send the PDF file
        if pdf_filename and os.path.exists(pdf_filename):
            with open(pdf_filename, 'rb') as pdf_file:
                await query.message.reply_document(
                    document=pdf_file,
                    filename=f"{report_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    caption=f"📄 *{report_title}*\n📅 تاريخ الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n📖 تقرير محسّن مع استخراج كامل لمحتوى المقالات",
                    parse_mode='Markdown'
                )
            
            # Clean up the temporary file
            os.unlink(pdf_filename)
            
            # Update status message
            await status_message.edit_text(
                "✅ تم توليد تقرير PDF محسّن وإرساله بنجاح!\n📖 يشمل محتوى كاملًا للمقالات وتحليلًا متعمقًا للاستراتيجية والقيادة والتعلم والتطوير.",
                parse_mode='Markdown'
            )
        else:
            await status_message.edit_text(
                "❌ خطأ: تعذر إنشاء ملف PDF.",
                parse_mode='Markdown'
            )
        
    except Exception as e:
        try:
            await status_message.edit_text(
                f"❌ حدث خطأ أثناء توليد تقرير PDF المحسّن: {str(e)}",
                parse_mode='Markdown'
            )
        except Exception as edit_error:
            # Try to send a new message instead
            try:
                await status_message.reply_text(
                    f"❌ حدث خطأ أثناء توليد تقرير PDF المحسّن: {str(e)}"
                )
            except Exception as reply_error:
                logger.error(f"Error sending reply: {reply_error}")

def generate_daily_quality_blog_with_ai(articles, category=None, keywords=None):
    """Generate a daily quality and excellence blog-style summary so PDFs match weekly blog formatting."""
    if not articles:
        logger.warning("No articles provided to generate_daily_quality_blog_with_ai")
        return "# التقرير اليومي للاستراتيجية المؤسسية والقيادة والتعلم والتطوير\n\nلا توجد مقالات متاحة اليوم."
    
    # Prepare content from articles (shorter excerpts for daily)
    max_daily_articles = min(len(articles), 40)
    news_content = ""
    for i, article in enumerate(articles[:max_daily_articles], 1):
        if not article:
            continue
        title = article.get('title', 'No title')
        source = article.get('source', {}).get('name', 'Unknown source') if article.get('source') else 'Unknown source'
        full_content = article.get('full_content', article.get('description', 'No content'))
        published_date = article.get('publishedAt', 'Unknown date')
        url = article.get('url', '')
        if full_content and len(full_content) > 450:
            full_content = full_content[:450] + "..."
        news_content += f"""
ARTICLE {i}:
Title: {title}
Source: {source}
Date: {published_date}
URL: {url}
Content: {full_content or 'No content available'}
---
"""
    
    # Choose focus
    if category in [
        "Corporate Strategy & Leadership",
        "L&D & Talent Development"
    ]:
        title_suffix = f" – {category}"
        intro_target = f"أهم تطورات {category} اليوم"
    else:
        title_suffix = ""
        intro_target = "أهم تطورات الاستراتيجية المؤسسية والقيادة والتعلم والتطوير اليوم"
    
    # System message (static, will be cached)
    system_message = (
        "You are a professional Arabic writer. "
        "You write concise, structured daily blog reports about corporate strategy, leadership, learning & development, and talent management in MODERN STANDARD ARABIC. "
        "All visible content, headings, and paragraphs must be in Arabic, but you may read/analyze English source text. "
        "Keep the style صحفي احترافي وسهل القراءة، واستخدم عناوين Markdown."
    )
    
    keyword_guidance = build_keyword_instruction_block(keywords)
    
    user_prompt = f"""
    {keyword_guidance}

    اكتب تقريرًا يوميًا موجزًا بأسلوب مدونة عن {intro_target} باللغة العربية الفصحى،
    مستخدمًا البنية التالية **بالضبط** باستخدام Markdown. اجعل النص مركزًا وغنيًا بالمعلومات.

# [اكتب عنوانًا عربيًا جذابًا لليوم]

## نظرة سريعة
[فقرة من 80–120 كلمة تلخص أهم محاور اليوم والعناوين الرئيسية في أخبار الاستراتيجية المؤسسية والقيادة والتعلم والتطوير]

## أبرز الأخبار
[2-3 فقرات قصيرة، كل منها 80–120 كلمة، تربط بين أهم التحديثات في مجال الاستراتيجية والقيادة والتعلم والتطوير]

## تطورات لافتة
[قائمة نقطية من 6–8 عناصر مختصرة، كل عنصر 1–2 جملة، تشير إلى شركات أو مبادرات أو نتائج محددة]

## السوق والتأثير
[1–2 فقرة عن تأثير الأخبار على قطاع الاستراتيجية والقيادة والتعلم والتطوير]

## ما الذي نترقبه لاحقًا
[3–5 نقاط حول الإعلانات المتوقعة أو الاتجاهات الصاعدة في مجال الاستراتيجية والقيادة والتعلم والتطوير]

متطلبات أساسية:
- استخدم عناوين الأقسام العربية أعلاه كما هي مع تنسيق Markdown (##).
- امزج المعلومات من عدة مقالات، ولا تكتفِ بسردها واحدة تلو الأخرى.
- اذكر الأسماء والأرقام والمبادرات والمنظمات كلما أمكن ذلك.
- اجعل الأسلوب صحفيًا احترافيًا وواضحًا، مناسبًا لتقرير يومي عن الاستراتيجية والقيادة والتعلم والتطوير.
- ركّز دائمًا على صلة المحتوى بمجال الاستراتيجية المؤسسية والقيادة والتعلم والتطوير.

مقالات للتحليل ({max_daily_articles} مقالاً):
{news_content}
"""
    
    # Call AWS Bedrock Claude API
    content, error = call_claude_api(
        system_message=system_message,
        user_message=user_prompt,
        max_tokens=50000,
        temperature=0.45,
        use_cache=True,
        use_long_timeout=True
    )
    
    if error:
        return f"# التقرير اليومي للاستراتيجية المؤسسية والقيادة والتعلم والتطوير{title_suffix}\n\nحدث خطأ أثناء توليد المحتوى: {error}"
    
    if not content:
        return f"# التقرير اليومي للاستراتيجية المؤسسية والقيادة والتعلم والتطوير{title_suffix}\n\nتعذّر توليد المحتوى اليوم."
    
    if not content.lstrip().startswith('#'):
        prefix_title = f"# التقرير اليومي للاستراتيجية المؤسسية والقيادة والتعلم والتطوير{title_suffix}\n\n"
        return prefix_title + content
    
    logger.info(f"Model content length: {len(content)}")
    return content

def build_fallback_quality_blog_content(articles, category=None):
    """Build a minimal, readable daily report from available articles when the model response is empty."""
    heading = f"# التقرير اليومي للاستراتيجية المؤسسية والقيادة والتعلم والتطوير – {category}" if category else "# التقرير اليومي للاستراتيجية المؤسسية والقيادة والتعلم والتطوير"
    if not articles:
        return f"{heading}\n\nلا توجد مقالات متاحة اليوم."
    lines = [heading, "", "## أهم العناوين", ""]
    count = 0
    for art in articles:
        if not art:
            continue
        title = art.get('title') or art.get('headline') or art.get('name')
        desc = art.get('description') or art.get('summary') or art.get('excerpt') or art.get('full_content', '')[:200]
        if not title and not desc:
            continue
        bullet = f"- {title.strip()}" if title else "- (بدون عنوان)"
        if desc:
            bullet += f" — {desc.strip()[:240]}"
        lines.append(bullet)
        count += 1
        if count >= 20:
            break
    if count == 0:
        lines.append("- لا توجد عناصر قابلة للعرض.")
    lines += ["", "## ملاحظات", "تم إنشاء هذا الملخص الاحتياطي بسبب عدم توفر استجابة من نموذج الذكاء الاصطناعي."]
    return "\n".join(lines)

def generate_quality_blog_with_ai(articles, blog_theme, time_period="weekly", keywords=None):
    """Generate a quality and excellence blog post using Claude AI"""
    
    if not articles:
        logger.warning(f"No articles provided to generate_quality_blog_with_ai for {blog_theme}")
        return "تعذّر إنشاء مدونة الجودة والتميز: لا توجد مقالات كافية للتحليل."
    
    # Prepare content from articles
    news_content = ""
    article_count = min(len(articles), 30)
    
    for i, article in enumerate(articles[:article_count], 1):
        if not article:
            continue
        title = article.get('title', 'No title')
        source = article.get('source', {}).get('name', 'Unknown source') if article.get('source') else 'Unknown source'
        full_content = article.get('full_content', article.get('description', 'No content'))
        published_date = article.get('publishedAt', 'Unknown date')
        url = article.get('url', '')
        
        if full_content and len(full_content) > 600:
            full_content = full_content[:600] + "..."
        
        news_content += f"""
ARTICLE {i}:
Title: {title}
Source: {source}
Date: {published_date}
URL: {url}
Content: {full_content or 'No content available'}
---
"""
    
    # Determine period-specific language (Arabic labels)
    period_adj = "أسبوعية" if time_period == "weekly" else "شهرية"
    period_cap = "هذا الأسبوع" if time_period == "weekly" else "هذا الشهر"
    period_next = "الأسبوع القادم" if time_period == "weekly" else "الشهر القادم"
    
    # Create theme-specific prompts
    if blog_theme == "management":
        blog_focus = "الاستراتيجية المؤسسية والقيادة"
        blog_angle = (
            "ركّز على تطورات الاستراتيجية المؤسسية، والتحول الرقمي، والتخطيط الاستراتيجي، والحوكمة، "
            "ومستقبل العمل، واتجاهات السوق، ورؤى القيادة التنفيذية. "
            "الجمهور المستهدف هو المديرون التنفيذيون، والاستشاريون، وصانعو القرار في المؤسسات. "
            "ابرز استراتيجيات الأعمال، وفرص النمو، والشراكات، وأبرز رؤى القيادة."
        )
    else:  # improvement
        blog_focus = "التعلم والتطوير وتنمية المواهب"
        blog_angle = (
            "ركّز على تطورات التعلم والتطوير، وتنمية المواهب، وبرامج التدريب، وتقنيات التعلم، "
            "والتعلم المخصص، وتحليلات التعلم، والاتجاهات العالمية في مجال L&D. "
            "الجمهور المستهدف هو مديرو التعلم والتطوير، ومتخصصو الموارد البشرية، وقادة تطوير المواهب. "
            "أبرز أفضل الممارسات، ونماذج الكفاءات، وأدوات التعلم الحديثة، وتجارب التطوير الناجحة."
        )
    
    system_message = (
        "You are a professional Arabic Corporate Strategy and L&D industry blogger. "
        "You always write engaging, insightful blog posts in MODERN STANDARD ARABIC about corporate strategy, leadership, learning & development, and talent management. "
        "Use clear structure, strong headings in Arabic, and actionable insights. "
        "Always use proper markdown formatting for headers, and keep the tone صحفي احترافي وجذّاب."
    )
    
    keyword_guidance = build_keyword_instruction_block(keywords)
    
    user_prompt = f"""
    {keyword_guidance}

    اكتب تدوينة {period_adj} عربية شاملة عن {blog_focus} خلال {period_cap}،
    مستخدمًا البنية التالية **بالضبط** باستخدام Markdown:

    # [اكتب عنوانًا عربيًا جذابًا]

    ## مقدمة
    [مقدمة مشوّقة من 150 كلمة تقريبًا تجذب القارئ وتشرح سياق التقرير]

    ## أهم قصة في {period_cap}
    [250–300 كلمة تغطي التطور الأهم في أخبار الاستراتيجية المؤسسية والقيادة والتعلم والتطوير لهذا {period_cap}]

    ## تطور رئيسي ثانٍ
    [250–300 كلمة عن ثاني أهم تطور]

    ## اتجاهات بارزة
    [200–250 كلمة عن أبرز الاتجاهات والأنماط الملحوظة]

    ## تركيز على مبادرة أو قطاع
    [200–250 كلمة تبرز مبادرات أو شركات أو قطاعات محددة]

    ## ملخصات سريعة
    [200–250 كلمة تغطي 6–8 تطورات إضافية بشكل موجز]

    ## مراقبة السوق
    [150–200 كلمة عن الاستثمارات، الشراكات، وأخبار الأعمال في مجال الاستراتيجية والقيادة]

    ## ما الذي ينتظرنا لاحقًا
    [100–150 كلمة تستشرف ما قد يحدث في {period_next}]

    ## خلاصة
    [فقرة ختامية قصيرة بأهم الرسائل والتوصيات]

    زاوية التغطية:
    {blog_angle}

    متطلبات أساسية:
    - يجب استخدام عناوين الأقسام العربية أعلاه كما هي مع تنسيق Markdown (##).
    - استشهد بما لا يقل عن 15–20 مقالًا مختلفًا داخل التدوينة.
    - اذكر أسماء الشركات، المبادرات، الأرقام، التواريخ، والمصادر كلما أمكن.
    - اجعل الأسلوب عربيًا صحفيًا مهنيًا وجذابًا.
    - اجعل كل قسم غنيًا بالمعلومات وقابلًا للاستخدام لمحترفي الاستراتيجية والقيادة والتعلم والتطوير.
    - أمامك {article_count} مقالًا، فاستخدم هذا التنوع في بناء الصورة الكلية.

    محتوى المقالات للتحليل ({article_count} مقالاً):
    {news_content}

    اكتب التدوينة باللغة العربية الفصحى فقط، بدون أي فقرات تفسيرية باللغة الإنجليزية.
    """
    
    content, error = call_claude_api(
        system_message=system_message,
        user_message=user_prompt,
        max_tokens=50000,
        temperature=0.5,
        use_cache=True,
        use_long_timeout=True
    )
    
    if error:
        return f"حدث خطأ أثناء توليد التدوينة: {error}"
    else:
        return content



async def generate_weekly_blogs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate comprehensive weekly Quality and Excellence blog posts."""
    user_id = get_user_id(update)
    
    # Check usage limit
    has_limit, current_usage = check_usage_limit(user_id, 'weekly')
    if not has_limit:
        limit_message = (
            f"❌ *تم الوصول إلى الحد الأقصى*\n\n"
            f"لقد استخدمت جميع المحاولات المتاحة للتقارير الأسبوعية ({USAGE_LIMITS['weekly']}/{USAGE_LIMITS['weekly']}).\n\n"
            f"استخدم الأمر `/reset` لإعادة تعيين المحاولات (يتطلب صلاحيات المسؤول)."
        )
        if update.callback_query:
            await update.callback_query.answer("تم الوصول إلى الحد الأقصى", show_alert=True)
            await update.callback_query.message.reply_text(limit_message, parse_mode='Markdown')
        else:
            await update.message.reply_text(limit_message, parse_mode='Markdown')
        return
    
    # Increment usage
    increment_usage(user_id, 'weekly')
    
    if update.callback_query:
        await update.callback_query.answer()
        message = await update.callback_query.message.reply_text(
            "📝 *مولّد التقارير الأسبوعية للاستراتيجية المؤسسية والقيادة والتعلم والتطوير*\n\n⏳ جارٍ إعداد تحليل أسبوعي شامل...\n📊 سيتم تحليل أحدث المقالات من HBR وMcKinsey وATD وForbes لآخر 7 أيام\n⏰ الزمن المتوقع: 3–5 دقائق\n\nيرجى الانتظار...",
            parse_mode='Markdown'
        )
    else:
        message = await update.message.reply_text(
            "📝 *مولّد التقارير الأسبوعية للاستراتيجية المؤسسية والقيادة والتعلم والتطوير*\n\n⏳ جارٍ إعداد تحليل أسبوعي شامل...\n📊 سيتم تحليل أحدث المقالات من HBR وMcKinsey وATD وForbes لآخر 7 أيام\n⏰ الزمن المتوقع: 3–5 دقائق\n\nيرجى الانتظار...",
            parse_mode='Markdown'
        )
    
    try:
        await message.edit_text(
            "📝 *الخطوة 1/4:* جلب أخبار الاستراتيجية المؤسسية والقيادة والتعلم والتطوير الأسبوعية...\n📡 يتم الآن جمع المقالات من HBR وMcKinsey وATD وForbes من آخر 7 أيام...",
            parse_mode='Markdown'
        )
        
        newsapi_articles = [] # fetch_weekly_quality_news() or []
        gnews_articles = [] # fetch_gnews_quality() or []
        rss_articles = fetch_rss_quality() or []
        try:
            custom_articles = await fetch_all_custom_scrapers(max_articles_per_source=50)
        except Exception as e:
            logger.warning(f"Custom scrapers failed: {e}")
            custom_articles = []
        logger.info(f"Fetched {len(newsapi_articles)} NewsAPI, {len(gnews_articles)} GNews, {len(rss_articles)} RSS and {len(custom_articles)} custom scraper articles.")
        await message.edit_text(
            "📝 *الخطوة 2/4:* فلترة المقالات ذات الصلة...\n🔍 يتم الآن تطبيق فلاتر الاستراتيجية والقيادة والتعلم والتطوير...",
            parse_mode='Markdown'
        )

        filtered_newsapi = filter_relevant_articles(newsapi_articles) or []
        filtered_gnews = filter_relevant_articles(gnews_articles) or []
        filtered_rss = filter_relevant_articles(rss_articles) or []
        filtered_custom = filter_relevant_articles(custom_articles) or []
        recent_newsapi = filter_recent_articles(filtered_newsapi, days=7) or []
        recent_gnews = filter_recent_articles(filtered_gnews, days=7) or []
        recent_rss = filter_recent_articles(filtered_rss, days=7) or []
        recent_custom = filter_recent_articles(filtered_custom, days=7) or []

        all_articles = recent_newsapi + recent_gnews + recent_rss + recent_custom

        # Fallback: if recency filter returned nothing, use the filtered articles directly
        if not all_articles:
            logger.warning("No articles within 60 days — falling back to filtered articles regardless of date")
            all_articles = (filtered_newsapi[:5] + filtered_gnews[:5] +
                            filtered_rss[:25] + filtered_custom[:5])

        logger.info(f"Total relevant articles: {len(all_articles)}")
        
        if not all_articles:
            await message.edit_text(
                "❌ لم يتم العثور على مقالات حديثة كافية في مجال الاستراتيجية والقيادة والتعلم والتطوير. يرجى المحاولة لاحقًا.",
                parse_mode='Markdown'
            )
            return
        
        await message.edit_text(
            f"📝 *الخطوة 3/4:* استخراج المحتوى الكامل...\n📖 جاري معالجة {min(len(all_articles), 10)} مقالات من المصادر المتخصصة\n⏱️ قد يستغرق هذا من 2–3 دقائق...",
            parse_mode='Markdown'
        )
        
        enhanced_articles = enhance_articles_with_content(all_articles, max_articles=50, weekly_mode=True) or []
        enhanced_count = len([a for a in enhanced_articles if a.get('full_content')])
        logger.info(f"Enhanced articles: {enhanced_count}/{len(enhanced_articles)}")
        
        await message.edit_text(
            "📝 *الخطوة 4/6:* توليد تقارير أسبوعية باستخدام الذكاء الاصطناعي...\\n✍️ يتم الآن إنشاء تحليلات أسبوعية شاملة للاستراتيجية والقيادة والتعلم والتطوير...",
            parse_mode='Markdown'
        )
        
        user_keywords = get_user_keywords(context)
        categorized = categorize_articles(enhanced_articles)
        strategy_articles = categorized.get('Corporate Strategy & Leadership', []) or []
        ld_articles = categorized.get('L&D & Talent Development', []) or []
        
        logger.info(f"Corporate Strategy & Leadership blog articles: {len(strategy_articles)}, L&D & Talent Development blog articles: {len(ld_articles)}")
        
        # Generate Corporate Strategy & Leadership Blog
        strategy_blog = None
        if strategy_articles:
            strategy_blog = generate_quality_blog_with_ai(
                strategy_articles, "management", "weekly", keywords=user_keywords
            )
        
        # Generate L&D & Talent Development Blog
        ld_blog = None
        if ld_articles:
            ld_blog = generate_quality_blog_with_ai(
                ld_articles, "improvement", "weekly", keywords=user_keywords
            )
        
        # Step 5: Create PDFs
        await message.edit_text(
            "📝 *الخطوة 5/6:* إنشاء ملفات PDF احترافية...\\n📄 يتم الآن تنسيق تقارير الاستراتيجية والقيادة والتعلم والتطوير الأسبوعية...",
            parse_mode='Markdown'
        )
        
        strategy_filename = None
        ld_filename = None
        
        if strategy_blog:
            strategy_filename = create_quality_blog_pdf(
                strategy_blog,
                "التقرير الأسبوعي للاستراتيجية المؤسسية والقيادة",
                is_temp_file=True
            )
        
        if ld_blog:
            ld_filename = create_quality_blog_pdf(
                ld_blog,
                "التقرير الأسبوعي للتعلم والتطوير وتنمية المواهب",
                is_temp_file=True
            )
        
        # Step 6: Send the blog PDFs
        await message.edit_text(
            "📝 *الخطوة 6/6:* إرسال ملفات PDF...\\n📤 يتم الآن إرسال الرؤى والتحليلات الأسبوعية للاستراتيجية والقيادة والتعلم والتطوير...",
            parse_mode='Markdown'
        )
        
        if strategy_filename:
            try:
                with open(strategy_filename, 'rb') as pdf_file:
                    await message.reply_document(
                        document=pdf_file,
                        filename=f"Corporate_Strategy_Weekly_{datetime.now().strftime('%Y%m%d')}.pdf",
                        caption="📝 **التقرير الأسبوعي للاستراتيجية المؤسسية والقيادة**\\n💼 تحليل شامل لاتجاهات الاستراتيجية والقيادة ورؤى السوق",
                        parse_mode='Markdown'
                    )
                os.unlink(strategy_filename)
            except Exception as e:
                logger.error(f"Error sending strategy PDF: {e}")
        
        if ld_filename:
            try:
                with open(ld_filename, 'rb') as pdf_file:
                    await message.reply_document(
                        document=pdf_file,
                        filename=f"LD_Talent_Weekly_{datetime.now().strftime('%Y%m%d')}.pdf",
                        caption="📝 **التقرير الأسبوعي للتعلم والتطوير وتنمية المواهب**\\n⭐ تحليل شامل لاتجاهات التعلم والتطوير وتنمية المواهب",
                        parse_mode='Markdown'
                    )
                os.unlink(ld_filename)
            except Exception as e:
                logger.error(f"Error sending L&D PDF: {e}")
        
        # Success message with statistics
        strategy_status = "Generated" if strategy_blog else "Skipped (insufficient data)"
        ld_status = "Generated" if ld_blog else "Skipped (insufficient data)"
        
        success_message = f"""
 ✅ **تم الانتهاء من توليد التقارير الأسبوعية للاستراتيجية المؤسسية والتعلم والتطوير بنجاح!**

 📊 **إحصائيات المعالجة:**
 • إجمالي المقالات التي تم تحليلها: {len(enhanced_articles)}
 • نجاح استخراج المحتوى الكامل: {enhanced_count}/{len(enhanced_articles)} ({(enhanced_count/len(enhanced_articles)*100) if enhanced_articles else 0:.1f}%)
 • عدد المقالات في تقرير الاستراتيجية والقيادة: {len(strategy_articles)}
 • عدد المقالات في تقرير التعلم والتطوير: {len(ld_articles)}
 • نطاق التغطية الأسبوعية: {(datetime.now() - timedelta(days=7)).strftime('%B %d')} - {datetime.now().strftime('%B %d, %Y')}

 📝 **التقارير التي تم توليدها:**
 • التقرير الأسبوعي للاستراتيجية المؤسسية والقيادة - {strategy_status}
 • التقرير الأسبوعي للتعلم والتطوير وتنمية المواهب - {ld_status}

 كلا التقريرين يحتويان على أقسام منظمة وتحليل متعمق وتنسيق احترافي!
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 توليد تقارير أسبوعية جديدة", callback_data='generate_weekly')],
            [InlineKeyboardButton("📰 الأخبار اليومية", callback_data='get_news')],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.edit_text(
            success_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        error_message = f"❌ حدث خطأ أثناء توليد المدونات الأسبوعية: {str(e)}"
        logger.error(f"Weekly blog generation error: {str(e)}")
        await message.edit_text(error_message)

async def weekly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /weekly command directly."""
    await generate_weekly_blogs(update, context)

async def generate_monthly_blogs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate comprehensive monthly Quality and Excellence blog posts."""
    user_id = get_user_id(update)
    
    # Check usage limit
    has_limit, current_usage = check_usage_limit(user_id, 'monthly')
    if not has_limit:
        limit_message = (
            f"❌ *تم الوصول إلى الحد الأقصى*\n\n"
            f"لقد استخدمت جميع المحاولات المتاحة للتقارير الشهرية ({USAGE_LIMITS['monthly']}/{USAGE_LIMITS['monthly']}).\n\n"
            f"استخدم الأمر `/reset` لإعادة تعيين المحاولات (يتطلب صلاحيات المسؤول)."
        )
        if update.callback_query:
            await update.callback_query.answer("تم الوصول إلى الحد الأقصى", show_alert=True)
            await update.callback_query.message.reply_text(limit_message, parse_mode='Markdown')
        else:
            await update.message.reply_text(limit_message, parse_mode='Markdown')
        return
    
    # Increment usage
    increment_usage(user_id, 'monthly')
    
    if update.callback_query:
        await update.callback_query.answer()
        message = await update.callback_query.message.reply_text(
            "📝 *مولّد التقارير الشهرية للاستراتيجية المؤسسية والقيادة والتعلم والتطوير*\n\n⏳ جارٍ إعداد تحليل شهري شامل...\n📊 سيتم تحليل أحدث المقالات من HBR وMcKinsey وATD وForbes لآخر 30 يومًا\n⏰ الزمن المتوقع: 5–10 دقائق\n\nيرجى الانتظار...",
            parse_mode='Markdown'
        )
    else:
        message = await update.message.reply_text(
            "📝 *مولّد التقارير الشهرية للاستراتيجية المؤسسية والقيادة والتعلم والتطوير*\n\n⏳ جارٍ إعداد تحليل شهري شامل...\n📊 سيتم تحليل أحدث المقالات من HBR وMcKinsey وATD وForbes لآخر 30 يومًا\n⏰ الزمن المتوقع: 5–10 دقائق\n\nيرجى الانتظار...",
            parse_mode='Markdown'
        )
    
    try:
        await message.edit_text(
            "📝 *الخطوة 1/4:* جلب أخبار الاستراتيجية المؤسسية والقيادة والتعلم والتطوير الشهرية...\n📡 يتم الآن جمع المقالات من HBR وMcKinsey وATD وForbes من آخر 30 يومًا...",
            parse_mode='Markdown'
        )
        
        newsapi_articles = [] # fetch_monthly_quality_news() or []
        gnews_articles = [] # fetch_gnews_quality() or []
        rss_articles = fetch_rss_quality() or []
        try:
            custom_articles = await fetch_all_custom_scrapers(max_articles_per_source=50)
        except Exception as e:
            logger.warning(f"Custom scrapers failed: {e}")
            custom_articles = []
        logger.info(f"Fetched {len(newsapi_articles)} NewsAPI, {len(gnews_articles)} GNews, {len(rss_articles)} RSS and {len(custom_articles)} custom scraper articles.")

        await message.edit_text(
            "📝 *الخطوة 2/4:* فلترة المقالات ذات الصلة...\n🔍 يتم الآن تطبيق فلاتر الاستراتيجية والقيادة والتعلم والتطوير...",
            parse_mode='Markdown'
        )

        filtered_newsapi = filter_relevant_articles(newsapi_articles) or []
        filtered_gnews = filter_relevant_articles(gnews_articles) or []
        filtered_rss = filter_relevant_articles(rss_articles) or []
        filtered_custom = filter_relevant_articles(custom_articles) or []
        recent_newsapi = filter_recent_articles(filtered_newsapi, days=30) or []
        recent_gnews = filter_recent_articles(filtered_gnews, days=30) or []
        recent_rss = filter_recent_articles(filtered_rss, days=30) or []
        recent_custom = filter_recent_articles(filtered_custom, days=30) or []

        all_articles = recent_newsapi + recent_gnews + recent_rss + recent_custom

        # Fallback: if recency filter returned nothing, use the filtered articles directly
        if not all_articles:
            logger.warning("No articles within 60 days — falling back to filtered articles regardless of date")
            all_articles = (filtered_newsapi[:5] + filtered_gnews[:5] +
                            filtered_rss[:25] + filtered_custom[:5])

        logger.info(f"Total relevant articles: {len(all_articles)}")
        
        if not all_articles:
            await message.edit_text(
                "❌ لم يتم العثور على مقالات حديثة كافية في مجال الاستراتيجية والقيادة والتعلم والتطوير. يرجى المحاولة لاحقًا.",
                parse_mode='Markdown'
            )
            return
        
        await message.edit_text(
            f"📝 *الخطوة 3/4:* استخراج المحتوى الكامل...\n📖 جاري معالجة {min(len(all_articles), 10)} مقالات تقريبًا\n⏱️ قد يستغرق هذا من 5–8 دقائق...",
            parse_mode='Markdown'
        )
        
        enhanced_articles = enhance_articles_with_content(all_articles, max_articles=50, monthly_mode=True) or []
        enhanced_count = len([a for a in enhanced_articles if a.get('full_content')])
        logger.info(f"Enhanced articles: {enhanced_count}/{len(enhanced_articles)}")
        
        await message.edit_text(
            "📝 *الخطوة 4/6:* توليد تدوينات شهرية باستخدام الذكاء الاصطناعي...\\n✍️ يتم الآن إنشاء تحليلات شهرية شاملة...",
            parse_mode='Markdown'
        )
        
        user_keywords = get_user_keywords(context)
        categorized = categorize_articles(enhanced_articles)
        strategy_articles = categorized.get('Corporate Strategy & Leadership', []) or []
        ld_articles = categorized.get('L&D & Talent Development', []) or []
        
        logger.info(f"Corporate Strategy & Leadership blog articles: {len(strategy_articles)}, L&D & Talent Development blog articles: {len(ld_articles)}")
        
        # Generate Corporate Strategy & Leadership Blog
        strategy_blog = None
        if strategy_articles:
            strategy_blog = generate_quality_blog_with_ai(
                strategy_articles, "management", "monthly", keywords=user_keywords
            )
        
        # Generate L&D & Talent Development Blog
        ld_blog = None
        if ld_articles:
            ld_blog = generate_quality_blog_with_ai(
                ld_articles, "improvement", "monthly", keywords=user_keywords
            )
        
        # Step 5: Create PDFs
        await message.edit_text(
            "📝 *الخطوة 5/6:* إنشاء ملفات PDF احترافية...\\n📄 يتم الآن تنسيق التدوينات...",
            parse_mode='Markdown'
        )
        
        strategy_filename = None
        ld_filename = None
        
        if strategy_blog:
            strategy_filename = create_quality_blog_pdf(
                strategy_blog,
                "التقرير الشهري للاستراتيجية المؤسسية والقيادة",
                is_temp_file=True
            )
        
        if ld_blog:
            ld_filename = create_quality_blog_pdf(
                ld_blog,
                "التقرير الشهري للتعلم والتطوير وتنمية المواهب",
                is_temp_file=True
            )
        
        #  Step 6: Send the blog PDFs
        await message.edit_text(
            "📝 *الخطوة 6/6:* إرسال ملفات PDF...\\n📤 يتم الآن إرسال الرؤى والتحليلات الشهرية للاستراتيجية والقيادة والتعلم والتطوير...",
            parse_mode='Markdown'
        )
        
        if strategy_filename:
            try:
                with open(strategy_filename, 'rb') as pdf_file:
                    await message.reply_document(
                        document=pdf_file,
                        filename=f"Corporate_Strategy_Monthly_{datetime.now().strftime('%Y%m%d')}.pdf",
                        caption="📝 **التقرير الشهري للاستراتيجية المؤسسية والقيادة**\\n💼 تحليل شهري شامل لاتجاهات الاستراتيجية والقيادة ورؤى السوق",
                        parse_mode='Markdown'
                    )
                os.unlink(strategy_filename)
            except Exception as e:
                logger.error(f"Error sending strategy PDF: {e}")
        
        if ld_filename:
            try:
                with open(ld_filename, 'rb') as pdf_file:
                    await message.reply_document(
                        document=pdf_file,
                        filename=f"LD_Talent_Monthly_{datetime.now().strftime('%Y%m%d')}.pdf",
                        caption="📝 **التقرير الشهري للتعلم والتطوير وتنمية المواهب**\\n⭐ تحليل شهري شامل لاتجاهات التعلم والتطوير وتنمية المواهب",
                        parse_mode='Markdown'
                    )
                os.unlink(ld_filename)
            except Exception as e:
                logger.error(f"Error sending L&D PDF: {e}")
        
        # Success message with statistics
        strategy_status = "Generated" if strategy_blog else "Skipped (insufficient data)"
        ld_status = "Generated" if ld_blog else "Skipped (insufficient data)"
        
        success_message = f"""
 ✅ **تم الانتهاء من توليد التقارير الشهرية للاستراتيجية المؤسسية والتعلم والتطوير بنجاح!**

 📊 **إحصائيات المعالجة:**
 • إجمالي المقالات التي تم تحليلها: {len(enhanced_articles)}
 • نجاح استخراج المحتوى الكامل: {enhanced_count}/{len(enhanced_articles)} ({(enhanced_count/len(enhanced_articles)*100) if enhanced_articles else 0:.1f}%)
 • عدد المقالات في تقرير الاستراتيجية والقيادة: {len(strategy_articles)}
 • عدد المقالات في تقرير التعلم والتطوير: {len(ld_articles)}
 • نطاق التغطية الشهرية: {(datetime.now() - timedelta(days=30)).strftime('%B %d')} - {datetime.now().strftime('%B %d, %Y')}

 📝 **التقارير التي تم توليدها:**
 • التقرير الشهري للاستراتيجية المؤسسية والقيادة - {strategy_status}
 • التقرير الشهري للتعلم والتطوير وتنمية المواهب - {ld_status}

 كلا التقريرين يحتويان على أقسام منظمة وتحليل متعمق وتنسيق احترافي!
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 توليد تقارير شهرية جديدة", callback_data='generate_monthly')],
            [InlineKeyboardButton("📰 الأخبار اليومية", callback_data='get_news')],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.edit_text(
            success_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        error_message = f"❌ حدث خطأ أثناء توليد المدونات الشهرية: {str(e)}"
        logger.error(f"Monthly blog generation error: {str(e)}")
        await message.edit_text(error_message)

async def monthly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /monthly command directly."""
    await generate_monthly_blogs(update, context)

# ============================================================================
# AI MAGAZINE FEATURE
# ============================================================================

def generate_magazine_content_with_ai(articles):
    """
    Generate structured JSON content for the monthly magazine using Claude.
    """
    if not articles:
        return None

    # Prepare article context
    articles_context = ""
    for i, article in enumerate(articles[:40]):  # Limit to 40 articles for context
        title = article.get('title', 'No title')
        content = article.get('full_content', '')[:1000] # Truncate for token limits
        articles_context += f"Article {i+1}: {title}\nContent: {content}\n\n"

    system_message = (
        "You are the Editor-in-Chief of 'Corporate Strategy & L&D Monthly Report', a professional monthly magazine. "
        "Your goal is to maintain a professional, insightful, and visionary tone covering Corporate Strategy, Leadership, and Learning & Development. "
        "Critical page layout rule: Each article (including the first one) must fit exactly on one A4 page. "
        "NO EXCEPTIONS - All 8 articles must be between 220-250 words TOTAL (Lead + Main Content). "
        "Strict Enforcement: Count words for each article. If any article exceeds 250 words, it will overflow the page. "
        "If any article is under 200 words, it will have excessive whitespace. "
        "Target 230-240 words per article for optimal page fill without overflow. "
        "The first article is NOT special - it must follow the same word count rules as all other articles. "
        "Balance depth with brevity - provide comprehensive coverage but adhere to the strict 220-250 word limit. "
        "Output ONLY valid JSON matching the specified structure. "
        "All text must be in ENGLISH."
    )

    user_prompt = f"""
    Create content for this month's Corporate Strategy & L&D Magazine based on these articles:
    {articles_context}

    Return a JSON object with this EXACT structure (no markdown, just JSON):
    {{
        "title": "Corporate Strategy & L&D Report: [Catchy Title]",
        "subtitle": "[Engaging Subtitle]",
        "date": "[Current Month Year]",
        "highlights": [
            {{"title": "[Highlight 1]", "description": "[Short description]"}},
            {{"title": "[Highlight 2]", "description": "[Short description]"}},
            {{"title": "[Highlight 3]", "description": "[Short description]"}}
        ],
        "editors_note": "[Max 150 words. Visionary editorial commentary aimed to fit the page.]",
        "articles": [
            {{
                "category": "[One of: Strategy, Leadership, L&D, Talent, Technology]",
                "title": "[Catchy Magazine Title]",
                "location": "[Location/Region, e.g., New York / USA]",
                "lead": "[Compelling lead paragraph, 2 sentences (approx 30-40 words) that hooks the reader. This word count IS included in the 220-250 total.]",
                "content": "[Main content in HTML format with <h3> subheadings and <p> paragraphs. STRICT WORD COUNT: Total word count (Lead + This Content) MUST be exactly 220-250 words - no more, no less. Main content should be 190-210 words (Lead is 30-40). Create 2 sophisticated paragraphs (approx 80-90 words each) plus 1 subheading. DO NOT exceed 250 words total - this causes page overflow. DO NOT go under 220 words total. Target 235 total words for perfect page fill. This applies to ALL articles including the first one - NO EXCEPTIONS. Use proper HTML structure with <h3> for subheadings and <p> for paragraphs.]",
                "source": "[Original Source Name]",
                "score": "[Relevance Score 1-10]"
            }},
            ... (Generate exactly 8 featured articles. Do not exceed 8.)
        ]
    }}

    IMPORTANT: 
    1. Ensure all double quotes inside string values are properly escaped with backslash (\\").
    2. Do NOT use markdown line breaks or extra trailing commas that make JSON invalid.
    3. Output must be a single VALID JSON string.
    4. STRICT WORD COUNT ENFORCEMENT FOR ALL ARTICLES (NO EXCEPTIONS): 
       - Total word count for EACH article (Lead paragraph + Main content) MUST be between 220-250 words.
       - Minimum: 220 words.
       - Maximum: 250 words (Critical limit to prevent overflow).
       - Optimal Range: 230-240 words per article.
       - consistency is key.
    5. ALL TEXT MUST BE IN ENGLISH.
    """

    logger.info("Calling AWS Bedrock Claude API for magazine content generation...")
    content_text, error = call_claude_api(
        system_message=system_message, 
        user_message=user_prompt, 
        max_tokens=50000,
        temperature=0.7,
        use_long_timeout=True  # Use 600 second timeout for magazine generation
    )

    if error:
        logger.error(f"Magazine generation error (AWS Bedrock): {error}")
        logger.error(f"Error type: {type(error)}")
        return None

    if not content_text:
        logger.error("Magazine generation returned empty content")
        return None

    try:
        # Clean potential markdown fences
        json_str = content_text.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()
        
        # Log the length of the response for debugging
        logger.info(f"Magazine JSON response length: {len(json_str)} characters")
        
        # Check if the JSON appears to be truncated (unterminated string or brace)
        if not json_str.endswith('}'):
            logger.warning("JSON response appears to be truncated (doesn't end with })")
            logger.error(f"JSON string ending: ...{json_str[-200:]}")
            return None
        
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode magazine JSON: {e}")
        logger.error(f"JSON decode error at line {e.lineno}, column {e.colno}")
        logger.error(f"JSON string preview (first 500 chars):\n{json_str[:500]}")
        logger.error(f"JSON string ending (last 500 chars):\n...{json_str[-500:]}")
        logger.error(f"Full JSON length: {len(json_str)} characters")
        
        # Try to identify if this is a truncation issue
        if "Unterminated string" in str(e) or "Expecting" in str(e):
            logger.error("⚠️ This appears to be a truncated response. The model may have hit the max_tokens limit.")
            logger.error("   Possible solutions:")
            logger.error("   1. Reduce the number of articles in the magazine (currently 8)")
            logger.error("   2. Simplify the article content requirements")
            logger.error("   3. Split magazine generation into multiple API calls")
        
        return None

def render_newspaper_pdf(content_data, output_filename="newspaper.pdf"):
    """
    Render newspaper-style PDF using Jinja2 and WeasyPrint.
    """
    if not WEASYPRINT_AVAILABLE:
        logger.error("WeasyPrint not available (missing GTK or module). Cannot generate PDF.")
        return None

    try:
        # Setup Jinja2
        template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('newspaper.html')
        
        # Inject default images if available
        import glob
        import random
        import pathlib
        
        images_dir = os.path.join(template_dir, 'images')
        available_images = []
        if os.path.exists(images_dir):
            all_images = (
                glob.glob(os.path.join(images_dir, '*.jpg')) +
                glob.glob(os.path.join(images_dir, '*.png')) +
                glob.glob(os.path.join(images_dir, '*.jpeg')) +
                glob.glob(os.path.join(images_dir, '*.webp'))
            )
            # Filter out cover images
            exclude_files = ['Cover.png', 'cover.png', 'cover_generated.png', 'back_cover_generated.png', 'Back Cover.png', 'Back Cover.jpg', 'back cover.png', '1767655448098.jpg','Logo.jpg']
            available_images = [
                img for img in all_images 
                if os.path.basename(img) not in exclude_files
            ]
        
        # Assign images to articles (round-robin or random)
        articles = content_data.get('articles', [])
        for article in articles:
            if available_images and not article.get('local_image_path') and not article.get('image_url'):
                # Convert to file URI safely handling spaces/OS specifics
                img_path = random.choice(available_images)
                article['local_image_path'] = pathlib.Path(img_path).as_uri()
        
        # Batch articles into pages (2 articles per page)
        pages = []
        page_num = 1
        for i in range(0, len(articles), 2):
            page_articles = articles[i:i+2]
            pages.append({
                'page_num': page_num,
                'articles': page_articles
            })
            page_num += 1
        
        # Prepare template data
        template_data = {
            'title': content_data.get('title', 'Corporate Strategy & L&D'),
            'publication_name': content_data.get('publication_name', 'Corporate Strategy & L&D'),
            'tagline': content_data.get('tagline', 'مجلة إلكترونية تعنى بالاستراتيجية المؤسسية والقيادة وتطوير المواهب'),
            'issue_number': content_data.get('issue_number', '190'),
            'pages': pages,
            'footer_text': content_data.get('footer_text', 'corporateld'),
            'contact_phone': content_data.get('contact_phone', '00973 3701 4477'),
            'editors_note': content_data.get('editors_note', ''),
            'cover_image_path': content_data.get('cover_image_path')
        }

        # Optional cover image (look in templates/images)
        # Try Cover.png first, then fallback to other cover images
        cover_path = os.path.join(template_dir, 'images', 'Cover.png')
        if not os.path.exists(cover_path):
            cover_path = os.path.join(template_dir, 'images', '1767655448098.jpg')
        if not os.path.exists(cover_path):
            cover_path = os.path.join(template_dir, 'images', 'cover.png')
        
        if os.path.exists(cover_path):
            template_data['cover_image_path'] = pathlib.Path(cover_path).as_uri()
            logger.info(f"Using cover image: {cover_path}")
        elif content_data.get('cover_image_path'):
            template_data['cover_image_path'] = content_data.get('cover_image_path')
            logger.info(f"Using cover image from content_data")
        else:
            logger.warning("No cover image found")
        
        # Optional back cover image
        back_cover_path = os.path.join(template_dir, 'images', 'Back Cover.png')
        if not os.path.exists(back_cover_path):
            back_cover_path = os.path.join(template_dir, 'images', 'back_cover_generated.png')
        if not os.path.exists(back_cover_path):
            back_cover_path = os.path.join(template_dir, 'images', 'Back Cover.jpg')
        
        if os.path.exists(back_cover_path):
            template_data['back_cover_image_path'] = pathlib.Path(back_cover_path).as_uri()
            logger.info(f"Using back cover image: {back_cover_path}")
        elif content_data.get('back_cover_path'):
            template_data['back_cover_image_path'] = content_data.get('back_cover_path')
            logger.info(f"Using back cover image from content_data")
        
        # Render HTML
        html_out = template.render(**template_data)
        
        # Convert to PDF
        css_path = os.path.join(template_dir, 'newspaper.css')
        HTML(string=html_out, base_url=template_dir).write_pdf(
            output_filename, 
            stylesheets=[CSS(css_path)]
        )
        return output_filename
    except Exception as e:
        logger.error(f"Newspaper PDF rendering error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def render_magazine_pdf(content_data, output_filename="magazine.pdf"):
    """
    Render PDF using Jinja2 and WeasyPrint.
    """
    if not WEASYPRINT_AVAILABLE:
        logger.error("WeasyPrint not available (missing GTK or module). Cannot generate PDF.")
        return None

    try:
        # Setup Jinja2
        template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('magazine.html')
        
        # Inject default images if available
        import glob
        import random
        import pathlib
        
        images_dir = os.path.join(template_dir, 'images')
        available_images = []
        if os.path.exists(images_dir):
            all_images = (
                glob.glob(os.path.join(images_dir, '*.jpg')) +
                glob.glob(os.path.join(images_dir, '*.png')) +
                glob.glob(os.path.join(images_dir, '*.jpeg')) +
                glob.glob(os.path.join(images_dir, '*.webp'))
            )
            # Filter out cover images and logo
            exclude_files = ['Cover.png', 'cover.png', 'cover_generated.png', 'back_cover_generated.png', 'Back Cover.png', 'Back Cover.jpg', 'back cover.png', '1767655448098.jpg', 'TransformiX logo .png', 'Logo.jpg', 'logo.png']
            available_images = [
                img for img in all_images 
                if os.path.basename(img) not in exclude_files
            ]
        
        # Assign images to articles (round-robin or random)
        if 'articles' in content_data:
            for article in content_data['articles']:
                if available_images:
                    # Convert to file URI safely handling spaces/OS specifics
                    img_path = random.choice(available_images)
                    article['local_image_path'] = pathlib.Path(img_path).as_uri()
        
        # Inject Cover Image and Logo
        # Priority: cover.png (User requested)
        cover_path = os.path.join(images_dir, 'cover.png')
        if not os.path.exists(cover_path):
             cover_path = os.path.join(images_dir, 'Cover.png')
        if not os.path.exists(cover_path):
             cover_path = os.path.join(images_dir, 'cover_generated.png')
            
        if os.path.exists(cover_path):
            content_data['cover_image_path'] = pathlib.Path(cover_path).as_uri()
            
        logo_path = os.path.join(images_dir, 'logo.png')
        if os.path.exists(logo_path):
            content_data['logo_path'] = pathlib.Path(logo_path).as_uri()

        # Inject Back Cover Image
        # Priority: Back Cover.png (User requested)
        back_cover_path = os.path.join(images_dir, 'Back Cover.png')
        if not os.path.exists(back_cover_path):
             back_cover_path = os.path.join(images_dir, 'back_cover_generated.png')
             
        if os.path.exists(back_cover_path):
            content_data['back_cover_path'] = pathlib.Path(back_cover_path).as_uri()

        # Render HTML
        html_out = template.render(**content_data)
        
        # Convert to PDF
        css_path = os.path.join(template_dir, 'magazine.css')
        HTML(string=html_out, base_url=template_dir).write_pdf(
            output_filename, 
            stylesheets=[CSS(css_path)]
        )
        return output_filename
    except Exception as e:
        logger.error(f"PDF rendering error: {e}")
        return None

def clean_deduplicate_articles(articles):
     # Simple helper if not already present
     seen = set()
     clean = []
     for a in articles:
         t = a.get('title')
         if t and t not in seen:
             seen.add(t)
             clean.append(a)
     return clean

async def generate_magazine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /magazine command."""
    user_id = get_user_id(update)
    
    # Check usage limit
    has_limit, current_usage = check_usage_limit(user_id, 'magazine')
    if not has_limit:
        limit_message = (
            f"❌ *تم الوصول إلى الحد الأقصى*\n\n"
            f"لقد استخدمت جميع المحاولات المتاحة للمجلة ({USAGE_LIMITS['magazine']}/{USAGE_LIMITS['magazine']}).\n\n"
            f"استخدم الأمر `/reset` لإعادة تعيين المحاولات (يتطلب صلاحيات المسؤول)."
        )
        if update.callback_query:
            await update.callback_query.answer("تم الوصول إلى الحد الأقصى", show_alert=True)
            await update.callback_query.message.reply_text(limit_message, parse_mode='Markdown')
        else:
            await update.message.reply_text(limit_message, parse_mode='Markdown')
        return
    
    # Increment usage
    increment_usage(user_id, 'magazine')
    
    # Send initial status
    if update.callback_query:
        await update.callback_query.answer()
        message = await update.callback_query.message.reply_text(
            "🎨 *مولد مجلة الجودة والتميز*\n\n⏳ جارٍ إعداد إصدار هذا الشهر...\n🔍 تحليل الاتجاهات الشهرية المتاحة...",
            parse_mode='Markdown'
        )
    else:
        message = await update.message.reply_text(
            "🎨 *مولد مجلة الجودة والتميز*\n\n⏳ جارٍ إعداد إصدار هذا الشهر...\n🔍 تحليل الاتجاهات الشهرية المتاحة...",
            parse_mode='Markdown'
        )

    try:
        # 1. Fetch Monthly News
        await message.edit_text("🎨 *المرحلة 1/3:* جمع المعلومات...", parse_mode='Markdown')

        newsapi_articles = [] # fetch_monthly_quality_news() or []
        gnews_articles = [] # fetch_gnews_quality() or []
        rss_articles = fetch_rss_quality() or []
        try:
            custom_articles = await fetch_all_custom_scrapers(max_articles_per_source=10)
        except Exception as e:
            logger.warning(f"Custom scrapers failed: {e}")
            custom_articles = []
        logger.info(f"Magazine: Fetched {len(newsapi_articles)} NewsAPI, {len(gnews_articles)} GNews, {len(rss_articles)} RSS and {len(custom_articles)} custom scraper articles.")

        # Filter relevant articles
        filtered_newsapi = filter_relevant_articles(newsapi_articles) or []
        filtered_gnews = filter_relevant_articles(gnews_articles) or []
        filtered_rss = filter_relevant_articles(rss_articles) or []
        filtered_custom = filter_relevant_articles(custom_articles) or []
        recent_newsapi = filter_recent_articles(filtered_newsapi, days=30) or []
        recent_gnews = filter_recent_articles(filtered_gnews, days=30) or []
        recent_rss = filter_recent_articles(filtered_rss, days=30) or []
        recent_custom = filter_recent_articles(filtered_custom, days=30) or []

        all_articles = clean_deduplicate_articles(recent_newsapi + recent_gnews + recent_rss + recent_custom)

        # Fallback: if recency filter returned nothing, use the filtered articles directly
        if not all_articles:
            logger.warning("Magazine: No articles within 60 days — falling back to filtered articles regardless of date")
            all_articles = clean_deduplicate_articles(
                filtered_newsapi[:5] + filtered_gnews[:5] + filtered_rss[:25] + filtered_custom[:5]
            )

        logger.info(f"Magazine: Total relevant articles after filtering: {len(all_articles)}")

        if not all_articles:
             await message.edit_text("❌ لم يتم العثور على بيانات كافية للمجلة.")
             return

        # Enhance top articles
        await message.edit_text("🎨 *المرحلة 2/3:* تنقية وتحسين المحتوى...", parse_mode='Markdown')
        enhanced_articles = enhance_articles_with_content(all_articles, max_articles=12, monthly_mode=True)
        enhanced_count = len([a for a in enhanced_articles if a.get('full_content')])
        logger.info(f"Magazine: Enhanced articles: {enhanced_count}/{len(enhanced_articles)}")

        # 2. Generate Content
        await message.edit_text("🎨 *المرحلة 3/3:* تصميم التخطيط وإنشاء PDF...", parse_mode='Markdown')
        magazine_data = generate_magazine_content_with_ai(enhanced_articles)
        
        if not magazine_data:
             await message.edit_text("❌ فشل في توليد محتوى المجلة عبر الذكاء الاصطناعي.")
             return

        # Add newspaper metadata (English)
        current_date = datetime.now()
        magazine_data['date'] = current_date.strftime("%B %Y")
        
        # Ensure all articles have location field (default if missing)
        for article in magazine_data.get('articles', []):
            if 'location' not in article or not article['location']:
                article['location'] = 'Global'

        # Fetch og:images from source article URLs and assign round-robin to magazine articles
        await message.edit_text("🎨 *المرحلة 3/3:* جلب الصور وتصميم PDF...", parse_mode='Markdown')
        try:
            source_images = fetch_images_for_articles(enhanced_articles, max_articles=20, timeout=4)
            if source_images and magazine_data.get('articles'):
                for i, article in enumerate(magazine_data['articles']):
                    article['image_url'] = source_images[i % len(source_images)]
                logger.info(f"Assigned {len(source_images)} images across {len(magazine_data['articles'])} magazine articles")
        except Exception as e:
            logger.warning(f"Image assignment failed: {e}")

        # 3. Render PDF using NEW MAGAZINE template
        filename = f"IBDL_Monthly_{datetime.now().strftime('%B_%Y')}.pdf"
        pdf_path = render_magazine_pdf(magazine_data, filename)
        
        if pdf_path and os.path.exists(pdf_path):
             await message.reply_document(
                document=open(pdf_path, 'rb'),
                filename=filename,
                caption=f"🎨 **Corporate Strategy & L&D Magazine - {datetime.now().strftime('%B %Y')}**\n\nEnjoy your premium monthly report!",
                parse_mode='Markdown'
            )
             # Optional: os.unlink(pdf_path) if running long term
        else:
             await message.edit_text("❌ فشل في إنشاء ملف PDF.")

    except Exception as e:
        logger.error(f"Magazine error: {e}")
        await message.edit_text(f"❌ خطأ: {str(e)}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset usage limits for users (admin only)."""
    user_id = get_user_id(update)
    
    # Check if user is admin
    if ADMIN_USER_IDS and user_id not in ADMIN_USER_IDS:
        await update.message.reply_text(
            "❌ *غير مصرح*\n\nهذا الأمر متاح للمسؤولين فقط.",
            parse_mode='Markdown'
        )
        return
    
    # Check if specific user ID provided
    if context.args and len(context.args) > 0:
        try:
            target_user_id = int(context.args[0])
            if reset_user_usage(target_user_id):
                await update.message.reply_text(
                    f"✅ تم إعادة تعيين المحاولات للمستخدم: {target_user_id}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ لم يتم العثور على المستخدم: {target_user_id}",
                    parse_mode='Markdown'
                )
        except ValueError:
            await update.message.reply_text(
                "❌ معرّف المستخدم غير صحيح. استخدم: `/reset [user_id]` أو `/reset all`",
                parse_mode='Markdown'
            )
    elif context.args and context.args[0].lower() == 'all':
        reset_user_usage()
        await update.message.reply_text(
            "✅ تم إعادة تعيين جميع المحاولات لجميع المستخدمين.",
            parse_mode='Markdown'
        )
    else:
        # Reset current user
        reset_user_usage(user_id)
        await update.message.reply_text(
            "✅ تم إعادة تعيين محاولاتك.",
            parse_mode='Markdown'
        )

async def usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current usage status."""
    user_id = get_user_id(update)
    status = get_usage_status(user_id)
    
    status_message = (
        "📊 *حالة الاستخدام الحالية*\n\n"
        f"📰 الأخبار اليومية: {status['daily_news']['used']}/{status['daily_news']['limit']}\n"
        f"📝 التقارير الأسبوعية: {status['weekly']['used']}/{status['weekly']['limit']}\n"
        f"📅 التقارير الشهرية: {status['monthly']['used']}/{status['monthly']['limit']}\n"
        f"🎨 المجلة: {status['magazine']['used']}/{status['magazine']['limit']}\n\n"
        f"استخدم `/reset` لإعادة تعيين المحاولات (للمسؤولين فقط)."
    )
    
    await update.message.reply_text(status_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
🌟 *مساعدة بوت الاستراتيجية المؤسسية والقيادة والتعلم والتطوير*

*🆕 المزايا المحسّنة:*
• 📖 **استخراج كامل للمقالات** – قراءة النص الكامل للمقالات وليس الوصف فقط  
• 🧠 **ملخصات أذكى** – تحليل يعتمد على المحتوى الكامل  
• 📝 **توليد تقارير أسبوعية وشهرية** – تقارير معمّقة عن الاستراتيجية والقيادة والتعلم والتطوير  
• 🎨 **توليد مجلة Corporate Strategy & L&D الشهرية** – مجلة PDF احترافية بالإنجليزية
• 🔍 **استخراج متعدد الأساليب** – استخدام newspaper3k و BeautifulSoup  
• 📊 **إحصائيات المحتوى** – عرض نسبة نجاح استخراج النصوص  
• 🎯 **فلترة موجهة للاستراتيجية والقيادة والتعلم والتطوير** – استبعاد الأخبار غير ذات الصلة

*الأوامر المتاحة:*
• `/start` – رسالة الترحيب والقائمة الرئيسية  
• `/news` – الحصول على أحدث أخبار الاستراتيجية والقيادة والتعلم والتطوير  
• `/categories` – تصفح الأخبار حسب التصنيف  
• `/weekly` – توليد تقارير أسبوعية شاملة  
• `/monthly` – توليد تقارير شهرية شاملة  
• `/magazine` – توليد مجلة Corporate Strategy & L&D الشهرية (PDF)
• `/keywords` – إعداد الكلمات المفتاحية الأساسية والثانوية (بالإنجليزية) لتحسين محركات البحث  
• `/help` – عرض رسالة المساعدة هذه

*مصادر المحتوى:*
• 📗 Harvard Business Review (HBR)
• 📘 McKinsey Insights
• 📙 Deloitte Insights
• 📕 Forbes Leadership & Strategy
• 📒 ATD (Association for Talent Development)
• 📓 Training Industry
• 👤 Josh Bersin | Donald H. Taylor | Lori Niles-Hofmann

*التصنيفات المتاحة:*
• 📊 الاستراتيجية المؤسسية والقيادة  
• 📚 التعلم والتطوير وتنمية المواهب  

*كيف يعمل الاستخراج المحسّن:*
1. 📡 جلب الأخبار من RSS وتغذيات المصادر المتخصصة  
2. 🔍 استخراج المحتوى الكامل من الروابط  
3. 📖 استخدام newspaper3k و BeautifulSoup  
4. 🧠 تطبيق فلترة موجهة للاستراتيجية والقيادة والتعلم والتطوير  
5. 📄 إنشاء تقارير تفصيلية وملفات PDF

استخدم `/news` للتحديثات اليومية، و`/weekly` للتقارير الأسبوعية، و`/monthly` للتقارير الشهرية، و`/magazine` للمجلة الشهرية الاحترافية.
    """
    
    # Handle both regular commands and callback queries
    if update.callback_query:
        await update.callback_query.message.reply_text(help_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = """
🌟 صباح الخير ! 👋

أنا **ستراتيجي** — محرر محتوى متخصص في الاستراتيجية المؤسسية والقيادة والتعلم والتطوير.
أتابع أحدث الرؤى والمستجدات من أبرز المصادر العالمية كـ HBR وMcKinsey وATD وForbes،
وألخّصها بأسلوب احترافي يحافظ على دقتها ومعناها،
لتصلك المعلومة واضحة، مختصرة، ومباشرة.

🤖 تنويه
أستخدم تقنيات الذكاء الاصطناعي للمساعدة في جمع المحتوى، تنظيمه، وتلخيصه.
المحتوى مخصص للمتابعة والاطلاع فقط، وليس بديلاً عن المصادر الرسمية أو القرارات المهنية.

✨ ماذا أقدّم لك؟

📰 أخبار الاستراتيجية المؤسسية والقيادة يوميًا
📚 رؤى التعلم والتطوير وتنمية المواهب
📊 تقارير أسبوعية وشهرية معمّقة
📰 مجلة Corporate Strategy & L&D الشهرية الاحترافية
⏱️ توفير وقت وجهد المتابعة اليومية

🎯 كيف يمكن الاستفادة مني؟
متابعة أحدث اتجاهات الاستراتيجية والقيادة يوميًا
مشاركة ملخصات الأخبار مع فريق العمل والإدارة
استخدام التقارير في الاجتماعات الاستراتيجية
فهم مستقبل العمل وتنمية المواهب بشكل أوضح
الاعتماد على محتوى جاهز بدون مجهود

📰 المجلة الشهرية للاستراتيجية المؤسسية والقيادة
📘 مجلة شهرية متكاملة باللغة الإنجليزية
📄 بصيغة PDF وجاهزة للاستخدام
🧭 تشمل:
أبرز أخبار الشهر في الاستراتيجية والقيادة
رؤى التعلم والتطوير وتنمية المواهب
اتجاهات مستقبل العمل
تقارير McKinsey وHBR وATD وForbes
مناسبة للإدارة التنفيذية، فرق HR، والمديرين.

🚀 كيف تستخدم ستراتيجي؟
اكتب الكلمة اللي تحتاجها، وأنا أقدّم لك المحتوى فورًا.
تم التطوير التقني بالاشتراك مع شركة ترانسفورمكس
    """

    
    keyboard = [
        [InlineKeyboardButton("📰 الملخص اليومي", callback_data='get_news')],
        [InlineKeyboardButton("📊 الملخص الأسبوعي", callback_data='generate_weekly'),
         InlineKeyboardButton("📅 الملخص الشهري", callback_data='generate_monthly')],
        [InlineKeyboardButton("📰 المجلة", callback_data='generate_magazine')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Handle both regular messages and callback queries
    if update.callback_query:
        await update.callback_query.message.reply_text(
            welcome_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

def main():
    """Start the enhanced Quality and Excellence bot."""
    # Create custom request with increased timeouts to handle slow connections
    request = HTTPXRequest(
        connect_timeout=30.0,   # 30 seconds to establish connection
        read_timeout=60.0,      # 60 seconds to read data
        write_timeout=60.0,     # 60 seconds to write data
        pool_timeout=30.0,      # 30 seconds to get connection from pool
    )
    
    # Create the Application with custom timeouts
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .request(request)
        .get_updates_request(request)
        .build()
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("news", get_news))
    application.add_handler(CommandHandler("categories", show_categories))
    application.add_handler(CommandHandler("weekly", weekly_command))  # Weekly blog command
    application.add_handler(CommandHandler("monthly", monthly_command))  # Monthly blog command
    application.add_handler(CommandHandler("magazine", generate_magazine))  # Magazine command
    application.add_handler(CommandHandler("keywords", keywords_command))
    application.add_handler(CommandHandler("setkeywords", keywords_command))
    application.add_handler(CommandHandler("reset", reset_command))  # Reset usage command
    application.add_handler(CommandHandler("usage", usage_command))  # Show usage status
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    print("⭐ Starting Enhanced Quality and Excellence News Bot...")
    print("📱 Bot is ready! Send /start to begin.")
    print("✨ Enhanced features:")
    print("   • 📖 Full article content extraction")
    print("   • 🧠 Quality and Excellence-specific filtering")
    print("   • 📝 Weekly & monthly blog generation")
    print("   • 📄 Enhanced reports with full content")
    print("   • 🔍 Multi-method content extraction")
    print("   • 📊 Content extraction statistics")
    print("   • ⚡ Smart categorization using full text")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
