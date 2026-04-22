# Custom Scrapers Test Results

## Test Date: April 21, 2026

## Overview
This document summarizes the test results for custom scrapers using Playwright and Apify.

## Playwright Scrapers (✅ Working)

### HBR (Harvard Business Review) - ✅ WORKING
- **Status:** Successfully scraping articles
- **Method:** Playwright with headless Chromium
- **Articles Fetched:** 6 articles
- **Sample Articles:**
  - "Tapping into Your Team's Circadian Rhythms"
  - "Why Leaders Need 'Power Skills'"
  - "The Hidden Demand for AI Inside Your Company"
  - "Case Study: Should a Funeral Company Shift Its Business Model?"
  - "Negotiating When There Is No Plan B"
  - "Data Privacy Is a Growth Strategy"

### Deloitte - ✅ WORKING
- **Status:** Successfully scraping articles
- **Method:** Playwright with headless Chromium
- **Articles Fetched:** 7 articles
- **Sample Articles:**
  - "Weekly Global Economic Update"
  - "Tech Trends 2026"
  - "2026 Global Human Capital Trends"
  - "2026 Digital Media Trends: Capturing All Viewers"
  - "TMT Predictions 2026: The AI gap narrows"

## Apify Scrapers (⚠️ Issues Found)

### Forbes - ❌ ERROR
- **Status:** Failing with JavaScript error
- **Error:** `TypeError: $ is not a function`
- **Issue:** The pageFunction uses jQuery ($) syntax which is not available in Apify's context
- **Fix Needed:** Update to use Cheerio or Playwright selectors

### McKinsey - ❌ PENDING
- **Status:** Not yet tested in current run
- **Previous Issue:** HTTP2 protocol errors with Playwright
- **Expected:** Should work with Apify once Forbes issue is fixed

### ATD - ❌ PENDING
- **Status:** Not yet tested in current run
- **Previous Issue:** No articles found with Playwright
- **Expected:** Should work with Apify once Forbes issue is fixed

## Issues Identified

### 1. Apify Selector Error
**Problem:** The Apify pageFunction uses jQuery syntax (`$('h1')`) which is not available in the Apify Website Content Crawler context.

**Solution:** Update pageFunction to use:
- Playwright's built-in selectors: `await page.locator('h1').textContent()`
- Or Cheerio selectors if using CheerioContext

### 2. Previous Playwright Failures
**Forbes:** Timeout issues (30s exceeded)
**McKinsey:** HTTP2 protocol errors
**ATD:** No articles found

## Current Success Rate
- **Playwright Scrapers:** 2/2 working (100%)
- **Apify Scrapers:** 0/3 tested successfully (needs fix)
- **Overall:** 2/5 working (40%)

## Recommendations

1. **Fix Apify Selectors:** Update all Apify scrapers to use correct selector syntax
2. **Test Apify Scrapers:** Re-run tests after fixing selector issues
3. **Optimize Playwright:** Consider increasing timeout for Forbes
4. **Consider Fallback Strategy:** Implement automatic fallback from Playwright to Apify for difficult sites

## Next Steps

1. Fix Apify pageFunction selectors
2. Re-run combined tests
3. Document final working configuration
4. Create production-ready scraper integration