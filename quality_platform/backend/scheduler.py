import os
import sys
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import SessionLocal
from models import Article

# Ensure project root (.. ) is on sys.path so we can import quality_bot module
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

os.environ.setdefault("AWS_BEARER_TOKEN_BEDROCK", "DUMMY_WEB_API_TOKEN")

from quality_bot.telegram_bot_quality_arabic import (  # type: ignore
    fetch_quality_news,
    fetch_rss_quality,
    fetch_eos_news,
    fetch_egac_news,
    filter_relevant_articles
)

logger = logging.getLogger(__name__)

def fetch_and_store_news():
    logger.info("Starting scheduled news fetch...")
    db = SessionLocal()
    try:
        # Fetch all sources
        api_articles = fetch_quality_news() or []
        rss_articles = fetch_rss_quality() or []
        eos_articles = fetch_eos_news() or []
        egac_articles = fetch_egac_news() or []

        all_articles = api_articles + rss_articles + eos_articles + egac_articles

        # Filter relevance natively
        filtered = filter_relevant_articles(all_articles)

        new_count = 0
        for article_data in filtered:
            url = article_data.get('url')
            if not url:
                continue
            
            # Check if exists
            existing = db.query(Article).filter(Article.url == url).first()
            if not existing:
                try:
                    pub_str = article_data.get('publishedAt')
                    pub_dt = None
                    if pub_str:
                        # try to parse dates loosely, or keep as none if failed
                        try:
                            # If it's pure ISO
                            if 'T' in pub_str:
                                pub_dt = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
                            else:
                                pub_dt = datetime.strptime(pub_str[:10], "%Y-%m-%d")
                        except Exception:
                            pass

                    # Extract the source name properly depending on the dictionary format
                    source_obj = article_data.get('source')
                    source_name = "مجهول"
                    if isinstance(source_obj, dict):
                        source_name = source_obj.get('name', 'مجهول')
                    elif isinstance(source_obj, str):
                        source_name = source_obj

                    new_article = Article(
                        title=article_data.get('title', ''),
                        description=article_data.get('description', ''),
                        url=url,
                        published_at=pub_dt,
                        source_name=source_name,
                        content=article_data.get('content', '')
                    )
                    db.add(new_article)
                    db.commit()
                    new_count += 1
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error saving article {url}: {e}")

        logger.info(f"Finished scheduled fetch. Added {new_count} new articles.")
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run every 6 hours
    scheduler.add_job(
        fetch_and_store_news,
        trigger=IntervalTrigger(hours=6),
        id="fetch_news_job",
        name="Fetch news every 6 hours",
        replace_existing=True,
    )
    scheduler.start()
    
    # Also attempt an initial run on startup, in the background
    scheduler.add_job(
        fetch_and_store_news,
        id="initial_fetch_job",
        replace_existing=True,
    )
    
    return scheduler
