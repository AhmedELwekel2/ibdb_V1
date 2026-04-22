#!/usr/bin/env python3
"""
Test script for custom scrapers using Playwright
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_all_scrapers():
    """Test all custom scrapers with Playwright"""
    logger.info("="*80)
    logger.info("🧪 CUSTOM SCRAPERS TEST WITH PLAYWRIGHT")
    logger.info("="*80)
    
    try:
        from custom_scrapers import (
            scrape_hbr_playwright,
            scrape_forbes_playwright,
            scrape_atd_playwright,
            scrape_mckinsey_playwright,
            scrape_deloitte_playwright
        )
        logger.info("✅ Successfully imported all scrapers\n")
    except ImportError as e:
        logger.error(f"❌ Failed to import scrapers: {e}")
        return
    
    results = {}
    
    # Test HBR
    logger.info("Testing HBR scraper...")
    try:
        hbr_articles = await scrape_hbr_playwright(max_articles=3)
        results['HBR'] = len(hbr_articles)
        logger.info(f"✅ HBR: Found {len(hbr_articles)} articles")
        if hbr_articles:
            logger.info(f"   Sample: {hbr_articles[0].get('title', 'No title')[:60]}...")
    except Exception as e:
        logger.error(f"❌ HBR failed: {e}")
        results['HBR'] = 0
    
    # Test Forbes
    logger.info("\nTesting Forbes scraper...")
    try:
        forbes_articles = await scrape_forbes_playwright(max_articles=3)
        results['Forbes'] = len(forbes_articles)
        logger.info(f"✅ Forbes: Found {len(forbes_articles)} articles")
        if forbes_articles:
            logger.info(f"   Sample: {forbes_articles[0].get('title', 'No title')[:60]}...")
    except Exception as e:
        logger.error(f"❌ Forbes failed: {e}")
        results['Forbes'] = 0
    
    # Test ATD
    logger.info("\nTesting ATD scraper...")
    try:
        atd_articles = await scrape_atd_playwright(max_articles=3)
        results['ATD'] = len(atd_articles)
        logger.info(f"✅ ATD: Found {len(atd_articles)} articles")
        if atd_articles:
            logger.info(f"   Sample: {atd_articles[0].get('title', 'No title')[:60]}...")
    except Exception as e:
        logger.error(f"❌ ATD failed: {e}")
        results['ATD'] = 0
    
    # Test McKinsey
    logger.info("\nTesting McKinsey scraper...")
    try:
        mckinsey_articles = await scrape_mckinsey_playwright(max_articles=3)
        results['McKinsey'] = len(mckinsey_articles)
        logger.info(f"✅ McKinsey: Found {len(mckinsey_articles)} articles")
        if mckinsey_articles:
            logger.info(f"   Sample: {mckinsey_articles[0].get('title', 'No title')[:60]}...")
    except Exception as e:
        logger.error(f"❌ McKinsey failed: {e}")
        results['McKinsey'] = 0
    
    # Test Deloitte
    logger.info("\nTesting Deloitte scraper...")
    try:
        deloitte_articles = await scrape_deloitte_playwright(max_articles=3)
        results['Deloitte'] = len(deloitte_articles)
        logger.info(f"✅ Deloitte: Found {len(deloitte_articles)} articles")
        if deloitte_articles:
            logger.info(f"   Sample: {deloitte_articles[0].get('title', 'No title')[:60]}...")
    except Exception as e:
        logger.error(f"❌ Deloitte failed: {e}")
        results['Deloitte'] = 0
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("📊 TEST SUMMARY")
    logger.info("="*80)
    
    total_articles = sum(results.values())
    working_scrapers = sum(1 for count in results.values() if count > 0)
    
    for source, count in results.items():
        status = "✅ WORKING" if count > 0 else "❌ FAILED"
        logger.info(f"   {source:<15} {count:3} articles  {status}")
    
    logger.info(f"\n   Total: {total_articles} articles")
    logger.info(f"   Working scrapers: {working_scrapers}/5")
    
    logger.info("="*80)
    
    return results

if __name__ == "__main__":
    asyncio.run(test_all_scrapers())