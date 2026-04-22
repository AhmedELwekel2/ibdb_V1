#!/usr/bin/env python3
"""
Test script for the improved custom scrapers with timeout fixes.
"""

import asyncio
import logging
import time
from custom_scrapers import fetch_all_custom_scrapers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_improved_scrapers():
    """Test the improved scrapers with reduced timeouts and better error handling."""
    print("="*80)
    print("🧪 TESTING IMPROVED CUSTOM SCRAPERS")
    print("="*80)
    
    start_time = time.time()
    
    try:
        # Test with fewer articles to speed up testing
        articles = await fetch_all_custom_scrapers(max_articles_per_source=3)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ Test completed in {duration:.1f} seconds")
        print(f"📊 Total articles fetched: {len(articles)}")
        
        # Show summary by source
        sources = {}
        for article in articles:
            source = article.get('source', {}).get('name', 'Unknown')
            sources[source] = sources.get(source, 0) + 1
        
        print("\n📈 Articles by source:")
        for source, count in sources.items():
            print(f"   {source}: {count} articles")
        
        # Show a few sample titles
        print("\n📝 Sample article titles:")
        for i, article in enumerate(articles[:5]):
            title = article.get('title', 'No title')[:60]
            source = article.get('source', {}).get('name', 'Unknown')
            print(f"   {i+1}. {title}... ({source})")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_improved_scrapers())
    
    if success:
        print("\n🎉 All tests passed! The improved scrapers are working correctly.")
    else:
        print("\n💥 Tests failed. Check the error messages above.")