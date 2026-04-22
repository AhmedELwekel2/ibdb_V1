#!/usr/bin/env python3
"""
Test script to diagnose and fix Playwright 'NoneType' object issues
"""

import asyncio
import logging
from custom_scrapers import scrape_hbr_playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_single_scraper():
    """Test a single scraper to identify the 'NoneType' issue"""
    logger.info("🧪 Testing single HBR scraper...")
    
    try:
        # Test with minimal articles
        articles = await scrape_hbr_playwright(max_articles=2)
        logger.info(f"✅ SUCCESS: Got {len(articles)} articles")
        
        if articles:
            for i, article in enumerate(articles[:3]):  # Show first 3
                logger.info(f"   Article {i+1}: {article.get('title', 'No title')[:50]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ FAILED: {str(e)}")
        logger.error(f"   Error type: {type(e).__name__}")
        
        # Check if it's the 'NoneType' object error
        if "'NoneType' object" in str(e):
            logger.error("   🎯 This is the 'NoneType' object error!")
            logger.error("   🔍 This usually means:")
            logger.error("      1. Playwright browser failed to launch")
            logger.error("      2. Missing Playwright browsers")
            logger.error("      3. Anti-bot measures blocking access")
        
        return False

async def test_playwright_installation():
    """Test if Playwright is properly installed"""
    logger.info("🔧 Testing Playwright installation...")
    
    try:
        from playwright.async_api import async_playwright
        logger.info("✅ Playwright module imported successfully")
        
        # Test browser launch
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
                logger.info("✅ Browser launched successfully")
                
                # Test page creation
                page = await browser.new_page()
                logger.info("✅ Page created successfully")
                
                # Test simple navigation
                await page.goto("https://httpbin.org/get", timeout=10000)
                logger.info("✅ Navigation successful")
                
                await page.close()
                await browser.close()
                logger.info("✅ Browser closed successfully")
                
                return True
                
            except Exception as browser_error:
                logger.error(f"❌ Browser error: {browser_error}")
                return False
                
    except ImportError as e:
        logger.error(f"❌ Playwright not installed: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("="*60)
    logger.info("🚀 PLAYWRIGHT DIAGNOSTIC TEST")
    logger.info("="*60)
    
    # Step 1: Test installation
    install_ok = await test_playwright_installation()
    if not install_ok:
        logger.error("❌ Playwright installation failed - fix this first!")
        logger.error("   Run: playwright install chromium")
        return
    
    # Step 2: Test single scraper
    scraper_ok = await test_single_scraper()
    if not scraper_ok:
        logger.error("❌ Scraper test failed - check logs above")
        return
    
    logger.info("✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())