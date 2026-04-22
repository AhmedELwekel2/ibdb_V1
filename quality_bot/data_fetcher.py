"""
Data fetching from RSS feeds, NewsAPI, GNews, and custom websites
"""
import requests
import logging
import feedparser
from config import RSS_FEEDS, NEWSAPI_KEY, GNEWS_API_KEY

logger = logging.getLogger(__name__)


def is_real_quality(article):
    """Filter to ensure articles are genuinely about Corporate Strategy, Leadership, and L&D"""
    text = (
        (article.get("title") or "") + " " +
        (article.get("description") or "") + " " +
        (article.get("content") or "")
    ).lower()

    professional_words = [
        "corporate strategy", "business transformation", "digital transformation", "organizational change",
        "strategic planning", "strategic management", "strategic decision-making", "corporate governance",
        "business growth", "business model innovation", "market strategy", "competitive advantage",
        "change management", "organizational culture", "executive leadership", "leadership development",
        "leadership trends", "leadership coaching", "executive coaching", "management theory",
        "leadership best practices", "organizational excellence", "organizational leadership",
        "executive strategy", "market trends", "future of work", "industry outlooks",
        "human capital trends", "strategic business insights", "market analysis",
        "talent development", "employee training", "professional development", "learning technologies",
        "upskilling", "reskilling", "learning and development", "training programs", "skill development",
        "hr development", "capability building", "workforce development", "talent development standards",
        "capability model", "learning management systems", "lms", "blended learning", "microlearning",
        "gamification", "mobile learning", "social learning", "learning experience design",
        "instructional design", "ai in l&d", "personalized learning", "data-driven l&d",
        "virtual reality", "talent management", "career development", "employee engagement",
        "performance improvement", "learning analytics", "global l&d trends", "business of learning"
    ]

    banned_words = [
        "accident", "killed", "dead", "poisoning", "food poisoning",
        "crime", "arrest", "flood", "storm", "earthquake",
        "film", "tv episode", "episode", "review", "movie",
        "celebrity", "gossip", "football", "soccer", "nfl", "nba", 
        "premier league", "match", "game", "championship"
    ]

    if any(b in text for b in banned_words):
        return False

    return any(w in text for w in professional_words)


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
        clean = [a for a in articles if is_real_quality(a)]
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
        clean = [a for a in articles if is_real_quality(a)]
        return clean
    except Exception as e:
        logger.error(f"Error fetching GNews articles: {e}")
        return []


def fetch_rss_quality():
    """Fetch Corporate Strategy, Leadership, and L&D news from configured RSS feeds."""
    articles = []
    for feed in RSS_FEEDS:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            try:
                response = requests.get(feed["url"], headers=headers, timeout=10)
                if response.status_code == 200:
                    parsed = feedparser.parse(response.content)
                else:
                    logger.warning(f"Failed to fetch {feed['name']} via requests: {response.status_code}, falling back to direct parse")
                    parsed = feedparser.parse(feed["url"])
            except Exception as req_err:
                logger.warning(f"Requests failed for {feed['name']}: {req_err}, falling back to direct parse")
                parsed = feedparser.parse(feed["url"])

            entries = parsed.entries if hasattr(parsed, 'entries') else []
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
                            from datetime import datetime
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
                        'source': {'name': feed['name']}
                    }
                    articles.append(article)
                except Exception as inner_e:
                    logger.warning(f"Error parsing RSS entry from {feed['name']}: {inner_e}")
                    continue
        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed['name']}: {e}")
            continue
    
    # Apply quality filter to RSS articles
    clean = [a for a in articles if is_real_quality(a)]
    return clean