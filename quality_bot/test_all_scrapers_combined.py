#!/usr/bin/env python3
"""
Combined test script using Playwright for easy sites and Apify for difficult sites.
"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_playwright_scrapers():
    """Test scrapers that work well with Playwright"""
    logger.info("="*80)
    logger.info("🎭 PLAYWRIGHT SCRAPERS")
    logger.info("="*80)
    
    from custom_scrapers import (
        scrape_hbr_playwright,
        scrape_deloitte_playwright
    )
    
    results = {}
    
    # Test HBR
    logger.info("\nTesting HBR scraper...")
    try:
        hbr_articles = await scrape_hbr_playwright(max_articles=5)
        results['HBR'] = len(hbr_articles)
        logger.info(f"✅ HBR: {len(hbr_articles)} articles")
        if hbr_articles:
            logger.info(f"   Sample: {hbr_articles[0].get('title', 'No title')[:60]}...")
    except Exception as e:
        logger.error(f"❌ HBR failed: {e}")
        results['HBR'] = 0
    
    # Test Deloitte
    logger.info("\nTesting Deloitte scraper...")
    try:
        deloitte_articles = await scrape_deloitte_playwright(max_articles=5)
        results['Deloitte'] = len(deloitte_articles)
        logger.info(f"✅ Deloitte: {len(deloitte_articles)} articles")
        if deloitte_articles:
            logger.info(f"   Sample: {deloitte_articles[0].get('title', 'No title')[:60]}...")
    except Exception as e:
        logger.error(f"❌ Deloitte failed: {e}")
        results['Deloitte'] = 0
    
    return results


def test_apify_scrapers():
    """Test scrapers that need Apify's anti-bot bypass"""
    logger.info("\n" + "="*80)
    logger.info("🤖 APIFY SCRAPERS")
    logger.info("="*80)
    
    from apify_scrapers import (
        scrape_forbes_apify,
        scrape_mckinsey_apify,
        scrape_atd_apify
    )
    
    results = {}
    
    # Test Forbes
    logger.info("\nTesting Forbes via Apify...")
    forbes_articles = scrape_forbes_apify(max_articles=5)
    results['Forbes'] = len(forbes_articles)
    logger.info(f"{'✅' if forbes_articles else '❌'} Forbes: {len(forbes_articles)} articles")
    if forbes_articles:
        logger.info(f"   Sample: {forbes_articles[0].get('title', 'No title')[:60]}...")
    
    # Test McKinsey
    logger.info("\nTesting McKinsey via Apify...")
    mckinsey_articles = scrape_mckinsey_apify(max_articles=5)
    results['McKinsey'] = len(mckinsey_articles)
    logger.info(f"{'✅' if mckinsey_articles else '❌'} McKinsey: {len(mckinsey_articles)} articles")
    if mckinsey_articles:
        logger.info(f"   Sample: {mckinsey_articles[0].get('title', 'No title')[:60]}...")
    
    # Test ATD
    logger.info("\nTesting ATD via Apify...")
    atd_articles = scrape_atd_apify(max_articles=5)
    results['ATD'] = len(atd_articles)
    logger.info(f"{'✅' if atd_articles else '❌'} ATD: {len(atd_articles)} articles")
    if atd_articles:
        logger.info(f"   Sample: {atd_articles[0].get('title', 'No title')[:60]}...")
    
    return results


async def main():
    """Run all combined tests"""
    logger.info("\n")
    logger.info("█" * 80)
    logger.info("█" + " " * 78 + "█")
    logger.info("█" + " " * 15 + "COMBINED SCRAPERS TEST SUITE" + " " * 30 + "█")
    logger.info("█" + " " * 25 + "Playwright + Apify" + " " * 32 + "█")
    logger.info("█" + " " * 78 + "█")
    logger.info("█" * 80)
    logger.info("\n")
    
    # Test Playwright scrapers (async)
    playwright_results = await test_playwright_scrapers()
    
    # Test Apify scrapers (sync)
    apify_results = test_apify_scrapers()
    
    # Combine results
    all_results = {**playwright_results, **apify_results}
    
    # Final summary
    logger.info("\n" + "="*80)
    logger.info("📊 FINAL TEST SUMMARY")
    logger.info("="*80)
    
    total_articles = sum(all_results.values())
    working_scrapers = sum(1 for count in all_results.values() if count > 0)
    
    # Group by method
    logger.info("\n🎭 Playwright Scrapers:")
    for source in ['HBR', 'Deloitte']:
        if source in all_results:
            count = all_results[source]
            status = "✅" if count > 0 else "❌"
            logger.info(f"   {source:<15} {count:3} articles  {status}")
    
    logger.info("\n🤖 Apify Scrapers:")
    for source in ['Forbes', 'McKinsey', 'ATD']:
        if source in all_results:
            count = all_results[source]
            status = "✅" if count > 0 else "❌"
            logger.info(f"   {source:<15} {count:3} articles  {status}")
    
    logger.info("\n" + "="*80)
    logger.info(f"📈 Overall Results:")
    logger.info(f"   Total Articles: {total_articles}")
    logger.info(f"   Working Scrapers: {working_scrapers}/5")
    logger.info(f"   Success Rate: {working_scrapers/5*100:.1f}%")
    logger.info("="*80)
    
    return all_results


if __name__ == "__main__":
    asyncio.run(main())