#!/usr/bin/env python3
"""
Diagnostic script to test RSS feed URLs and identify working ones.
Run this to find the actual working URLs for your RSS feeds.
"""

import requests
import feedparser
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_rss_url(url, name):
    """Test a single RSS URL and return results."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    results = {
        'name': name,
        'url': url,
        'status': 'FAILED',
        'method': None,
        'articles': 0,
        'error': None
    }
    
    # Method 1: Direct feedparser (often works best)
    try:
        print(f"\n[Method 1] Testing direct feedparser.parse()...")
        parsed = feedparser.parse(url)
        
        if hasattr(parsed, 'entries') and len(parsed.entries) > 0:
            results['status'] = 'SUCCESS'
            results['method'] = 'direct feedparser'
            results['articles'] = len(parsed.entries)
            print(f"✅ SUCCESS! Found {len(parsed.entries)} articles")
            print(f"   Feed title: {parsed.feed.get('title', 'N/A')}")
            print(f"   Most recent: {parsed.entries[0].get('published', 'N/A') if parsed.entries else 'N/A'}")
            return results
        else:
            print(f"❌ No entries found via direct parse")
    except Exception as e:
        print(f"❌ Direct parse failed: {str(e)}")
        results['error'] = f"Direct parse: {str(e)}"
    
    # Method 2: Requests with headers
    try:
        print(f"\n[Method 2] Testing requests.get() with headers...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        
        if response.status_code == 200:
            parsed = feedparser.parse(response.content)
            if hasattr(parsed, 'entries') and len(parsed.entries) > 0:
                results['status'] = 'SUCCESS'
                results['method'] = 'requests with headers'
                results['articles'] = len(parsed.entries)
                print(f"✅ SUCCESS! Found {len(parsed.entries)} articles")
                return results
            else:
                print(f"⚠️ Got 200 but no entries")
        else:
            print(f"⚠️ HTTP {response.status_code}: {response.reason}")
            results['error'] = f"HTTP {response.status_code}"
    except Exception as e:
        print(f"❌ Requests failed: {str(e)}")
        if not results['error']:
            results['error'] = f"Requests: {str(e)}"
    
    return results

def main():
    print("\n" + "="*60)
    print("RSS FEED DIAGNOSTIC TOOL")
    print("="*60)
    print("\nThis tool will test multiple URLs for each RSS feed to find working ones.")
    print("Please wait while testing...\n")
    
    # Define all URLs to test
    test_urls = [
        # Harvard Business Review
        {"name": "HBR - Primary (feed)", "url": "https://hbr.org/feed"},
        {"name": "HBR - Fallback 1 (rss/)", "url": "https://hbr.org/feed/rss/"},
        {"name": "HBR - Fallback 2 (harvardbusiness)", "url": "https://feeds.hbr.org/harvardbusiness"},
        {"name": "HBR - Fallback 3 (rss/feed.xml)", "url": "https://hbr.org/feed/rss/feed.xml"},
        {"name": "HBR - Webinars", "url": "https://hbr.org/webinars/feed"},
        {"name": "HBR - Topic: Strategy", "url": "https://hbr.org/topic/strategy.rss"},
        {"name": "HBR - Topic: Leadership", "url": "https://hbr.org/topic/leadership.rss"},
        
        # Forbes Leadership
        {"name": "Forbes - Leadership Feed", "url": "https://www.forbes.com/leadership/feed/"},
        {"name": "Forbes - Main Feed", "url": "https://www.forbes.com/feed/"},
        {"name": "Forbes - Real-time Feed", "url": "https://www.forbes.com/real-time/feed2/"},
        {"name": "Forbes - Leadership RSS", "url": "https://www.forbes.com/leadership/feed/rss/"},
        
        # ATD (Association for Talent Development)
        {"name": "ATD - Primary (/rss)", "url": "https://www.td.org/rss"},
        {"name": "ATD - Fallback 1 (rss.xml)", "url": "https://www.td.org/rss.xml"},
        {"name": "ATD - Fallback 2 (/feed)", "url": "https://www.td.org/feed"},
        {"name": "ATD - ATD International", "url": "https://www.td.org/atd-international/feed"},
        {"name": "ATD - ATD Research", "url": "https://www.td.org/research/feed"},
        
        # Training Industry
        {"name": "Training Industry", "url": "https://trainingindustry.com/feed/"},
        
        # Josh Bersin
        {"name": "Josh Bersin", "url": "https://joshbersin.com/feed/"},
    ]
    
    # Test URLs sequentially (to avoid rate limiting)
    working_urls = []
    failed_urls = []
    
    for test in test_urls:
        # Add delay to avoid rate limiting
        if test_urls.index(test) > 0:
            time.sleep(2)
        
        result = test_rss_url(test['url'], test['name'])
        
        if result['status'] == 'SUCCESS':
            working_urls.append(result)
        else:
            failed_urls.append(result)
    
    # Summary
    print("\n\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    print(f"\n✅ WORKING URLS ({len(working_urls)}):")
    for url in working_urls:
        print(f"\n   • {url['name']}")
        print(f"     URL: {url['url']}")
        print(f"     Method: {url['method']}")
        print(f"     Articles: {url['articles']}")
    
    print(f"\n❌ FAILED URLS ({len(failed_urls)}):")
    for url in failed_urls:
        print(f"\n   • {url['name']}")
        print(f"     URL: {url['url']}")
        print(f"     Error: {url['error']}")
    
    # Recommendations
    print("\n\n" + "="*60)
    print("RECOMMENDATIONS FOR RSS_FEEDS CONFIGURATION")
    print("="*60)
    
    # Group working URLs by source
    hbr_working = [u for u in working_urls if 'HBR' in u['name']]
    forbes_working = [u for u in working_urls if 'Forbes' in u['name']]
    atd_working = [u for u in working_urls if 'ATD' in u['name']]
    
    print("\n📚 RECOMMENDED RSS_FEEDS CONFIGURATION:")
    print("""
RSS_FEEDS = [
    {
        "name": "Harvard Business Review",
        "urls": [
""" + "\n".join([f'            "{u["url"]}",  # {u["name"]}' for u in hbr_working[:3]]) + """
        ]
    },
    {
        "name": "Forbes Leadership",
        "urls": [
""" + "\n".join([f'            "{u["url"]}",  # {u["name"]}' for u in forbes_working[:3]]) + """
        ]
    },
    {
        "name": "ATD",
        "urls": [
""" + "\n".join([f'            "{u["url"]}",  # {u["name"]}' for u in atd_working[:2]]) + """
        ]
    },
    {
        "name": "Training Industry",
        "urls": [
            "https://trainingindustry.com/feed/"
        ]
    },
    {
        "name": "Josh Bersin",
        "urls": [
            "https://joshbersin.com/feed/"
        ]
    }
]
""")
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()