"""
Custom scrapers for HBR, Forbes, ATD, McKinsey, Deloitte, and LinkedIn.
These scrapers use Playwright-based browsing to fetch articles from websites.
"""

import asyncio
import logging
import random
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Retry helper function
async def retry_async(func, max_retries=3, delay=1):
    """Retry an async function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            result = await func()
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            wait_time = delay * (2 ** attempt) + random.uniform(0.5, 1.5)
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time:.1f}s: {e}")
            await asyncio.sleep(wait_time)

# Wrapper function for retrying with parameters
async def retry_with_params(func, *args, max_retries=3, delay=1):
    """Retry an async function with parameters."""
    async def wrapper():
        return await func(*args)
    
    return await retry_async(wrapper, max_retries=max_retries, delay=delay)

# ============================================================================
# PLAYWRIGHT-BASED SCRAPERS
# ============================================================================

async def scrape_hbr_playwright(max_articles=15):
    """
    Scrape HBR articles using Playwright to bypass anti-bot measures.
    
    Returns: List of article dictionaries
    """
    logger.info("🎭 Using Playwright to scrape HBR articles...")
    articles = []
    
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
                '--disable-images',  # Speed up loading by not loading images
                '--disable-javascript-har-promises',  # Fix HTTP/2 issues
                '--disable-http2'  # Disable HTTP/2 to avoid protocol errors
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
            ignore_https_errors=True,  # Ignore SSL certificate errors
            java_script_enabled=True
        )
        
        hbr_urls = [
            "https://hbr.org/topic/management",
            "https://hbr.org/topic/strategy", 
            "https://hbr.org/topic/leadership",
        ]
        
        for url_idx, base_url in enumerate(hbr_urls):
            try:
                if url_idx > 0:
                    await asyncio.sleep(2)  # Reduced delay
                
                logger.info(f"   🎭 Playwright fetching HBR: {base_url}")
                page = await context.new_page()
                
                await page.goto(base_url, wait_until='domcontentloaded', timeout=60000)
                
                # Wait a bit for dynamic content
                await asyncio.sleep(1)
                
                # Find article links
                article_links = []
                links = await page.query_selector_all('a[href]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href and any(year in href for year in ['/2023/', '/2024/', '/2025/', '/2026/']):
                        if not any(skip in href for skip in ['/authors/', '/search/', '/topic/']):
                            if href.startswith('/'):
                                full_url = 'https://hbr.org' + href
                            else:
                                full_url = href
                            if full_url not in article_links:
                                article_links.append(full_url)
                
                logger.info(f"   Found {len(article_links)} potential articles")
                
                # Fetch article details
                limit = min(max_articles // len(hbr_urls) + 2, len(article_links))
                for url in article_links[:limit]:
                    try:
                        await asyncio.sleep(random.uniform(0.5, 1.5))  # Random short delay
                        
                        # Create a new page for each article to avoid conflicts
                        article_page = await context.new_page()
                        try:
                            # Use retry logic for article fetching
                            article = await retry_with_params(
                                fetch_hbr_article_playwright, article_page, url,
                                max_retries=2,
                                delay=1
                            )
                            if article:
                                articles.append(article)
                                logger.info(f"   ✅ HBR article: {article['title'][:40]}...")
                        finally:
                            await article_page.close()
                    except Exception as e:
                        logger.warning(f"   Failed to fetch HBR article {url}: {e}")
                        continue
                
                await page.close()
                
                if len(articles) >= max_articles:
                    break
                    
            except Exception as e:
                logger.error(f"   Playwright HBR error {base_url}: {e}")
                continue
        
        await browser.close()
    
    logger.info(f"✅ Playwright scraped {len(articles)} HBR articles")
    return articles

async def fetch_hbr_article_playwright(page, url):
    """Fetch a single HBR article using Playwright."""
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        await asyncio.sleep(0.5)  # Reduced delay
        
        # Extract title
        title_elem = await page.query_selector('h1')
        title = await title_elem.inner_text() if title_elem else ''
        
        # Extract description
        desc_elem = await page.query_selector('meta[property="og:description"]')
        description = await desc_elem.get_attribute('content') if desc_elem else ''
        
        # Extract date
        date_elem = await page.query_selector('time')
        published = await date_elem.get_attribute('datetime') if date_elem else ''
        
        # Extract body
        article_body = await page.query_selector('article')
        body_text = await article_body.inner_text() if article_body else description
        body_text = body_text[:500] + '...' if body_text else description
        
        return {
            'title': title,
            'description': description or body_text[:300],
            'url': url,
            'publishedAt': published,
            'source': {'name': 'Harvard Business Review'},
            'full_content': body_text
        }
    except Exception as e:
        logger.warning(f"   Playwright error fetching HBR article {url}: {e}")
        return None

async def scrape_forbes_playwright(max_articles=15):
    """
    Scrape Forbes articles using Playwright to bypass anti-bot measures.

    Returns: List of article dictionaries
    """
    logger.info("🎭 Using Playwright to scrape Forbes articles...")
    articles = []
    
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
        
        forbes_urls = [
            "https://www.forbes.com/leadership/",
            "https://www.forbes.com/business/",
        ]
        
        for url_idx, base_url in enumerate(forbes_urls):
            try:
                if url_idx > 0:
                    await asyncio.sleep(2)  # Reduced delay
                
                logger.info(f"   🎭 Playwright fetching Forbes: {base_url}")
                page = await context.new_page()
                page.set_default_timeout(60000)
                await page.goto(base_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(1)  # Reduced delay
                
                # Find article links
                article_links = []
                links = await page.query_selector_all('a[href]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href and any(pattern in href for pattern in ['/sites/', '/article/', '/2023/', '/2024/', '/2025/']):
                        if not any(skip in href for skip in ['/video/', '/pictures/', '/gallery/']):
                            if href.startswith('/'):
                                full_url = 'https://www.forbes.com' + href
                            else:
                                full_url = href
                            if full_url not in article_links:
                                article_links.append(full_url)
                
                logger.info(f"   Found {len(article_links)} potential articles")
                
                # Fetch article details
                limit = min(max_articles // len(forbes_urls) + 2, len(article_links))
                for url in article_links[:limit]:
                    try:
                        await asyncio.sleep(random.uniform(0.5, 1.5))  # Random short delay
                        
                        # Use retry logic for article fetching
                        article = await retry_with_params(
                            fetch_forbes_article_playwright, page, url,
                            max_retries=2,
                            delay=1
                        )
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.warning(f"   Failed to fetch Forbes article {url}: {e}")
                        continue
                
                await page.close()
                
                if len(articles) >= max_articles:
                    break
                    
            except Exception as e:
                logger.error(f"   Playwright Forbes error {base_url}: {e}")
                continue
        
        await browser.close()
    
    logger.info(f"✅ Playwright scraped {len(articles)} Forbes articles")
    return articles

async def fetch_forbes_article_playwright(page, url):
    """Fetch a single Forbes article using Playwright."""
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        await asyncio.sleep(1)  # Reduced delay
        
        # Extract title
        title_elem = await page.query_selector('h1')
        title = await title_elem.inner_text() if title_elem else ''
        
        # Extract description
        desc_elem = await page.query_selector('meta[property="og:description"]')
        description = await desc_elem.get_attribute('content') if desc_elem else ''
        
        # Extract date
        date_elem = await page.query_selector('time')
        published = await date_elem.get_attribute('datetime') if date_elem else ''
        
        # Extract body
        article_body = await page.query_selector('article')
        body_text = await article_body.inner_text() if article_body else description
        body_text = body_text[:500] + '...' if body_text else description
        
        return {
            'title': title,
            'description': description or body_text[:300],
            'url': url,
            'publishedAt': published,
            'source': {'name': 'Forbes Leadership'},
            'full_content': body_text
        }
    except Exception as e:
        logger.warning(f"   Playwright error fetching Forbes article {url}: {e}")
        return None

async def scrape_atd_playwright(max_articles=15):
    """
    Scrape ATD articles using Playwright to bypass anti-bot measures.

    Returns: List of article dictionaries
    """
    logger.info("🎭 Using Playwright to scrape ATD articles...")
    articles = []
    
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
        
        atd_urls = [
            "https://www.td.org/atd-blog",
            "https://www.td.org/",
        ]
        
        for url_idx, base_url in enumerate(atd_urls):
            try:
                if url_idx > 0:
                    await asyncio.sleep(3)  # Reduced from 15s
                
                logger.info(f"   🎭 Playwright fetching ATD: {base_url}")
                page = await context.new_page()
                page.set_default_timeout(60000)
                try:
                    await page.goto(base_url, wait_until='networkidle', timeout=60000)
                except Exception as nav_err:
                    logger.warning(f"   ATD navigation issue ({base_url}): {nav_err}, trying domcontentloaded...")
                    await page.goto(base_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(3)  # Wait for any redirects to settle
                
                # Find article links
                article_links = []
                try:
                    links = await page.query_selector_all('a[href]')
                except Exception as q_err:
                    logger.warning(f"   ATD query error, page may have navigated: {q_err}")
                    links = []
                for link in links:
                    href = await link.get_attribute('href')
                    if href and any(pattern in href for pattern in ['/article/', '/blog/', 'td.org/']):
                        if not any(skip in href for skip in ['#', '/search/', '/contact/']):
                            if href.startswith('/'):
                                full_url = 'https://www.td.org' + href
                            else:
                                full_url = href
                            if full_url not in article_links:
                                article_links.append(full_url)
                
                logger.info(f"   Found {len(article_links)} potential articles")
                
                # Fetch article details with reasonable delays
                limit = min(max_articles // len(atd_urls) + 1, len(article_links))
                for i, url in enumerate(article_links[:limit]):
                    try:
                        delay = random.uniform(1, 3)  # Random delay between 1-3 seconds
                        logger.info(f"   Fetching ATD article {i+1}/{limit} (waiting {delay:.1f}s)...")
                        await asyncio.sleep(delay)
                        
                        # Use retry logic for article fetching
                        article = await retry_with_params(
                            fetch_atd_article_playwright, page, url,
                            max_retries=2,
                            delay=1
                        )
                        if article:
                            articles.append(article)
                            logger.info(f"   ✅ ATD article: {article['title'][:50]}...")
                    except Exception as e:
                        logger.warning(f"   Failed to fetch ATD article {url}: {e}")
                        continue
                
                await page.close()
                
                if len(articles) >= max_articles:
                    break
                    
            except Exception as e:
                logger.error(f"   Playwright ATD error {base_url}: {e}")
                continue
        
        await browser.close()
    
    logger.info(f"✅ Playwright scraped {len(articles)} ATD articles")
    return articles

async def fetch_atd_article_playwright(page, url):
    """Fetch a single ATD article using Playwright."""
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        await asyncio.sleep(1)  # Reduced delay
        
        # Extract title
        title_elem = await page.query_selector('h1')
        title = await title_elem.inner_text() if title_elem else ''
        
        # Extract description
        desc_elem = await page.query_selector('meta[property="og:description"]')
        description = await desc_elem.get_attribute('content') if desc_elem else ''
        
        # Extract date
        date_elem = await page.query_selector('time')
        published = await date_elem.get_attribute('datetime') if date_elem else ''
        
        # Extract body
        article_body = await page.query_selector('article')
        body_text = await article_body.inner_text() if article_body else description
        body_text = body_text[:500] + '...' if body_text else description
        
        return {
            'title': title,
            'description': description or body_text[:300],
            'url': url,
            'publishedAt': published,
            'source': {'name': 'ATD'},
            'full_content': body_text
        }
    except Exception as e:
        logger.warning(f"   Playwright error fetching ATD article {url}: {e}")
        return None

async def scrape_mckinsey_playwright(max_articles=15):
    """
    Scrape McKinsey articles using Playwright to bypass anti-bot measures.
    Best for: High-level data on the future of work and digital transformation.
    Includes fallback to requests-based scraping when Playwright fails.

    Returns: List of article dictionaries
    """
    logger.info("🎭 Using Playwright to scrape McKinsey articles...")
    articles = []
    
    # Try Playwright first
    playwright_success = False
    
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
                '--disable-http2'  # Critical for fixing HTTP/2 protocol errors
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            ignore_https_errors=True,  # Important for HTTPS issues
            java_script_enabled=True
        )
        
        mckinsey_urls = [
            "https://www.mckinsey.com/featured-insights",
            "https://www.mckinsey.com/capabilities/people-and-organizational-performance/our-insights",
        ]
        
        for url_idx, base_url in enumerate(mckinsey_urls):
            try:
                if url_idx > 0:
                    await asyncio.sleep(3)
                
                logger.info(f"   🎭 Playwright fetching McKinsey: {base_url}")
                page = await context.new_page()
                page.set_default_timeout(30000)  # Reduced from 90s to fail faster
                await page.goto(base_url, wait_until='load', timeout=30000)
                await asyncio.sleep(2)
                
                # Find article links
                article_links = []
                links = await page.query_selector_all('a[href]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href and any(pattern in href for pattern in ['/featured-insights/', '/our-insights/', '/industries/', '/capabilities/']):
                        if not any(skip in href for skip in ['#', '/search/', '/about/', '/careers/', '/contact/']):
                            if href.startswith('/'):
                                full_url = 'https://www.mckinsey.com' + href
                            else:
                                full_url = href
                            if full_url not in article_links and len(full_url) > 40:
                                article_links.append(full_url)
                
                logger.info(f"   Found {len(article_links)} potential articles")
                
                if article_links:
                    playwright_success = True
                
                # Fetch article details
                limit = min(max_articles // len(mckinsey_urls) + 2, len(article_links))
                for url in article_links[:limit]:
                    try:
                        await asyncio.sleep(random.uniform(1, 2))
                        
                        article = await retry_with_params(
                            fetch_mckinsey_article_playwright, page, url,
                            max_retries=2,
                            delay=1
                        )
                        if article:
                            articles.append(article)
                            logger.info(f"   ✅ McKinsey article: {article['title'][:40]}...")
                    except Exception as e:
                        logger.warning(f"   Failed to fetch McKinsey article {url}: {e}")
                        continue
                
                await page.close()
                
                if len(articles) >= max_articles:
                    break
                    
            except Exception as e:
                logger.error(f"   Playwright McKinsey error {base_url}: {e}")
                continue
        
        await browser.close()
    
    # Fallback: Use requests if Playwright failed completely
    if not articles:
        logger.info("   🔄 Playwright failed for McKinsey, trying requests fallback...")
        try:
            import requests as req_lib
            from bs4 import BeautifulSoup
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            fallback_urls = [
                "https://www.mckinsey.com/featured-insights",
                "https://www.mckinsey.com/capabilities/people-and-organizational-performance/our-insights",
            ]
            
            for base_url in fallback_urls:
                try:
                    resp = req_lib.get(base_url, headers=headers, timeout=20, verify=False)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.content, 'html.parser')
                        links = soup.find_all('a', href=True)
                        
                        article_links = []
                        for link in links:
                            href = link['href']
                            if any(p in href for p in ['/our-insights/', '/featured-insights/', '/industries/']):
                                if not any(s in href for s in ['#', '/search/', '/about/', '/careers/']):
                                    full_url = 'https://www.mckinsey.com' + href if href.startswith('/') else href
                                    if full_url not in article_links and len(full_url) > 40:
                                        article_links.append(full_url)
                        
                        logger.info(f"   Found {len(article_links)} potential articles via requests fallback")
                        
                        for url in article_links[:max_articles]:
                            try:
                                art_resp = req_lib.get(url, headers=headers, timeout=15, verify=False)
                                if art_resp.status_code == 200:
                                    art_soup = BeautifulSoup(art_resp.content, 'html.parser')
                                    title_elem = art_soup.find('h1')
                                    title = title_elem.get_text(strip=True) if title_elem else ''
                                    desc_elem = art_soup.find('meta', property='og:description')
                                    description = desc_elem['content'] if desc_elem else ''
                                    
                                    if title and len(title) > 10:
                                        articles.append({
                                            'title': title,
                                            'description': description or title,
                                            'url': url,
                                            'publishedAt': '',
                                            'source': {'name': 'McKinsey Insights'},
                                            'full_content': description or title
                                        })
                                        logger.info(f"   ✅ McKinsey (fallback): {title[:40]}...")
                            except Exception:
                                continue
                        
                        if articles:
                            break
                except Exception as e:
                    logger.warning(f"   Requests fallback also failed for {base_url}: {e}")
                    continue
        except ImportError:
            logger.warning("   requests/bs4 not available for McKinsey fallback")
    
    logger.info(f"✅ Playwright scraped {len(articles)} McKinsey articles")
    return articles

async def fetch_mckinsey_article_playwright(page, url):
    """Fetch a single McKinsey article using Playwright."""
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(1)  # Reduced delay
        
        # Extract title
        title_elem = await page.query_selector('h1')
        title = await title_elem.inner_text() if title_elem else ''
        
        # Extract description
        desc_elem = await page.query_selector('meta[property="og:description"]')
        description = await desc_elem.get_attribute('content') if desc_elem else ''
        
        # Extract date
        date_elem = await page.query_selector('time')
        published = await date_elem.get_attribute('datetime') if date_elem else ''
        
        # Extract body
        article_body = await page.query_selector('article')
        body_text = await article_body.inner_text() if article_body else description
        body_text = body_text[:500] + '...' if body_text else description
        
        return {
            'title': title,
            'description': description or body_text[:300],
            'url': url,
            'publishedAt': published,
            'source': {'name': 'McKinsey Insights'},
            'full_content': body_text
        }
    except Exception as e:
        logger.warning(f"   Playwright error fetching McKinsey article {url}: {e}")
        return None

async def scrape_deloitte_playwright(max_articles=15):
    """
    Scrape Deloitte articles using Playwright to bypass anti-bot measures.
    Best for: Industry outlooks and human capital trends.

    Returns: List of article dictionaries
    """
    logger.info("🎭 Using Playwright to scrape Deloitte articles...")
    articles = []
    
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
        
        deloitte_urls = [
            "https://www2.deloitte.com/insights",
        ]
        
        for url_idx, base_url in enumerate(deloitte_urls):
            try:
                logger.info(f"   🎭 Playwright fetching Deloitte: {base_url}")
                page = await context.new_page()
                page.set_default_timeout(60000)
                await page.goto(base_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(1)  # Reduced delay
                
                # Find article links
                article_links = []
                links = await page.query_selector_all('a[href]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href and any(pattern in href for pattern in ['/insights/', '/article/', '/blog/']):
                        if not any(skip in href for skip in ['#', '/search/', '/about/', '/contact/']):
                            if href.startswith('/'):
                                full_url = 'https://www2.deloitte.com' + href
                            else:
                                full_url = href
                            if full_url not in article_links:
                                article_links.append(full_url)
                
                logger.info(f"   Found {len(article_links)} potential articles")
                
                # Fetch article details
                limit = min(max_articles // len(deloitte_urls) + 2, len(article_links))
                for url in article_links[:limit]:
                    try:
                        await asyncio.sleep(random.uniform(0.5, 1.5))  # Random short delay
                        
                        # Use retry logic for article fetching
                        article = await retry_with_params(
                            fetch_deloitte_article_playwright, page, url,
                            max_retries=2,
                            delay=1
                        )
                        if article:
                            articles.append(article)
                            logger.info(f"   ✅ Deloitte article: {article['title'][:40]}...")
                    except Exception as e:
                        logger.warning(f"   Failed to fetch Deloitte article {url}: {e}")
                        continue
                
                await page.close()
                
                if len(articles) >= max_articles:
                    break
                    
            except Exception as e:
                logger.error(f"   Playwright Deloitte error {base_url}: {e}")
                continue
        
        await browser.close()
    
    logger.info(f"✅ Playwright scraped {len(articles)} Deloitte articles")
    return articles

async def fetch_deloitte_article_playwright(page, url):
    """Fetch a single Deloitte article using Playwright."""
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        await asyncio.sleep(1)  # Reduced delay
        
        # Extract title
        title_elem = await page.query_selector('h1')
        title = await title_elem.inner_text() if title_elem else ''
        
        # Extract description
        desc_elem = await page.query_selector('meta[property="og:description"]')
        description = await desc_elem.get_attribute('content') if desc_elem else ''
        
        # Extract date
        date_elem = await page.query_selector('time')
        published = await date_elem.get_attribute('datetime') if date_elem else ''
        
        # Extract body
        article_body = await page.query_selector('article')
        body_text = await article_body.inner_text() if article_body else description
        body_text = body_text[:500] + '...' if body_text else description
        
        return {
            'title': title,
            'description': description or body_text[:300],
            'url': url,
            'publishedAt': published,
            'source': {'name': 'Deloitte Insights'},
            'full_content': body_text
        }
    except Exception as e:
        logger.warning(f"   Playwright error fetching Deloitte article {url}: {e}")
        return None

async def scrape_linkedin_playwright(max_articles=15):
    """
    Scrape LinkedIn Learning insights using Playwright.
    Note: LinkedIn profiles require authentication, so we scrape the Learning Hub instead.

    Returns: List of article dictionaries
    """
    logger.info("🎭 Using Playwright to scrape LinkedIn Learning...")
    articles = []
    
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
        
        linkedin_urls = [
            "https://www.linkedin.com/learning/blog",
            "https://www.linkedin.com/learning/"
        ]
        
        for url_idx, base_url in enumerate(linkedin_urls):
            try:
                if url_idx > 0:
                    await asyncio.sleep(2)  # Reduced delay
                
                logger.info(f"   🎭 Playwright fetching LinkedIn: {base_url}")
                page = await context.new_page()
                page.set_default_timeout(60000)
                await page.goto(base_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(1)  # Reduced delay
                
                # Find article links
                article_links = []
                links = await page.query_selector_all('a[href]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href and '/learning/' in href:
                        if not any(skip in href for skip in ['#', '/search/', '/login/', '/signup/']):
                            if href.startswith('/'):
                                full_url = 'https://www.linkedin.com' + href
                            else:
                                full_url = href
                            if full_url not in article_links:
                                article_links.append(full_url)
                
                logger.info(f"   Found {len(article_links)} potential articles")
                
                # Fetch article details
                limit = min(max_articles // len(linkedin_urls) + 2, len(article_links))
                for url in article_links[:limit]:
                    try:
                        await asyncio.sleep(random.uniform(0.5, 1.5))  # Random short delay
                        
                        # Use retry logic for article fetching
                        article = await retry_with_params(
                            fetch_linkedin_article_playwright, page, url,
                            max_retries=2,
                            delay=1
                        )
                        if article:
                            articles.append(article)
                            logger.info(f"   ✅ LinkedIn article: {article['title'][:40]}...")
                    except Exception as e:
                        logger.warning(f"   Failed to fetch LinkedIn article {url}: {e}")
                        continue
                
                await page.close()
                
                if len(articles) >= max_articles:
                    break
                    
            except Exception as e:
                logger.error(f"   Playwright LinkedIn error {base_url}: {e}")
                continue
        
        await browser.close()
    
    logger.info(f"✅ Playwright scraped {len(articles)} LinkedIn articles")
    return articles

async def fetch_linkedin_article_playwright(page, url):
    """Fetch a single LinkedIn article using Playwright."""
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
        await asyncio.sleep(1)  # Reduced delay
        
        # Extract title
        title_elem = await page.query_selector('h1')
        title = await title_elem.inner_text() if title_elem else ''
        
        # Extract description
        desc_elem = await page.query_selector('meta[property="og:description"]')
        description = await desc_elem.get_attribute('content') if desc_elem else ''
        
        # Extract date
        date_elem = await page.query_selector('time')
        published = await date_elem.get_attribute('datetime') if date_elem else ''
        
        # Extract body
        article_body = await page.query_selector('article')
        body_text = await article_body.inner_text() if article_body else description
        body_text = body_text[:500] + '...' if body_text else description
        
        # Filter out non-article content (navigation, auth pages, category listings)
        skip_titles = [
            'sign in', 'log in', 'connect with a learning consultant',
            'all online training class topics', 'all online courses list',
            'all learning paths', 'start free trial', 'join now',
            'contact us', 'about us', 'privacy', 'terms',
        ]
        if title and any(skip in title.lower() for skip in skip_titles):
            logger.info(f"   ⏭️ Skipping non-article LinkedIn page: {title[:40]}...")
            return None
        
        # Require minimum title length to filter out junk
        if not title or len(title.strip()) < 10:
            return None
        
        return {
            'title': title,
            'description': description or body_text[:300],
            'url': url,
            'publishedAt': published,
            'source': {'name': 'LinkedIn Learning'},
            'full_content': body_text
        }
    except Exception as e:
        logger.warning(f"   Playwright error fetching LinkedIn article {url}: {e}")
        return None

# ============================================================================
# MAIN ORCHESTRATION FUNCTION
# ============================================================================

async def fetch_all_custom_scrapers(max_articles_per_source=15):
    """
    Fetch articles from all custom scrapers with detailed step-by-step logging.
    """
    logger.info("="*80)
    logger.info("🚀 STARTING CUSTOM SCRAPER ORCHESTRATION")
    logger.info("="*80)
    logger.info(f"📊 Target: {max_articles_per_source} articles per source")
    logger.info("="*80)

    # Track results for the summary report
    stats = {}
    all_articles = []

    # List of scrapers to run
    # Format: (Display Name, Scraper Function)
    scraper_list = [
        ("Harvard Business Review", scrape_hbr_playwright),
        ("Forbes Leadership", scrape_forbes_playwright),
        ("ATD (Talent Development)", scrape_atd_playwright),
        ("McKinsey Insights", scrape_mckinsey_playwright),
        ("Deloitte Insights", scrape_deloitte_playwright),
        ("LinkedIn Learning Hub", scrape_linkedin_playwright),
    ]

    total_sources = len(scraper_list)
    
    for idx, (name, scraper_func) in enumerate(scraper_list, 1):
        logger.info(f"\n{'='*20} SOURCE {idx}/{total_sources}: {name} {'='*20}")
        logger.info(f"🔍 Starting scrape process for: {name}")
        logger.info(f"🎯 Target: {max_articles_per_source} articles")
        logger.info("-" * 60)
        
        try:
            # Run the scraper with detailed timing
            import time
            start_time = time.time()
            
            logger.info(f"⚡ Executing {name} scraper...")
            results = await scraper_func(max_articles=max_articles_per_source)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Store stats
            count = len(results)
            stats[name] = {"status": "✅ Success", "count": count}
            all_articles.extend(results)
            
            logger.info(f"✅ COMPLETED: {name}")
            logger.info(f"   ⏱️  Duration: {duration:.1f} seconds")
            logger.info(f"   📦 Articles found: {count}")
            logger.info(f"   📈 Success rate: {(count/max_articles_per_source*100):.1f}%")
            
            # Log first few article titles for verification
            if results:
                logger.info(f"   📝 Sample articles:")
                for i, article in enumerate(results[:3]):
                    title = article.get('title', 'No title')[:50]
                    logger.info(f"      {i+1}. {title}...")
                if len(results) > 3:
                    logger.info(f"      ... and {len(results)-3} more")
            
        except Exception as e:
            logger.error(f"❌ FAILED: {name}")
            logger.error(f"   💥 Error: {str(e)}")
            logger.error(f"   📦 Articles found: 0")
            stats[name] = {"status": "❌ Failed", "count": 0}
        
        logger.info("-" * 60)

    # ============================================================================
    # FINAL SUMMARY REPORT
    # ============================================================================
    logger.info("\n" + "="*80)
    logger.info("🏆 FINAL SCRAPING RESULTS")
    logger.info("="*80)
    logger.info(f"{'SOURCE':<30} | {'STATUS':<10} | {'ARTICLES':<10}")
    logger.info("-" * 80)
    
    successful_sources = 0
    total_articles = 0
    
    for source, data in stats.items():
        status = data['status']
        count = data['count']
        logger.info(f"{source:<30} | {status:<10} | {count:<10}")
        
        if status == "✅ Success":
            successful_sources += 1
        total_articles += count
    
    logger.info("-" * 80)
    success_rate = (successful_sources / len(scraper_list)) * 100
    logger.info(f"{'TOTAL ARTICLES COLLECTED':<30} | {' ': <10} | {total_articles:<10}")
    logger.info(f"{'SUCCESSFUL SOURCES':<30} | {successful_sources}/{len(scraper_list):<10} | {success_rate:.1f}%")
    logger.info("="*80 + "\n")

    return all_articles

# Backwards compatibility alias
fetch_all_custom_scrapers_with_playwright = fetch_all_custom_scrapers

if __name__ == "__main__":
    # Test the scrapers
    logging.basicConfig(level=logging.INFO)
    articles = asyncio.run(fetch_all_custom_scrapers(max_articles_per_source=5))
    print(f"\n\nTotal articles fetched: {len(articles)}")
    for article in articles:
        print(f"\n- {article.get('title', 'No title')[:60]}...")
        print(f"  Source: {article.get('source', {}).get('name', 'Unknown')}")