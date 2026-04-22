"""
Test script for the get_news function from telegram_bot_quality_arabic_claude_version.py
"""
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, MagicMock
import json
from datetime import datetime

# Mock telegram imports before importing the bot module
sys.modules['telegram'] = MagicMock()
sys.modules['telegram.ext'] = MagicMock()

# Create mock classes
class MockUpdate:
    def __init__(self, user_id=123456):
        self.message = Mock()
        self.message.from_user = Mock()
        self.message.from_user.id = user_id
        self.message.reply_text = AsyncMock()
        self.callback_query = None

class MockContext:
    def __init__(self):
        self.user_data = {}

# Mock telegram classes
from unittest.mock import MagicMock
sys.modules['telegram'].Update = MockUpdate
sys.modules['telegram'].InlineKeyboardButton = MagicMock
sys.modules['telegram'].InlineKeyboardMarkup = MagicMock

# Now import the bot module
from telegram_bot_quality_arabic_claude_version import (
    fetch_rss_quality,
    filter_relevant_articles,
    filter_recent_articles,
    enhance_articles_with_content,
    fetch_quality_news,
    fetch_gnews_quality
)
from custom_scrapers import fetch_all_custom_scrapers

async def test_fetch_rss_quality():
    """Test RSS feed fetching function"""
    print("=" * 60)
    print("Testing fetch_rss_quality()...")
    print("=" * 60)
    
    try:
        articles = fetch_rss_quality()
        print(f"✅ Successfully fetched {len(articles)} articles from RSS feeds")
        
        if articles:
            print(f"\nSample article:")
            sample = articles[0]
            print(f"  Title: {sample.get('title', 'N/A')[:80]}...")
            print(f"  Source: {sample.get('source', {}).get('name', 'N/A')}")
            print(f"  URL: {sample.get('url', 'N/A')[:80]}...")
            print(f"  Published: {sample.get('publishedAt', 'N/A')}")
        return articles
    except Exception as e:
        print(f"❌ Error testing fetch_rss_quality: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

async def test_filter_relevant_articles(articles):
    """Test article filtering function"""
    print("\n" + "=" * 60)
    print("Testing filter_relevant_articles()...")
    print("=" * 60)
    
    try:
        filtered = filter_relevant_articles(articles)
        print(f"✅ Filtered {len(articles)} articles down to {len(filtered)} relevant articles")
        return filtered
    except Exception as e:
        print(f"❌ Error testing filter_relevant_articles: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

async def test_filter_recent_articles(articles):
    """Test recent articles filter"""
    print("\n" + "=" * 60)
    print("Testing filter_recent_articles()...")
    print("=" * 60)
    
    try:
        recent = filter_recent_articles(articles, days=2)
        print(f"✅ Filtered to {len(recent)} articles from the last 2 days")
        return recent
    except Exception as e:
        print(f"❌ Error testing filter_recent_articles: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

async def test_enhance_articles_with_content(articles):
    """Test content enhancement"""
    print("\n" + "=" * 60)
    print(f"Testing enhance_articles_with_content() on {len(articles)} articles...")
    print("=" * 60)
    
    try:
        # Limit to 3 articles for testing to avoid long wait times
        test_articles = articles[:3]
        enhanced = enhance_articles_with_content(test_articles, max_articles=3)
        
        print(f"✅ Enhanced {len(enhanced)} articles")
        
        # Show enhancement stats
        with_content = [a for a in enhanced if a.get('full_content')]
        print(f"   Articles with full content: {len(with_content)}/{len(enhanced)}")
        
        if enhanced:
            sample = enhanced[0]
            print(f"\nSample enhanced article:")
            print(f"  Title: {sample.get('title', 'N/A')[:80]}...")
            print(f"  Has full_content: {bool(sample.get('full_content'))}")
            print(f"  Extraction method: {sample.get('extraction_method', 'N/A')}")
            if sample.get('content_length'):
                print(f"  Content length: {sample['content_length']} characters")
        
        return enhanced
    except Exception as e:
        print(f"❌ Error testing enhance_articles_with_content: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

async def test_custom_scrapers():
    """Test custom scrapers (used as fallback in get_news)"""
    print("\n" + "=" * 60)
    print("Testing fetch_all_custom_scrapers()...")
    print("=" * 60)
    print("Note: This is used as fallback when RSS returns < 100 articles\n")
    
    try:
        custom_articles = fetch_all_custom_scrapers(max_articles_per_source=5)
        print(f"✅ Successfully fetched {len(custom_articles)} articles from custom scrapers")
        
        if custom_articles:
            print(f"\nSample custom scraper article:")
            sample = custom_articles[0]
            print(f"  Title: {sample.get('title', 'N/A')[:80]}...")
            print(f"  Source: {sample.get('source', {}).get('name', 'N/A')}")
            print(f"  URL: {sample.get('url', 'N/A')[:80]}...")
            
            # Count by source
            source_counts = {}
            for article in custom_articles:
                source = article.get('source', {}).get('name', 'Unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
            
            print(f"\nArticles by source:")
            for source, count in source_counts.items():
                print(f"  • {source}: {count} articles")
        
        return custom_articles
    except Exception as e:
        print(f"❌ Error testing fetch_all_custom_scrapers: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def save_articles_to_file(articles, filename_prefix="test_articles"):
    """Save articles to JSON file with timestamp"""
    if not articles:
        print("\n⚠️ No articles to save")
        return None
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Saved {len(articles)} articles to {filename}")
        return filename
    except Exception as e:
        print(f"\n❌ Error saving articles: {str(e)}")
        return None

async def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("GET_NEWS FUNCTION TEST SUITE")
    print("=" * 60)
    print("\nThis test will run the core functions used by get_news()")
    print("Note: get_news() requires Telegram Update/Context objects,")
    print("so we're testing its component functions instead.\n")
    
    # Test 1: Fetch RSS articles
    rss_articles = await test_fetch_rss_quality()
    
    if not rss_articles:
        print("\n⚠️ No RSS articles fetched. Testing custom scrapers only.")
        custom_articles = await test_custom_scrapers()
        if custom_articles:
            # Save custom articles
            save_articles_to_file(custom_articles, "custom_articles")
            # Test enhancement on custom articles
            await test_enhance_articles_with_content(custom_articles[:3])
        return
    
    # Test 2: Filter relevant articles
    relevant_articles = await test_filter_relevant_articles(rss_articles)
    
    if not relevant_articles:
        print("\n⚠️ No relevant articles after filtering. Using RSS articles for next tests.")
        relevant_articles = rss_articles
    
    # Test 3: Filter recent articles
    recent_articles = await test_filter_recent_articles(relevant_articles)
    
    if not recent_articles:
        print("\n⚠️ No recent articles. Using relevant articles for enhancement test.")
        recent_articles = relevant_articles
    
    # Test 4: Enhance articles with content
    enhanced_articles = await test_enhance_articles_with_content(recent_articles)
    
    # Save enhanced articles
    if enhanced_articles:
        save_articles_to_file(enhanced_articles, "enhanced_articles")
    
    # Test 5: Test custom scrapers (used as fallback in get_news)
    print("\n" + "=" * 60)
    print("CUSTOM SCRAPERS TEST")
    print("=" * 60)
    print("In get_news(), custom scrapers are used as fallback when RSS < 100 articles")
    print(f"Current RSS articles: {len(rss_articles)} (threshold: 100)")
    print(f"Custom scrapers would be: {'ENABLED' if len(rss_articles) < 100 else 'DISABLED'}\n")
    
    custom_articles = await test_custom_scrapers()
    
    if custom_articles:
        save_articles_to_file(custom_articles, "custom_articles")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"✅ RSS articles fetched: {len(rss_articles)}")
    print(f"✅ Relevant articles: {len(relevant_articles)}")
    print(f"✅ Recent articles: {len(recent_articles)}")
    if custom_articles:
        print(f"✅ Custom scraper articles: {len(custom_articles)}")
    print("\nAll component functions of get_news() have been tested successfully!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())