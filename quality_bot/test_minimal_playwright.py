#!/usr/bin/env python3
"""
Minimal test to isolate the Playwright issue without retry logic
"""

import asyncio
import logging
from playwright.async_api import async_playwright
from custom_scrapers import fetch_hbr_article_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_minimal_playwright():
    """Test Playwright without retry logic"""
    logger.info("="*60)
    logger.info("🧪 MINIMAL PLAYWRIGHT TEST")
    logger.info("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',
                '--disable-javascript-har-promises',
                '--disable-http2'
            ]
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            ignore_https_errors=True,
            java_script_enabled=True
        )
        
        try:
            # Create a page
            page = await context.new_page()
            logger.info(f"✅ Page created: {type(page)}")
            
            # Test URL
            test_url = "https://hbr.org/2024/03/the-future-of-leadership-development"
            
            logger.info(f"🧪 Testing direct function call...")
            logger.info(f"   Function: fetch_hbr_article_playwright")
            logger.info(f"   Page type: {type(page)}")
            logger.info(f"   URL: {test_url}")
            
            # Try direct call without retry
            try:
                article = await fetch_hbr_article_playwright(page, test_url)
                logger.info(f"✅ SUCCESS: Direct call worked!")
                if article:
                    logger.info(f"   Title: {article.get('title', 'No title')}")
                else:
                    logger.info(f"   Article is None (but no error)")
            except Exception as e:
                logger.error(f"❌ ERROR in direct call: {e}")
                logger.error(f"   Error type: {type(e)}")
                
        finally:
            await browser.close()
    
    logger.info("="*60)

if __name__ == "__main__":
    asyncio.run(test_minimal_playwright())