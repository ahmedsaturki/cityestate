"""
Google Search Skill — البحث المتقدم
====================================
Enhanced web search using multiple engines: Google, DuckDuckGo, Bing.
Supports location-based search, news, images, and real estate specific queries.
"""

import json
import logging
from urllib.parse import quote_plus

logger = logging.getLogger("skills.google_search")


class GoogleSearchSkill:
    """Multi-engine web search skill."""

    def __init__(self):
        self._engines = {
            "duckduckgo": self._search_duckduckgo,
            "google": self._search_google_scrape,
            "bing": self._search_bing,
        }

    async def search(
        self,
        query: str,
        engine: str = "duckduckgo",
        max_results: int = 10,
        location: str | None = None,
        language: str = "en",
    ) -> dict:
        """Search using specified engine."""
        search_fn = self._engines.get(engine, self._search_duckduckgo)
        return await search_fn(query, max_results, location, language)

    async def search_real_estate(
        self,
        query: str,
        area: str | None = None,
        max_results: int = 10,
    ) -> dict:
        """Specialized real estate search."""
        enhanced_query = f"{query} real estate Egypt"
        if area:
            enhanced_query += f" {area}"
        return await self.search(enhanced_query, max_results=max_results)

    async def search_news(self, query: str, max_results: int = 5) -> dict:
        """Search for recent news."""
        news_query = f"{query} news recent"
        return await self.search(news_query, max_results=max_results)

    async def _search_duckduckgo(
        self, query: str, max_results: int, location: str | None, language: str
    ) -> dict:
        """Search using DuckDuckGo (no API key required)."""
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return {
                    "engine": "duckduckgo",
                    "query": query,
                    "results": [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", ""),
                        }
                        for r in results
                    ],
                    "count": len(results),
                }
        except ImportError:
            return await self._search_google_scrape(query, max_results, location, language)
        except Exception as e:
            return {"engine": "duckduckgo", "error": str(e), "results": []}

    async def _search_google_scrape(
        self, query: str, max_results: int, location: str | None, language: str
    ) -> dict:
        """Search using Google scraping (fallback)."""
        try:
            from playwright.async_api import async_playwright

            search_url = f"https://www.google.com/search?q={quote_plus(query)}&hl={language}"

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(search_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

                results = []
                elements = await page.query_selector_all("div.g")
                for elem in elements[:max_results]:
                    try:
                        title_el = await elem.query_selector("h3")
                        link_el = await elem.query_selector("a")
                        snippet_el = await elem.query_selector("div.VwiC3b")

                        title = await title_el.inner_text() if title_el else ""
                        href = await link_el.get_attribute("href") if link_el else ""
                        snippet = await snippet_el.inner_text() if snippet_el else ""

                        if title and href:
                            results.append({"title": title, "url": href, "snippet": snippet})
                    except Exception as e:
                        logger.debug("Google search result error: %s", e)
                        continue

                await browser.close()
                return {
                    "engine": "google",
                    "query": query,
                    "results": results,
                    "count": len(results),
                }
        except Exception as e:
            return {"engine": "google", "error": str(e), "results": []}

    async def _search_bing(
        self, query: str, max_results: int, location: str | None, language: str
    ) -> dict:
        """Search using Bing scraping."""
        try:
            from playwright.async_api import async_playwright

            search_url = f"https://www.bing.com/search?q={quote_plus(query)}"

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(search_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

                results = []
                elements = await page.query_selector_all("li.b_algo")
                for elem in elements[:max_results]:
                    try:
                        title_el = await elem.query_selector("h2 a")
                        snippet_el = await elem.query_selector("div.b_caption p")

                        title = await title_el.inner_text() if title_el else ""
                        href = await title_el.get_attribute("href") if title_el else ""
                        snippet = await snippet_el.inner_text() if snippet_el else ""

                        if title and href:
                            results.append({"title": title, "url": href, "snippet": snippet})
                    except Exception as e:
                        logger.debug("Bing search result error: %s", e)
                        continue

                await browser.close()
                return {
                    "engine": "bing",
                    "query": query,
                    "results": results,
                    "count": len(results),
                }
        except Exception as e:
            return {"engine": "bing", "error": str(e), "results": []}


def get_search_tools():
    """Return CrewAI-compatible tools for web search."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class WebSearchInput(BaseModel):
        query: str = Field(description="Search query")
        engine: str = Field(default="duckduckgo", description="Search engine: duckduckgo, google, bing")
        max_results: int = Field(default=10, description="Max results to return")

    class EnhancedWebSearchTool(BaseTool):
        name: str = "enhanced_web_search"
        description: str = (
            "Search the web using multiple engines (Google, DuckDuckGo, Bing). "
            "Returns titles, URLs, and snippets. Great for market research, news, competitor analysis."
        )
        args_schema: type = WebSearchInput

        def _run(self, query: str, engine: str = "duckduckgo", max_results: int = 10) -> str:
            import asyncio
            skill = GoogleSearchSkill()
            result = asyncio.run(skill.search(query, engine=engine, max_results=max_results))
            return json.dumps(result, ensure_ascii=False)

    class RealEstateSearchInput(BaseModel):
        query: str = Field(description="Search query (e.g., 'apartments for sale')")
        area: str | None = Field(default=None, description="Area/location filter")

    class RealEstateSearchTool(BaseTool):
        name: str = "real_estate_search"
        description: str = "Search for real estate listings, market trends, and property news in Egypt."
        args_schema: type = RealEstateSearchInput

        def _run(self, query: str, area: str | None = None) -> str:
            import asyncio
            skill = GoogleSearchSkill()
            result = asyncio.run(skill.search_real_estate(query, area=area))
            return json.dumps(result, ensure_ascii=False)

    return [EnhancedWebSearchTool(), RealEstateSearchTool()]
