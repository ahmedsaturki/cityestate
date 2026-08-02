"""
Web Tools
===========
"""

import json
import logging

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)




class WebSearchInput(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(default=5, description="Max results to return")



class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo (no API key required)."""
    name: str = "web_search"
    description: str = (
        "Search the web for real estate news, market trends, developer announcements, "
        "or any topic. Returns title, URL, and snippet for each result."
    )
    args_schema: type = WebSearchInput

    def _run(self, query: str, max_results: int = 5) -> str:
        try:
            from src.services.mcp_service import get_mcp_service
            mcp = get_mcp_service()
            results = mcp.web_search(query, max_results=max_results)
            return json.dumps({"query": query, "results": results}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Content Save Tool
# ---------------------------------------------------------------------------

class WebCrawlerInput(BaseModel):
    source: str | None = Field(default=None, description="Crawl source: 'olx', 'propertyfinder', 'aqarmap'")
    url: str | None = Field(default=None, description="Custom URL to crawl")
    max_pages: int = Field(default=5, description="Max pages to crawl")


# ---------------------------------------------------------------------------
# Web Crawler Tool
# ---------------------------------------------------------------------------

class WebCrawlerTool(BaseTool):
    """Crawl real estate websites for property listings."""
    name: str = "web_crawler"
    description: str = (
        "Crawl real estate websites (OLX, PropertyFinder, Aqarmap) for "
        "El Sadat City property listings. Returns extracted property data."
    )
    args_schema: type = WebCrawlerInput

    def _run(self, source: str | None = None, url: str | None = None, max_pages: int = 5) -> str:
        try:
            from src.data.crawler import WebCrawler
            crawler = WebCrawler()

            if url:
                result = crawler.crawl_url(url)
                return json.dumps(result if result else {"message": "No properties found"}, ensure_ascii=False, default=str)
            elif source:
                results = crawler.crawl_source(source, max_pages=max_pages)
                return json.dumps({"count": len(results), "properties": results[:10]}, ensure_ascii=False, default=str)
            else:
                return json.dumps({"error": "Provide source or url"})
        except Exception as e:
            logger.error("Web crawl failed: %s", e)
            return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Data Enrichment Input
# ---------------------------------------------------------------------------
