"""
Test script for the new scrapers: McKinsey, Deloitte, and LinkedIn.
This script tests the newly added scrapers to ensure they work correctly.
"""

import logging
from custom_scrapers import (
    scrape_mckinsey_articles,
    scrape_deloitte_articles,
    scrape_linkedin_articles
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_mckinsey():
    """Test McKinsey Insights scraper."""
    print("\n" + "="*80)
    print("Testing McKinsey Insights Scraper")
    print("="*80)
    print("Best for: High-level data on the future of work and digital transformation")
    
    try:
        articles = scrape_mckinsey_articles(max_articles=5)
        print(f"\n✅ McKinsey scraper returned {len(articles)} articles")
        
        if articles:
            print("\nFirst 3 articles:")
            for i, article in enumerate(articles[:3], 1):
                print(f"\n{i}. {article.get('title', 'No title')[:70]}...")
                print(f"   URL: {article.get('url', 'No URL')[:80]}...")
                print(f"   Description: {article.get('description', 'No description')[:100]}...")
        return articles
    except Exception as e:
        print(f"\n❌ Error testing McKinsey scraper: {e}")
        return []

def test_deloitte():
    """Test Deloitte Insights scraper."""
    print("\n" + "="*80)
    print("Testing Deloitte Insights Scraper")
    print("="*80)
    print("Best for: Industry outlooks and human capital trends")
    
    try:
        articles = scrape_deloitte_articles(max_articles=5)
        print(f"\n✅ Deloitte scraper returned {len(articles)} articles")
        
        if articles:
            print("\nFirst 3 articles:")
            for i, article in enumerate(articles[:3], 1):
                print(f"\n{i}. {article.get('title', 'No title')[:70]}...")
                print(f"   URL: {article.get('url', 'No URL')[:80]}...")
                print(f"   Description: {article.get('description', 'No description')[:100]}...")
        return articles
    except Exception as e:
        print(f"\n❌ Error testing Deloitte scraper: {e}")
        return []

def test_linkedin():
    """Test LinkedIn Learning scraper."""
    print("\n" + "="*80)
    print("Testing LinkedIn Thought Leaders Scraper")
    print("="*80)
    print("Top Leaders: Josh Bersin, Donald H. Taylor, Lori Niles-Hofmann")
    print("Official Hub: LinkedIn Learning")
    
    try:
        articles = scrape_linkedin_articles(max_articles=5)
        print(f"\n✅ LinkedIn scraper returned {len(articles)} articles")
        
        if articles:
            print("\nFirst 3 articles:")
            for i, article in enumerate(articles[:3], 1):
                print(f"\n{i}. {article.get('title', 'No title')[:70]}...")
                print(f"   URL: {article.get('url', 'No URL')[:80]}...")
                print(f"   Description: {article.get('description', 'No description')[:100]}...")
        return articles
    except Exception as e:
        print(f"\n❌ Error testing LinkedIn scraper: {e}")
        return []

def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("TESTING NEW CUSTOM SCRAPERS")
    print("="*80)
    
    # Test each scraper
    mckinsey_results = test_mckinsey()
    deloitte_results = test_deloitte()
    linkedin_results = test_linkedin()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"McKinsey Insights: {len(mckinsey_results)} articles")
    print(f"Deloitte Insights: {len(deloitte_results)} articles")
    print(f"LinkedIn Learning: {len(linkedin_results)} articles")
    print(f"Total: {len(mckinsey_results) + len(deloitte_results) + len(linkedin_results)} articles")
    print("="*80)
    
    return {
        'mckinsey': mckinsey_results,
        'deloitte': deloitte_results,
        'linkedin': linkedin_results
    }

if __name__ == "__main__":
    results = main()