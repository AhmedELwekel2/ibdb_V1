#!/usr/bin/env python3
"""
Test the retry logic to isolate the 'NoneType' object can't be awaited issue
"""

import asyncio
import logging
from playwright.async_api import async_playwright
from custom_scrapers import fetch_hbr_article_playwright, retry_with_params

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_retry_logic():
    """Test the retry logic specifically"""
    logger.info("="*60)
    logger.info("🧪 TESTING RETRY LOGIC")
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
            
            logger.info(f"🧪 Testing retry_with_params...")
            logger.info(f"   Function: fetch_hbr_article_playwright")
            logger.info(f"   Page type: {type(page)}")
            logger.info(f"   URL: {test_url}")
            
            # Test the wrapper function creation
            logger.info(f"🔧 Creating wrapper function...")
            async def test_wrapper():
                logger.info(f"   Wrapper called with page: {type(page)}, url: {test_url}")
                return await fetch_hbr_article_playwright(page, test_url)
            
            logger.info(f"   Wrapper function type: {type(test_wrapper)}")
            logger.info(f"   Wrapper function: {test_wrapper}")
            
            # Test if wrapper is awaitable
            logger.info(f"🔧 Testing if wrapper is awaitable...")
            try:
                coro = test_wrapper()
                logger.info(f"   Wrapper is awaitable! Coroutine type: {type(coro)}")
                
                # Now try the actual retry function
                logger.info(f"🔧 Testing retry_with_params...")
                article = await retry_with_params(fetch_hbr_article_playwright, page, test_url, max_retries=1, delay=0.1)
                logger.info(f"✅ SUCCESS: retry_with_params worked!")
                if article:
                    logger.info(f"   Title: {article.get('title', 'No title')}")
                else:
                    logger.info(f"   Article is None (but no error)")
                    
            except Exception as e:
                logger.error(f"❌ ERROR in wrapper/retry: {e}")
                logger.error(f"   Error type: {type(e)}")
                import traceback
                traceback.print_exc()
                
        finally:
            await browser.close()
    
    logger.info("="*60)

if __name__ == "__main__":
    asyncio.run(test_retry_logic())