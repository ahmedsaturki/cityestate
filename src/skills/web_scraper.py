"""
Web Scraper Skill — الاستخراج المتقدم من المواقع
==================================================
Advanced web scraping with content extraction, structured data parsing,
and anti-detection measures. Supports real estate listing sites.
"""

import json
import logging
import re
from urllib.parse import urljoin

logger = logging.getLogger("skills.web_scraper")


class WebScraperSkill:
    """Advanced web scraping skill."""

    def __init__(self):
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    async def scrape_url(self, url: str, extract_links: bool = True) -> dict:
        """Scrape a single URL and extract content."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self._headers["User-Agent"],
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(2000)

                title = await page.title()
                content = await page.inner_text("body")
                html = await page.content()

                result = {
                    "url": url,
                    "title": title,
                    "content": content[:10000],
                    "html_length": len(html),
                }

                if extract_links:
                    links = await page.eval_on_selector_all(
                        "a[href]",
                        "els => els.map(e => ({text: e.innerText.trim(), href: e.href})).filter(l => l.text && l.href)",
                    )
                    result["links"] = links[:100]

                # Extract structured data
                result["structured"] = await self._extract_structured_data(page)

                await browser.close()
                return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def scrape_multiple(self, urls: list[str], max_concurrent: int = 3) -> list[dict]:
        """Scrape multiple URLs concurrently."""
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrent)

        async def _scrape_with_limit(url):
            async with semaphore:
                return await self.scrape_url(url, extract_links=False)

        tasks = [_scrape_with_limit(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            r if isinstance(r, dict) else {"url": urls[i], "error": str(r)}
            for i, r in enumerate(results)
        ]

    async def extract_listing(self, url: str, site_type: str = "auto") -> dict:
        """Extract real estate listing data from a URL."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(3000)

                listing_data = {"url": url}

                # Extract price
                price_selectors = [
                    "[class*='price']",
                    "[data-testid*='price']",
                    "span:has-text('EGP')",
                    "span:has-text('جنيه')",
                ]
                for sel in price_selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            price_text = await el.inner_text()
                            listing_data["price"] = self._extract_price(price_text)
                            break
                    except Exception as e:
                        logger.debug("Web scraper price error: %s", e)
                        continue

                # Extract location
                location_selectors = [
                    "[class*='location']",
                    "[class*='address']",
                    "[data-testid*='location']",
                ]
                for sel in location_selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            listing_data["location"] = await el.inner_text()
                            break
                    except Exception as e:
                        logger.debug("Web scraper location error: %s", e)
                        continue

                # Extract features
                features = await page.eval_on_selector_all(
                    "[class*='feature'], [class*='amenity'], li",
                    "els => els.map(e => e.innerText.trim()).filter(t => t.length > 0 && t.length < 100)",
                )
                listing_data["features"] = features[:20]

                # Extract images
                images = await page.eval_on_selector_all(
                    "img[src]",
                    "els => els.map(e => e.src).filter(s => s && !s.includes('icon'))",
                )
                listing_data["images"] = images[:10]

                await browser.close()
                return {"status": "success", "listing": listing_data}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def scrape_listing_site(self, site_url: str, max_pages: int = 3) -> dict:
        """Scrape multiple pages from a listing site."""
        try:
            from playwright.async_api import async_playwright

            all_listings = []
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                current_url = site_url
                for page_num in range(max_pages):
                    await page.goto(current_url, wait_until="networkidle")
                    await page.wait_for_timeout(2000)

                    # Extract listing links
                    links = await page.eval_on_selector_all(
                        "a[href*='listing'], a[href*='property'], a[href*='ad']",
                        "els => els.map(e => e.href)",
                    )
                    all_listings.extend(links[:20])

                    # Try to find next page
                    try:
                        next_btn = await page.query_selector("a[rel='next'], button:has-text('Next')")
                        if next_btn:
                            current_url = await next_btn.get_attribute("href")
                            if not current_url.startswith("http"):
                                current_url = urljoin(site_url, current_url)
                        else:
                            break
                    except Exception:
                        break

                await browser.close()
                return {
                    "status": "success",
                    "site": site_url,
                    "pages_scraped": page_num + 1,
                    "listings_found": len(all_listings),
                    "listing_urls": all_listings,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _extract_structured_data(self, page) -> dict:
        """Extract JSON-LD and meta tags from page."""
        try:
            # JSON-LD
            json_ld = await page.eval_on_selector_all(
                'script[type="application/ld+json"]',
                "els => els.map(e => { try { return JSON.parse(e.innerText); } catch { return null; } }).filter(Boolean)",
            )

            # Meta tags
            meta = await page.eval_on_selector_all(
                "meta[property], meta[name]",
                "els => els.reduce((acc, e) => { const key = e.getAttribute('property') || e.getAttribute('name'); const val = e.getAttribute('content'); if (key && val) acc[key] = val; return acc; }, {})",
            )

            return {"json_ld": json_ld[:5], "meta": meta}
        except Exception:
            return {}

    def _extract_price(self, text: str) -> str | None:
        """Extract price from text."""
        patterns = [
            r"[\d,]+(?:\.\d+)?\s*(?:EGP|جنيه|LE)",
            r"(?:EGP|جنيه|LE)\s*[\d,]+(?:\.\d+)?",
            r"[\d,]+(?:\.\d+)?\s*(?:M|K|m|k)\s*(?:EGP|جنيه)?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        return text[:100]


def get_scraper_tools():
    """Return CrewAI-compatible tools for web scraping."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class ScrapeUrlInput(BaseModel):
        url: str = Field(description="URL to scrape")

    class ScrapeUrlTool(BaseTool):
        name: str = "scrape_webpage"
        description: str = "Scrape a webpage and extract content, links, and structured data."
        args_schema: type = ScrapeUrlInput

        def _run(self, url: str) -> str:
            import asyncio
            skill = WebScraperSkill()
            result = asyncio.run(skill.scrape_url(url))
            return json.dumps(result, ensure_ascii=False)

    class ScrapeListingInput(BaseModel):
        url: str = Field(description="Real estate listing URL")

    class ScrapeListingTool(BaseTool):
        name: str = "scrape_listing"
        description: str = "Extract real estate listing data (price, location, features, images) from a URL."
        args_schema: type = ScrapeListingInput

        def _run(self, url: str) -> str:
            import asyncio
            skill = WebScraperSkill()
            result = asyncio.run(skill.extract_listing(url))
            return json.dumps(result, ensure_ascii=False)

    return [ScrapeUrlTool(), ScrapeListingTool()]
