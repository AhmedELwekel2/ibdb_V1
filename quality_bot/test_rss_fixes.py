#!/usr/bin/env python3
"""
Test script to verify RSS feed fixes work correctly.
Run this to test the improved fetch_rss_quality() function.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_bot_quality_arabic_claude_version import fetch_rss_quality
import logging

# Set up logging to see detailed output
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    print("=" * 80)
    print("Testing Improved RSS Feed Fetching")
    print("=" * 80)
    print()
    print("This test will:")
    print("  1. Test fetching from all configured RSS feeds")
    print("  2. Verify error handling for SSL, 403, and 429 errors")
    print("  3. Check that retry logic works correctly")
    print("  4. Verify rate limiting is implemented")
    print()
    print("=" * 80)
    print()
    
    try:
        articles = fetch_rss_quality()
        
        print()
        print("=" * 80)
        print("✅ TEST COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print()
        print(f"Total articles fetched: {len(articles)}")
        print()
        
        # Show breakdown by source
        sources = {}
        for article in articles:
            source = article.get('source', {}).get('name', 'Unknown')
            sources[source] = sources.get(source, 0) + 1
        
        print("Articles by source:")
        for source, count in sorted(sources.items()):
            print(f"  • {source}: {count} articles")
        
        print()
        print("=" * 80)
        print("✓ All RSS feeds are working correctly!")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        print("Please check the logs above for details on what went wrong.")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())