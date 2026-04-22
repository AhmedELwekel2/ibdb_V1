"""
Apify-based scrapers for websites that are difficult to scrape with Playwright.
Apify provides ready-made actors that bypass anti-bot measures.
"""

import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import Apify client
try:
    from apify_client import ApifyClient
    APIFY_AVAILABLE = True
except ImportError:
    APIFY_AVAILABLE = False
    logger.warning("Apify client not installed. Install with: pip install apify-client")


def get_apify_client() -> Optional[ApifyClient]:
    """Get Apify client with API token from environment."""
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        logger.error("APIFY_API_TOKEN not found in environment variables")
        return None
    
    if not APIFY_AVAILABLE:
        logger.error("Apify client not installed")
        return None
    
    return ApifyClient(api_token)


def scrape_forbes_apify(max_articles: int = 10) -> List[Dict]:
    """
    Scrape Forbes articles using Apify's dedicated Forbes scraper.
    
    Uses: natasha.lekh/forbes-scraper
    - Dedicated Forbes scraper with better anti-bot handling
    - Extracts articles, monitors popularity
    - Can filter by authors, topics, categories, or publication dates
    
    Returns: List of article dictionaries
    """
    logger.info("🤖 Using Apify Forbes Scraper...")
    
    client = get_apify_client()
    if not client:
        logger.error("Cannot initialize Apify client")
        return []
    
    try:
        # Use dedicated Forbes scraper actor
        actor_input = {
            "startUrls": [
                {"url": "https://www.forbes.com/leadership/"},
                {"url": "https://www.forbes.com/business/"}
            ],
            "maxArticles": max_articles,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
        
        logger.info("   Starting Forbes scraper with natasha.lekh/forbes-scraper...")
        run = client.actor("natasha.lekh/forbes-scraper").call(run_input=actor_input)
        
        # Wait for run to complete and fetch results
        client.dataset(run["defaultDatasetId"]).iterate_items()
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        articles = []
        for item in items[:max_articles]:
            articles.append({
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'url': item.get('url', ''),
                'publishedAt': item.get('publishedAt', ''),
                'source': item.get('source', {'name': 'Forbes Leadership'}),
                'full_content': item.get('fullContent', '')
            })
        
        logger.info(f"✅ Apify scraped {len(articles)} Forbes articles")
        return articles
        
    except Exception as e:
        logger.error(f"❌ Apify Forbes scraper failed: {e}")
        return []


def scrape_mckinsey_apify(max_articles: int = 10) -> List[Dict]:
    """
    Scrape McKinsey articles using Apify.
    
    Returns: List of article dictionaries
    """
    logger.info("🤖 Using Apify to scrape McKinsey articles...")
    
    client = get_apify_client()
    if not client:
        logger.error("Cannot initialize Apify client")
        return []
    
    try:
        actor_input = {
            "startUrls": [
                {"url": "https://www.mckinsey.com/featured-insights"},
                {"url": "https://www.mckinsey.com/insights"}
            ],
            "maxCrawlPages": max_articles * 2,
            "maxDepth": 1,
            "pageFunction": """async function pageFunction({ request, page }) {
    const title = await page.locator('h1').first().textContent().catch(() => '');
    const ogTitle = await page.locator('meta[property="og:title"]').getAttribute('content').catch(() => '');
    const description = await page.locator('meta[property="og:description"]').getAttribute('content').catch(() => '');
    const metaDesc = await page.locator('meta[name="description"]').getAttribute('content').catch(() => '');
    const publishedAt = await page.locator('time').getAttribute('datetime').catch(() => '');
    const articlePub = await page.locator('meta[property="article:published_time"]').getAttribute('content').catch(() => '');
    const url = request.url;
    
    const content = await page.locator('article p').first().textContent().catch(() => '') || '';
    
    return {
        title: title || ogTitle || '',
        description: description || metaDesc || content.substring(0, 300),
        url,
        publishedAt: publishedAt || articlePub || '',
        source: { name: 'McKinsey Insights' },
        fullContent: content.substring(0, 500) + '...'
    };
}""",
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
        
        logger.info("   Starting Apify crawl with web-scraper...")
        run = client.actor("apify/web-scraper").call(run_input=actor_input)
        
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        articles = []
        for item in items[:max_articles]:
            articles.append({
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'url': item.get('url', ''),
                'publishedAt': item.get('publishedAt', ''),
                'source': item.get('source', {'name': 'McKinsey Insights'}),
                'full_content': item.get('fullContent', '')
            })
        
        logger.info(f"✅ Apify scraped {len(articles)} McKinsey articles")
        return articles
        
    except Exception as e:
        logger.error(f"❌ Apify McKinsey scraper failed: {e}")
        return []


def scrape_atd_apify(max_articles: int = 10) -> List[Dict]:
    """
    Scrape ATD articles using Apify.
    
    Returns: List of article dictionaries
    """
    logger.info("🤖 Using Apify to scrape ATD articles...")
    
    client = get_apify_client()
    if not client:
        logger.error("Cannot initialize Apify client")
        return []
    
    try:
        actor_input = {
            "startUrls": [
                {"url": "https://www.td.org/atd-blog"},
                {"url": "https://www.td.org/magazines/ttd/"}
            ],
            "maxCrawlPages": max_articles * 2,
            "maxDepth": 1,
            "pageFunction": """async function pageFunction({ request, page }) {
    const title = await page.locator('h1').first().textContent().catch(() => '');
    const ogTitle = await page.locator('meta[property="og:title"]').getAttribute('content').catch(() => '');
    const description = await page.locator('meta[property="og:description"]').getAttribute('content').catch(() => '');
    const metaDesc = await page.locator('meta[name="description"]').getAttribute('content').catch(() => '');
    const publishedAt = await page.locator('time').getAttribute('datetime').catch(() => '');
    const articlePub = await page.locator('meta[property="article:published_time"]').getAttribute('content').catch(() => '');
    const url = request.url;
    
    const content = await page.locator('article p').first().textContent().catch(() => '') || '';
    
    return {
        title: title || ogTitle || '',
        description: description || metaDesc || content.substring(0, 300),
        url,
        publishedAt: publishedAt || articlePub || '',
        source: { name: 'ATD' },
        fullContent: content.substring(0, 500) + '...'
    };
}""",
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
        
        logger.info("   Starting Apify crawl with web-scraper...")
        run = client.actor("apify/web-scraper").call(run_input=actor_input)
        
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        articles = []
        for item in items[:max_articles]:
            articles.append({
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'url': item.get('url', ''),
                'publishedAt': item.get('publishedAt', ''),
                'source': item.get('source', {'name': 'ATD'}),
                'full_content': item.get('fullContent', '')
            })
        
        logger.info(f"✅ Apify scraped {len(articles)} ATD articles")
        return articles
        
    except Exception as e:
        logger.error(f"❌ Apify ATD scraper failed: {e}")
        return []


async def fetch_all_apify_scrapers(max_articles_per_source: int = 10) -> Dict[str, List[Dict]]:
    """
    Fetch articles from all Apify scrapers.
    
    Returns: Dictionary with source names as keys and article lists as values
    """
    logger.info("="*80)
    logger.info("🤖 APIFY SCRAPERS - FETCHING ALL SOURCES")
    logger.info("="*80)
    
    results = {
        'Forbes': [],
        'McKinsey': [],
        'ATD': []
    }
    
    # Test Forbes
    logger.info("\nFetching Forbes via Apify...")
    results['Forbes'] = scrape_forbes_apify(max_articles_per_source)
    
    # Test McKinsey
    logger.info("\nFetching McKinsey via Apify...")
    results['McKinsey'] = scrape_mckinsey_apify(max_articles_per_source)
    
    # Test ATD
    logger.info("\nFetching ATD via Apify...")
    results['ATD'] = scrape_atd_apify(max_articles_per_source)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("📊 APIFY SCRAPERS SUMMARY")
    logger.info("="*80)
    
    for source, articles in results.items():
        status = "✅" if articles else "❌"
        logger.info(f"   {source:<15} {len(articles):3} articles  {status}")
    
    total = sum(len(articles) for articles in results.values())
    logger.info(f"\n   Total: {total} articles via Apify")
    logger.info("="*80)
    
    return results


if __name__ == "__main__":
    import asyncio
    results = asyncio.run(fetch_all_apify_scrapers(max_articles_per_source=5))
    print(f"\nTotal articles: {sum(len(v) for v in results.values())}")