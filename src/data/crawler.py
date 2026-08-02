"""
Web Crawler — زاحف الويب
=========================
Crawls real estate websites for property listings in El Sadat City.
Supports multiple sources: OLX, PropertyFinder, Aqarmap, developer sites.

Premium focus — only luxury properties, no social housing.
"""

import logging
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

logger = logging.getLogger("data.crawler")


# ---------------------------------------------------------------------------
# Supported Crawl Sources
# ---------------------------------------------------------------------------
CRAWL_SOURCES = {
    "olx": {
        "base_url": "https://www.olx.com.eg",
        "search_path": "/en/real-estate/elm-sadat-city",
        "type": "classifieds",
    },
    "propertyfinder": {
        "base_url": "https://www.propertyfinder.eg",
        "search_path": "/en/properties-for-sale-in-sadat-city.html",
        "type": "portal",
    },
    "aqarmap": {
        "base_url": "https://www.aqarmap.com.eg",
        "search_path": "/en/sadat-city",
        "type": "portal",
    },
}


# ---------------------------------------------------------------------------
# WebCrawler
# ---------------------------------------------------------------------------
class WebCrawler:
    """
    Crawls real estate websites for El Sadat City property listings.

    Features:
    - Rate limiting (1 req/sec per domain)
    - Deduplication by URL
    - Retry with exponential backoff
    - Premium property filtering (min 1.5M EGP)
    """

    def __init__(self, max_retries: int = 3, delay: float = 1.0):
        self.max_retries = max_retries
        self.delay = delay
        self._crawled_urls: set[str] = set()
        self._last_request_time: dict[str, float] = {}
        self._stats = {"pages_crawled": 0, "properties_found": 0, "errors": 0}

    # ------------------------------------------------------------------
    # Main Crawl Entry Points
    # ------------------------------------------------------------------
    def crawl_source(self, source: str, max_pages: int = 10) -> list[dict]:
        """
        Crawl a specific source for property listings.

        Args:
            source: Source key (olx, propertyfinder, aqarmap).
            max_pages: Maximum pages to crawl.

        Returns:
            List of extracted property dicts.
        """
        if source not in CRAWL_SOURCES:
            logger.error("Unknown crawl source: %s", source)
            return []

        config = CRAWL_SOURCES[source]
        base_url = config["base_url"]
        search_path = config["search_path"]

        logger.info("Starting crawl: %s (%s) — max %d pages", source, base_url, max_pages)
        properties = []

        for page in range(1, max_pages + 1):
            url = f"{base_url}{search_path}?page={page}" if page > 1 else f"{base_url}{search_path}"

            if url in self._crawled_urls:
                logger.debug("Skipping already-crawled URL: %s", url)
                continue

            try:
                self._rate_limit(base_url)
                html = self._fetch_page(url)
                if html:
                    page_properties = self._parse_listings(html, source, url)
                    properties.extend(page_properties)
                    self._crawled_urls.add(url)
                    self._stats["pages_crawled"] += 1
                    self._stats["properties_found"] += len(page_properties)
                    logger.info("Page %d: found %d properties", page, len(page_properties))
                else:
                    logger.warning("Empty response from %s", url)
                    break

            except Exception as e:
                logger.error("Crawl error on %s: %s", url, e)
                self._stats["errors"] += 1

        logger.info("Crawl complete: %s — %d properties from %d pages",
                     source, len(properties), self._stats["pages_crawled"])
        return properties

    def crawl_all_sources(self, max_pages_per_source: int = 5) -> list[dict]:
        """Crawl all configured sources."""
        all_properties = []
        for source in CRAWL_SOURCES:
            properties = self.crawl_source(source, max_pages=max_pages_per_source)
            all_properties.extend(properties)
            time.sleep(2)  # Pause between sources
        return all_properties

    # ------------------------------------------------------------------
    # Custom URL Crawl
    # ------------------------------------------------------------------
    def crawl_url(self, url: str) -> dict | None:
        """
        Crawl a single URL for property data.

        Args:
            url: URL to crawl.

        Returns:
            dict with extracted property data, or None.
        """
        if url in self._crawled_urls:
            logger.debug("URL already crawled: %s", url)
            return None

        parsed = urlparse(url)
        domain = parsed.netloc

        try:
            self._rate_limit(f"{parsed.scheme}://{domain}")
            html = self._fetch_page(url)
            if html:
                properties = self._parse_listings(html, "custom", url)
                self._crawled_urls.add(url)
                self._stats["pages_crawled"] += 1
                self._stats["properties_found"] += len(properties)
                return properties[0] if properties else None
        except Exception as e:
            logger.error("Crawl error on %s: %s", url, e)
            self._stats["errors"] += 1

        return None

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------
    def _fetch_page(self, url: str) -> str | None:
        """
        Fetch a page with retry logic.

        In production, this would use httpx or requests.
        Returns HTML string or None.
        """
        import os
        jina_key = os.getenv("JINA_API_KEY")

        for attempt in range(self.max_retries):
            try:
                # Try Jina Reader API first (better for JS-rendered pages)
                if jina_key:
                    return self._fetch_via_jina(url, jina_key)

                # Fallback to basic HTTP
                return self._fetch_via_http(url)

            except Exception as e:
                wait = self.delay * (2 ** attempt)
                logger.warning("Fetch attempt %d failed for %s: %s — retrying in %.1fs",
                               attempt + 1, url, e, wait)
                time.sleep(wait)

        logger.error("All fetch attempts failed for %s", url)
        return None

    def _fetch_via_jina(self, url: str, api_key: str) -> str | None:
        """Fetch page via Jina Reader API."""
        try:
            import httpx
            jina_url = f"https://r.jina.ai/{url}"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "X-Return-Format": "text",
            }
            response = httpx.get(jina_url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.text
        except ImportError:
            logger.warning("httpx not installed — falling back to basic HTTP")
        except Exception as e:
            logger.warning("Jina fetch failed: %s", e)
        return None

    def _fetch_via_http(self, url: str) -> str | None:
        """Fetch page via basic HTTP request."""
        try:
            import httpx
            response = httpx.get(url, timeout=30, follow_redirects=True)
            if response.status_code == 200:
                return response.text
        except ImportError:
            logger.warning("httpx not installed")
        except Exception as e:
            logger.warning("HTTP fetch failed: %s", e)
        return None

    def _parse_listings(self, html: str, source: str, url: str) -> list[dict]:
        """
        Parse property listings from HTML.

        This is a basic parser — production would use BeautifulSoup or parsel.
        """
        properties = []

        # Basic regex-based extraction for common patterns
        # Price patterns
        price_pattern = re.compile(r'(\d[\d,]+)\s*(?:جنيه|ج\.م|EGP|pound|مليون)', re.IGNORECASE)
        area_sqm_pattern = re.compile(r'(\d+)\s*(?:م²|م2|sqm|m\b)', re.IGNORECASE)
        bedroom_pattern = re.compile(r'(\d+)\s*(?:غرف|room|bedroom|نوم)', re.IGNORECASE)

        # Find price mentions
        price_pattern.findall(html)
        area_sqm_pattern.findall(html)
        bedroom_pattern.findall(html)

        # Extract text blocks that look like property listings
        # Look for sections with price + area together
        sections = re.split(r'<(?:div|article|section|li)[^>]*>', html)

        for section in sections:
            section_prices = price_pattern.findall(section)
            section_areas = area_sqm_pattern.findall(section)
            section_bedrooms = bedroom_pattern.findall(section)

            if section_prices:
                price_str = section_prices[0].replace(",", "")
                try:
                    price = int(price_str)
                    if price < 1_500_000:
                        continue  # Skip below minimum

                    prop = {
                        "source": source,
                        "source_url": url,
                        "price": price,
                        "price_currency": "EGP",
                        "area_sqm": int(section_areas[0]) if section_areas else None,
                        "bedrooms": int(section_bedrooms[0]) if section_bedrooms else None,
                        "property_type": self._guess_property_type(section),
                        "area": self._guess_area(section),
                        "crawled_at": datetime.now(timezone.utc).isoformat(),
                        "raw_html": section[:1000],
                    }
                    properties.append(prop)

                except (ValueError, IndexError):
                    continue

        return properties[:20]  # Limit per page

    def _guess_property_type(self, text: str) -> str | None:
        """Guess property type from text."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["فيلا", "villa", "تاون هاوس"]):
            return "فيلا"
        if any(kw in text_lower for kw in ["شقة", "apartment", "بنتهاوس"]):
            return "شقة فاخرة"
        if any(kw in text_lower for kw in ["محل", "shop", "store"]):
            return "محل تجاري"
        if any(kw in text_lower for kw in ["مكتب", "office"]):
            return "مكتب"
        if any(kw in text_lower for kw in ["أرض", "land", "plot"]):
            return "أرض استثمارية"
        return None

    def _guess_area(self, text: str) -> str | None:
        """Guess El Sadat City area from text."""
        area_keywords = {
            "المنطقة 7 الشريط المميز": ["منطقة 7", "المنطقة 7"],
            "المنطقة 9 الشريط المميز": ["منطقة 9", "المنطقة 9"],
            "Polaris Parks": ["بولاريس", "polaris"],
            "المنطقة الصناعية": ["الصناعية", "industrial"],
        }
        for area, keywords in area_keywords.items():
            for kw in keywords:
                if kw in text:
                    return area
        return None

    def _rate_limit(self, domain: str):
        """Enforce rate limiting per domain."""
        now = time.time()
        last = self._last_request_time.get(domain, 0)
        wait = self.delay - (now - last)
        if wait > 0:
            time.sleep(wait)
        self._last_request_time[domain] = time.time()

    @property
    def stats(self) -> dict:
        """Return crawl statistics."""
        return self._stats.copy()

    def reset(self):
        """Reset crawl state."""
        self._crawled_urls.clear()
        self._last_request_time.clear()
        self._stats = {"pages_crawled": 0, "properties_found": 0, "errors": 0}
