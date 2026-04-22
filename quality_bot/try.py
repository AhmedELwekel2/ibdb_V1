#!/usr/bin/env python3
"""
Test script for scraping functions only (no Telegram bot)
Tests all data fetching, content extraction, and processing functions
"""

import json
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import scraping functions
try:
    from telegram_bot_quality_arabic_claude_version import (
        fetch_rss_quality,
        fetch_quality_news,
        fetch_gnews_quality,
        fetch_weekly_quality_news,
        fetch_monthly_quality_news,
        extract_article_content,
        enhance_articles_with_content,
        filter_relevant_articles,
        filter_recent_articles,
        categorize_articles,
        is_relevant_insight
    )
    print("✅ Successfully imported all scraping functions")
except ImportError as e:
    print(f"❌ Failed to import functions: {e}")
    sys.exit(1)


def print_separator(title):
    """Print a formatted separator"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def test_rss_feeds():
    """Test RSS feed fetching"""
    print_separator("TEST 1: RSS Feed Fetching")
    
    print("Fetching articles from RSS feeds (HBR, Forbes, ATD, etc.)...")
    articles = fetch_rss_quality()
    
    print(f"✅ Fetched {len(articles)} articles from RSS feeds")
    
    if articles:
        print("\n📰 Sample articles:")
        for i, article in enumerate(articles[:3], 1):
            title = article.get('title', 'No title')
            source = article.get('source', {}).get('name', 'Unknown')
            print(f"\n{i}. {title[:80]}...")
            print(f"   Source: {source}")
        
        # Save to file
        output_file = f"test_rss_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved all RSS articles to: {output_file}")
    else:
        print("⚠️ No articles fetched from RSS feeds")
    
    return articles


def test_newsapi():
    """Test NewsAPI fetching"""
    print_separator("TEST 2: NewsAPI Fetching")
    
    import os
    newsapi_key = os.getenv("NEWSAPI_KEY")
    
    if not newsapi_key or newsapi_key == "e45f816affb84b18ace6a929b6dffa56":
        print("⚠️ NEWSAPI_KEY not set or using default key")
        print("   Skipping NewsAPI test")
        return []
    
    print("Fetching articles from NewsAPI...")
    articles = fetch_quality_news()
    
    print(f"✅ Fetched {len(articles)} articles from NewsAPI")
    
    if articles:
        print("\n📰 Sample NewsAPI articles:")
        for i, article in enumerate(articles[:3], 1):
            title = article.get('title', 'No title')
            print(f"\n{i}. {title[:80]}...")
    else:
        print("⚠️ No articles fetched from NewsAPI")
    
    return articles


def test_gnews():
    """Test GNews fetching"""
    print_separator("TEST 3: GNews Fetching")
    
    import os
    gnews_key = os.getenv("GNEWS_API_KEY")
    
    if not gnews_key or gnews_key == "6428994f84e7d7b2faedd07b8b99be28":
        print("⚠️ GNEWS_API_KEY not set or using default key")
        print("   Skipping GNews test")
        return []
    
    print("Fetching articles from GNews...")
    articles = fetch_gnews_quality()
    
    print(f"✅ Fetched {len(articles)} articles from GNews")
    
    if articles:
        print("\n📰 Sample GNews articles:")
        for i, article in enumerate(articles[:3], 1):
            title = article.get('title', 'No title')
            print(f"\n{i}. {title[:80]}...")
    else:
        print("⚠️ No articles fetched from GNews")
    
    return articles


def test_article_filtering(articles):
    """Test article filtering"""
    print_separator("TEST 4: Article Filtering")
    
    if not articles:
        print("⚠️ No articles to filter")
        return []
    
    print(f"Filtering {len(articles)} articles for relevance...")
    
    # Test relevance filter
    filtered = filter_relevant_articles(articles)
    print(f"✅ Filtered to {len(filtered)} relevant articles")
    
    # Test date filter (past 7 days)
    recent = filter_recent_articles(articles, days=7)
    print(f"✅ Found {len(recent)} articles from past 7 days")
    
    return filtered


def test_content_extraction(articles, max_test=3):
    """Test content extraction from article URLs"""
    print_separator("TEST 5: Content Extraction")
    
    if not articles:
        print("⚠️ No articles to extract content from")
        return []
    
    # Get articles with URLs
    articles_with_urls = [a for a in articles if a.get('url')]
    
    if not articles_with_urls:
        print("⚠️ No articles with URLs found")
        return []
    
    print(f"Testing content extraction on {min(len(articles_with_urls), max_test)} articles...")
    
    results = []
    for i, article in enumerate(articles_with_urls[:max_test], 1):
        url = article.get('url')
        title = article.get('title', 'No title')
        
        print(f"\n{i}. Extracting content from: {title[:60]}...")
        print(f"   URL: {url}")
        
        try:
            content = extract_article_content(url)
            
            if content:
                text_length = len(content.get('text', ''))
                method = content.get('method', 'unknown')
                print(f"   ✅ Successfully extracted {text_length} characters")
                print(f"   Method: {method}")
                
                # Show preview
                preview = content.get('text', '')[:200]
                print(f"   Preview: {preview}...")
                
                results.append({
                    'url': url,
                    'title': title,
                    'content': content
                })
            else:
                print(f"   ❌ Failed to extract content")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    return results


def test_article_enhancement(articles):
    """Test article enhancement with full content"""
    print_separator("TEST 6: Article Enhancement")
    
    if not articles:
        print("⚠️ No articles to enhance")
        return []
    
    print(f"Enhancing {min(len(articles), 5)} articles with full content...")
    print("⏳ This may take 30-60 seconds...\n")
    
    enhanced = enhance_articles_with_content(articles, max_articles=5)
    
    print(f"\n✅ Enhanced {len(enhanced)} articles")
    
    # Show enhancement stats
    enhanced_count = sum(1 for a in enhanced if a.get('full_content'))
    print(f"   Articles with full content: {enhanced_count}/{len(enhanced)}")
    
    if enhanced_count > 0:
        print("\n📊 Enhancement statistics:")
        for article in enhanced[:3]:
            if article.get('full_content'):
                method = article.get('extraction_method', 'unknown')
                length = article.get('content_length', 0)
                print(f"   - {article.get('title', 'No title')[:50]}...")
                print(f"     Method: {method}, Length: {length} chars")
    
    return enhanced


def test_categorization(articles):
    """Test article categorization"""
    print_separator("TEST 7: Article Categorization")
    
    if not articles:
        print("⚠️ No articles to categorize")
        return {}
    
    print(f"Categorizing {len(articles)} articles...")
    
    categories = categorize_articles(articles)
    
    print(f"✅ Categorized articles into {len(categories)} categories:")
    for category, cat_articles in categories.items():
        print(f"\n   📊 {category}: {len(cat_articles)} articles")
        
        if cat_articles:
            print(f"   Sample articles:")
            for i, article in enumerate(cat_articles[:2], 1):
                title = article.get('title', 'No title')
                print(f"   {i}. {title[:60]}...")
    
    return categories


def test_weekly_fetch():
    """Test weekly news fetching"""
    print_separator("TEST 8: Weekly News Fetching")
    
    import os
    newsapi_key = os.getenv("NEWSAPI_KEY")
    
    if not newsapi_key or newsapi_key == "e45f816affb84b18ace6a929b6dffa56":
        print("⚠️ NEWSAPI_KEY not set, skipping weekly test")
        return []
    
    print("Fetching articles from past week...")
    articles = fetch_weekly_quality_news()
    
    print(f"✅ Fetched {len(articles)} articles from past week")
    
    if articles:
        print("\n📰 Sample weekly articles:")
        for i, article in enumerate(articles[:3], 1):
            title = article.get('title', 'No title')
            published = article.get('publishedAt', 'No date')
            print(f"\n{i}. {title[:80]}...")
            print(f"   Published: {published}")
    
    return articles


def test_monthly_fetch():
    """Test monthly news fetching"""
    print_separator("TEST 9: Monthly News Fetching")
    
    import os
    newsapi_key = os.getenv("NEWSAPI_KEY")
    
    if not newsapi_key or newsapi_key == "e45f816affb84b18ace6a929b6dffa56":
        print("⚠️ NEWSAPI_KEY not set, skipping monthly test")
        return []
    
    print("Fetching articles from past month...")
    articles = fetch_monthly_quality_news()
    
    print(f"✅ Fetched {len(articles)} articles from past month")
    
    if articles:
        print("\n📰 Sample monthly articles:")
        for i, article in enumerate(articles[:3], 1):
            title = article.get('title', 'No title')
            published = article.get('publishedAt', 'No date')
            print(f"\n{i}. {title[:80]}...")
            print(f"   Published: {published}")
    
    return articles


def save_results(all_results):
    """Save all test results to JSON file"""
    print_separator("SAVING RESULTS")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"scraper_test_results_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"💾 All test results saved to: {output_file}")


def main():
    """Run all scraping tests"""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + " " * 20 + "SCRAPING FUNCTIONS TEST SUITE" + " " * 24 + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    print("\n")
    
    # Dictionary to store all results
    all_results = {
        'test_timestamp': datetime.now().isoformat(),
        'tests': {}
    }
    
    # Run tests
    try:
        # Test 1: RSS Feeds (always works)
        rss_articles = test_rss_feeds()
        all_results['tests']['rss_feeds'] = {
            'count': len(rss_articles),
            'articles': rss_articles[:10]  # Save first 10
        }
        
        # Test 2: NewsAPI (requires API key)
        newsapi_articles = test_newsapi()
        all_results['tests']['newsapi'] = {
            'count': len(newsapi_articles),
            'articles': newsapi_articles[:5]
        }
        
        # Test 3: GNews (requires API key)
        gnews_articles = test_gnews()
        all_results['tests']['gnews'] = {
            'count': len(gnews_articles),
            'articles': gnews_articles[:5]
        }
        
        # Combine all articles for further tests
        all_articles = rss_articles + newsapi_articles + gnews_articles
        
        if all_articles:
            # Test 4: Filtering
            filtered_articles = test_article_filtering(all_articles)
            all_results['tests']['filtering'] = {
                'original_count': len(all_articles),
                'filtered_count': len(filtered_articles)
            }
            
            # Test 5: Content Extraction
            extraction_results = test_content_extraction(filtered_articles[:5])
            all_results['tests']['content_extraction'] = {
                'tested': len(extraction_results),
                'successful': len([r for r in extraction_results if r.get('content')])
            }
            
            # Test 6: Article Enhancement
            enhanced_articles = test_article_enhancement(filtered_articles[:10])
            all_results['tests']['enhancement'] = {
                'enhanced_count': len(enhanced_articles),
                'with_full_content': len([a for a in enhanced_articles if a.get('full_content')])
            }
            
            # Test 7: Categorization
            if enhanced_articles:
                categories = test_categorization(enhanced_articles)
                all_results['tests']['categorization'] = {
                    'categories': {k: len(v) for k, v in categories.items()}
                }
            
            # Test 8: Weekly Fetch
            weekly_articles = test_weekly_fetch()
            all_results['tests']['weekly_fetch'] = {
                'count': len(weekly_articles)
            }
            
            # Test 9: Monthly Fetch
            monthly_articles = test_monthly_fetch()
            all_results['tests']['monthly_fetch'] = {
                'count': len(monthly_articles)
            }
        
        # Save results
        save_results(all_results)
        
        print_separator("TEST SUMMARY")
        print("✅ All scraping tests completed successfully!")
        print(f"📊 Total articles processed: {len(all_articles)}")
        print(f"🔍 Check the generated JSON files for detailed results")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()