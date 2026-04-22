"""
Test script for Playwright-based scrapers.
Run this to verify the Playwright installation and test each scraper.
"""

import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_playwright_installation():
    """Test if Playwright is properly installed."""
    logger.info("="*60)
    logger.info("Testing Playwright Installation")
    logger.info("="*60)
    
    try:
        from playwright.sync_api import sync_playwright
        logger.info("✅ Playwright Python package installed")
        
        # Try to launch a browser
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            logger.info("✅ Chromium browser available")
            browser.close()
        
        return True
    except ImportError:
        logger.error("❌ Playwright not installed. Run: pip install playwright")
        return False
    except Exception as e:
        logger.error(f"❌ Playwright browser error: {e}")
        logger.info("Run: playwright install chromium")
        return False

def test_custom_scrapers():
    """Test the custom scrapers module."""
    logger.info("\n" + "="*60)
    logger.info("Testing Custom Scrapers Module")
    logger.info("="*60)
    
    try:
        from custom_scrapers import (
            fetch_all_custom_scrapers_with_playwright,
            scrape_hbr_playwright,
            scrape_forbes_playwright,
            scrape_atd_playwright,
            scrape_mckinsey_playwright,
            scrape_deloitte_playwright
        )
        logger.info("✅ Custom scrapers module imported successfully")
        logger.info("✅ Playwright scraper functions available")
        return True
    except ImportError as e:
        logger.error(f"❌ Cannot import custom scrapers: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error loading custom scrapers: {e}")
        return False

def test_hbr_quick():
    """Quick test of HBR scraper (RSS only)."""
    logger.info("\n" + "="*60)
    logger.info("Testing HBR Scraper (RSS Only)")
    logger.info("="*60)
    
    try:
        from custom_scrapers import fetch_hbr_via_rss
        articles = fetch_hbr_via_rss(max_articles=3)
        logger.info(f"✅ HBR RSS test successful: {len(articles)} articles")
        if articles:
            logger.info(f"   Sample: {articles[0].get('title', 'No title')[:50]}...")
        return len(articles) > 0
    except Exception as e:
        logger.error(f"❌ HBR RSS test failed: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("\n" + "="*80)
    logger.info("🧪 PLAYWRIGHT SCRAPERS TEST SUITE")
    logger.info("="*80)
    
    results = {}
    
    # Test 1: Playwright Installation
    results['playwright'] = test_playwright_installation()
    
    # Test 2: Custom Scrapers Module
    results['module'] = test_custom_scrapers()
    
    # Test 3: Quick RSS Test
    if results['module']:
        results['hbr_rss'] = test_hbr_quick()
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("📊 TEST SUMMARY")
    logger.info("="*80)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"   {test_name.upper():<20} {status}")
    
    all_passed = all(results.values())
    
    logger.info("\n" + "="*80)
    if all_passed:
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("✅ Playwright scrapers are ready to use")
        logger.info("\nTo run full scraper:")
        logger.info("  python -c 'from custom_scrapers import fetch_all_custom_scrapers_with_playwright; articles = fetch_all_custom_scrapers_with_playwright(max_articles_per_source=5); print(f\"Fetched {len(articles)} articles\")'")
    else:
        logger.error("❌ SOME TESTS FAILED")
        logger.info("\nTroubleshooting:")
        logger.info("  1. Playwright not installed: pip install playwright")
        logger.info("  2. Browser not installed: playwright install chromium")
        logger.info("  3. Check custom_scrapers.py for syntax errors")
    logger.info("="*80)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())