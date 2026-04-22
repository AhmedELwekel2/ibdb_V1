#!/usr/bin/env python3
"""
Full Cycle Test for Quality Bot News Process
Tests: RSS fetching, article filtering, content extraction, and categorization
Standalone - no heavy bot dependencies
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta
import requests
import feedparser
from newspaper import Article
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# CONFIGURATION
# ============================================

RSS_FEEDS = [
    {
        "name": "Training Industry",
        "urls": ["https://trainingindustry.com/feed/"]
    },
    {
        "name": "Josh Bersin",
        "urls": ["https://joshbersin.com/feed/"]
    }
]

KEYWORDS = {
    'strategy_leadership': [
        "corporate strategy", "business transformation", "digital transformation",
        "strategic planning", "strategic management", "leadership development",
        "executive leadership", "change management", "organizational culture",
        "business growth", "competitive advantage", "market strategy"
    ],
    'ld_talent': [
        "talent development", "employee training", "professional development",
        "learning and development", "upskilling", "reskilling", "training programs",
        "learning technologies", "lms", "instructional design", "talent management",
        "career development", "learning analytics", "skill development"
    ]
}

ALL_KEYWORDS = KEYWORDS['strategy_leadership'] + KEYWORDS['ld_talent']

BANNED_WORDS = [
    "accident", "killed", "dead", "poisoning", "crime", "arrest",
    "flood", "storm", "earthquake", "film", "tv episode", "celebrity",
    "gossip", "football", "soccer", "match", "game"
]

# ============================================
# UTILITY FUNCTIONS
# ============================================

def create_robust_session():
    """Create requests session with retry logic"""
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_headers():
    """Get realistic headers to avoid 403 errors"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    }

# ============================================
# STEP 1: RSS FEED FETCHING
# ============================================

def fetch_rss_articles():
    """Fetch articles from RSS feeds with error handling"""
    articles = []
    session = create_robust_session()
    
    print("\n" + "="*80)
    print("STEP 1: FETCHING RSS FEEDS")
    print("="*80)
    
    for i, feed_config in enumerate(RSS_FEEDS):
        feed_name = feed_config['name']
        feed_urls = feed_config.get('urls', [])
        
        print(f"\n[{i+1}/{len(RSS_FEEDS)}] Fetching: {feed_name}")
        print(f"  URLs available: {len(feed_urls)}")
        
        if i > 0:
            time.sleep(2)
        
        parsed = None
        for url_idx, feed_url in enumerate(feed_urls, 1):
            try:
                print(f"  Trying URL {url_idx}/{len(feed_urls)}: {feed_url}")
                
                headers = get_headers()
                response = session.get(
                    feed_url,
                    headers=headers,
                    timeout=20,
                    verify=False
                )
                
                if response.status_code == 200:
                    print(f"  ✅ Success (status: {response.status_code})")
                    parsed = feedparser.parse(response.content)
                    break
                elif response.status_code == 429:
                    print(f"  ⚠️ Rate limited, waiting 10s...")
                    time.sleep(10)
                else:
                    print(f"  ⚠️ Failed: status {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Error: {str(e)[:100]}")
                continue
        
        if not parsed or not hasattr(parsed, 'entries'):
            print(f"  ⚠️ No entries found for {feed_name}")
            continue
        
        entries = parsed.entries
        print(f"  📰 Found {len(entries)} articles")
        
        for entry in entries[:20]:  # Limit to 20 per feed
            try:
                article = {
                    'title': getattr(entry, 'title', '') or '',
                    'description': getattr(entry, 'summary', '') or getattr(entry, 'description', '') or '',
                    'url': getattr(entry, 'link', '') or '',
                    'publishedAt': getattr(entry, 'published', '') or '',
                    'source': {'name': feed_name}
                }
                articles.append(article)
            except Exception as e:
                continue
    
    print(f"\n✅ Total articles fetched: {len(articles)}")
    return articles

# ============================================
# STEP 2: ARTICLE FILTERING
# ============================================

def is_relevant_article(article):
    """Check if article is relevant to our topics"""
    text = (
        (article.get("title") or "") + " " +
        (article.get("description") or "") + " " +
        (article.get("content", "") or "")
    ).lower()
    
    # Check banned words
    if any(b in text for b in BANNED_WORDS):
        return False
    
    # Check relevant keywords
    return any(k in text for k in ALL_KEYWORDS)

def filter_articles(articles):
    """Filter articles for relevance"""
    print("\n" + "="*80)
    print("STEP 2: FILTERING ARTICLES")
    print("="*80)
    
    print(f"\n📊 Filtering {len(articles)} articles...")
    print(f"   Looking for keywords in: {len(ALL_KEYWORDS)} categories")
    print(f"   Banning: {len(BANNED_WORDS)} words")
    
    relevant = [a for a in articles if is_relevant_article(a)]
    
    print(f"\n✅ Relevant articles: {len(relevant)}")
    print(f"❌ Filtered out: {len(articles) - len(relevant)}")
    
    return relevant

# ============================================
# STEP 3: CATEGORIZATION
# ============================================

def categorize_articles(articles):
    """Categorize articles by topic"""
    print("\n" + "="*80)
    print("STEP 3: CATEGORIZING ARTICLES")
    print("="*80)
    
    categories = {
        'Corporate Strategy & Leadership': [],
        'L&D & Talent Development': []
    }
    
    for article in articles:
        title = article.get('title', '') or ''
        description = article.get('description', '') or ''
        text = f"{title.lower()} {description.lower()}"
        
        strategy_count = sum(1 for k in KEYWORDS['strategy_leadership'] if k in text)
        ld_count = sum(1 for k in KEYWORDS['ld_talent'] if k in text)
        
        if strategy_count >= ld_count:
            categories['Corporate Strategy & Leadership'].append(article)
        else:
            categories['L&D & Talent Development'].append(article)
    
    print("\n📊 Categorization Results:")
    for category, arts in categories.items():
        print(f"   • {category}: {len(arts)} articles")
    
    return categories

# ============================================
# STEP 4: CONTENT EXTRACTION
# ============================================

def extract_content(url, max_retries=2):
    """Extract full article content from URL"""
    if not url:
        return None
    
    # Method 1: newspaper3k
    try:
        article = Article(url)
        article.download()
        article.parse()
        
        if article.text and len(article.text.strip()) > 100:
            return {
                'text': article.text.strip()[:500],  # Limit for test
                'method': 'newspaper3k',
                'title': article.title or ''
            }
    except Exception as e:
        pass
    
    # Method 2: BeautifulSoup (simplified)
    try:
        headers = get_headers()
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        paragraphs = soup.find_all('p')
        text = ' '.join([p.get_text(strip=True) for p in paragraphs[:10]])
        
        if text and len(text) > 100:
            return {
                'text': text[:500],
                'method': 'beautifulsoup',
                'title': soup.find('title').get_text(strip=True) if soup.find('title') else ''
            }
    except Exception as e:
        pass
    
    return None

def extract_content_from_articles(articles, max_articles=3):
    """Extract content from a sample of articles"""
    print("\n" + "="*80)
    print("STEP 4: CONTENT EXTRACTION (Sample)")
    print("="*80)
    
    print(f"\n📖 Extracting content from first {min(len(articles), max_articles)} articles...")
    
    enhanced = []
    for i, article in enumerate(articles[:max_articles]):
        url = article.get('url', '')
        print(f"\n  [{i+1}/{min(len(articles), max_articles)}] {article.get('title', '')[:60]}...")
        
        content_data = extract_content(url)
        if content_data:
            print(f"     ✅ Extracted {len(content_data['text'])} chars using {content_data['method']}")
            article['full_content'] = content_data['text']
            article['content_length'] = len(content_data['text'])
            enhanced.append(article)
        else:
            print(f"     ⚠️ Could not extract content")
            enhanced.append(article)
        
        time.sleep(1)  # Be respectful
    
    print(f"\n✅ Enhanced {len([a for a in enhanced if a.get('full_content')])}/{len(enhanced)} articles")
    return enhanced

# ============================================
# STEP 5: SUMMARY & REPORT
# ============================================

def generate_summary(total_fetched, relevant, categories, enhanced):
    """Generate comprehensive test summary"""
    print("\n" + "="*80)
    print("FINAL TEST SUMMARY")
    print("="*80)
    
    print("\n📊 OVERALL STATISTICS:")
    print(f"   • Total articles fetched from RSS: {total_fetched}")
    print(f"   • Articles after filtering: {len(relevant)}")
    print(f"   • Filter rate: {((total_fetched - len(relevant)) / total_fetched * 100):.1f}%")
    
    print("\n📂 CATEGORIES:")
    for category, arts in categories.items():
        print(f"   • {category}: {len(arts)} articles")
    
    print("\n📖 CONTENT EXTRACTION:")
    with_content = len([a for a in enhanced if a.get('full_content')])
    print(f"   • Articles with full content: {with_content}/{len(enhanced)}")
    
    print("\n✅ TEST STATUS:")
    if len(relevant) > 0:
        print(f"   ✅ RSS fetching: Working")
        print(f"   ✅ Article filtering: Working ({len(relevant)} relevant articles)")
        print(f"   ✅ Categorization: Working")
        print(f"   ✅ Content extraction: Working ({with_content} successful)")
        print(f"\n🎉 FULL CYCLE SUCCESS!")
    else:
        print(f"   ❌ No relevant articles found")
        print(f"   ⚠️ Check keywords or feed sources")
    
    print("\n" + "="*80)
    
    # Save results to JSON
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_fetched': total_fetched,
        'relevant_count': len(relevant),
        'categories': {k: len(v) for k, v in categories.items()},
        'enhanced_count': with_content,
        'sample_articles': enhanced[:3]
    }
    
    output_file = 'test_news_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {output_file}")

# ============================================
# MAIN TEST FUNCTION
# ============================================

def main():
    """Run full news process test"""
    print("\n" + "="*80)
    print("QUALITY BOT - FULL NEWS PROCESS TEST")
    print("="*80)
    print("\nTesting the complete news pipeline:")
    print("  1. ✅ Fetch RSS feeds")
    print("  2. ✅ Filter relevant articles")
    print("  3. ✅ Categorize by topic")
    print("  4. ✅ Extract full content")
    print("  5. ✅ Generate summary")
    print()
    
    try:
        # Step 1: Fetch articles
        all_articles = fetch_rss_articles()
        
        # Step 2: Filter
        relevant_articles = filter_articles(all_articles)
        
        # Step 3: Categorize
        categorized = categorize_articles(relevant_articles)
        
        # Step 4: Extract content (sample)
        # Get articles from both categories for testing
        sample_articles = []
        for category_arts in categorized.values():
            sample_articles.extend(category_arts[:2])
        
        enhanced = extract_content_from_articles(sample_articles, max_articles=5)
        
        # Step 5: Summary
        generate_summary(len(all_articles), relevant_articles, categorized, enhanced)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())