"""
MCP Service — خدمة التكامل الموحدة
====================================
Unified interface for WhatsApp and web search operations.
Provides a single entry point for agents and scheduler jobs.
"""

import logging

logger = logging.getLogger("services.mcp")


class MCPService:
    """
    Unified MCP service integrating:
    - WhatsApp messaging (via WhatsAppExpert)
    - Web search (via DuckDuckGo)
    """

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._whatsapp = None

    def _get_whatsapp(self):
        """Lazy-init WhatsAppExpert."""
        if self._whatsapp is None:
            from src.automation.experts.whatsapp import WhatsAppExpert
            self._whatsapp = WhatsAppExpert(headless=self._headless)
        return self._whatsapp

    def _get_facebook(self):
        """DEPRECATED: FacebookExpert was removed in Phase 5."""
        raise NotImplementedError("FacebookExpert removed in Phase 5 Meta API cleanup")

    # ------------------------------------------------------------------
    # WhatsApp
    # ------------------------------------------------------------------
    def send_whatsapp(self, phone: str, message: str, dry_run: bool = False) -> dict:
        """
        Send a WhatsApp message.

        Args:
            phone: Recipient phone number (E.164 format preferred).
            message: Message body text.
            dry_run: If True, log but don't actually send.

        Returns:
            dict with status, phone, and optional error.
        """
        if dry_run:
            logger.info("[DRY RUN] Would send WhatsApp to %s: %s", phone, message[:80])
            return {"status": "dry_run", "phone": phone}

        try:
            import asyncio
            expert = self._get_whatsapp()
            # send_whatsapp_message is async; run it in the event loop
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    expert.send_whatsapp_message(to=phone, message=message)
                )
                return {"status": "sent" if result else "failed", "phone": phone}
            finally:
                loop.close()
        except Exception as e:
            logger.error("WhatsApp send failed to %s: %s", phone, e)
            return {"status": "error", "phone": phone, "error": str(e)}

    def send_whatsapp_batch(
        self, recipients: list[dict], dry_run: bool = False
    ) -> list[dict]:
        """
        Send WhatsApp messages to multiple recipients.

        Args:
            recipients: List of {"phone": str, "message": str}.
            dry_run: If True, log but don't send.

        Returns:
            List of result dicts.
        """
        results = []
        for r in recipients:
            result = self.send_whatsapp(r["phone"], r["message"], dry_run=dry_run)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Facebook (DEPRECATED — FacebookExpert removed in Phase 5)
    # ------------------------------------------------------------------
    def scrape_facebook_groups(
        self, groups: list[str] | None = None, max_groups: int = 10
    ) -> dict:
        """DEPRECATED: FacebookExpert was removed in Phase 5."""
        logger.warning("scrape_facebook_groups is deprecated — FacebookExpert removed in Phase 5")
        return {"status": "deprecated", "leads_found": 0, "message": "FacebookExpert removed"}

    def get_facebook_leads(self, limit: int = 50) -> list[dict]:
        """DEPRECATED: FacebookExpert was removed in Phase 5."""
        logger.warning("get_facebook_leads is deprecated — FacebookExpert removed in Phase 5")
        return []

    # ------------------------------------------------------------------
    # Web Search (DuckDuckGo)
    # ------------------------------------------------------------------
    def web_search(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Search the web using DuckDuckGo (no API key required).

        Args:
            query: Search query string.
            max_results: Maximum results to return.

        Returns:
            List of dicts with title, url, snippet.
        """
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return [
                    {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
                    for r in results
                ]
        except ImportError:
            logger.warning("duckduckgo_search not installed. Install with: pip install duckduckgo-search")
            return []
        except Exception as e:
            logger.error("Web search failed for '%s': %s", query, e)
            return []

    # ------------------------------------------------------------------
    # Convenience: Combined operations
    # ------------------------------------------------------------------
    def search_and_notify(self, query: str, phone: str, dry_run: bool = False) -> dict:
        """
        Search the web and send results via WhatsApp.

        Args:
            query: Search query.
            phone: Recipient phone number.
            dry_run: If True, don't actually send.

        Returns:
            dict with search results and send status.
        """
        results = self.web_search(query, max_results=3)
        if not results:
            return {"status": "no_results", "query": query}

        # Build a concise message from results
        lines = [f"نتائج البحث عن: {query}\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}\n   {r['url']}\n")
        message = "\n".join(lines)

        send_result = self.send_whatsapp(phone, message, dry_run=dry_run)
        return {
            "status": "completed",
            "query": query,
            "results_count": len(results),
            "send_result": send_result,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_service: MCPService | None = None


def get_mcp_service(headless: bool = True) -> MCPService:
    """Get or create the MCP service singleton."""
    global _service
    if _service is None:
        _service = MCPService(headless=headless)
    return _service
