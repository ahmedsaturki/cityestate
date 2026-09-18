"""
Browser Manager
===============
Centralized browser automation manager.
"""

import logging
import os
import time

logger = logging.getLogger("cityestate.automation.browser_manager")


class BrowserManager:
    """Centralized browser manager for all automation tasks."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._browser = None
        self._context = None
        self._page = None
        self._pw = None

    async def start(self):
        """Start the browser."""
        from playwright.async_api import async_playwright
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            locale="en-US",
            timezone_id="Africa/Cairo",
        )
        self._page = await self._context.new_page()
        return self

    async def get_page(self):
        """Get the current page."""
        if self._page is None:
            await self.start()
        return self._page

    async def navigate(self, url: str) -> dict:
        """Navigate to a URL."""
        page = await self.get_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            return {"status": "success", "url": url, "title": await page.title()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def screenshot(self, filename: str | None = None) -> str:
        """Take a screenshot."""
        page = await self.get_page()
        if filename is None:
            filename = f"output/screenshots/screenshot_{time.time():.0f}.png"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        await page.screenshot(path=filename, full_page=True)
        return filename

    async def click(self, selector: str) -> dict:
        """Click an element."""
        page = await self.get_page()
        try:
            await page.click(selector, timeout=5000)
            return {"status": "clicked", "selector": selector}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def type_text(self, selector: str, text: str) -> dict:
        """Type text into an input."""
        page = await self.get_page()
        try:
            await page.fill(selector, text)
            return {"status": "typed", "selector": selector}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def extract_text(self, selector: str) -> str:
        """Extract text from an element."""
        page = await self.get_page()
        try:
            return await page.text_content(selector)
        except Exception:
            return ""

    async def wait_for(self, selector: str, timeout: int = 10000) -> bool:
        """Wait for an element to appear."""
        page = await self.get_page()
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False

    async def scroll_to_bottom(self):
        """Scroll to the bottom of the page."""
        page = await self.get_page()
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    async def close(self):
        """Close the browser."""
        try:
            if self._browser:
                await self._browser.close()
        except Exception as e:
            logger.debug("Failed to close browser: %s", e)
        try:
            if self._pw:
                await self._pw.stop()
        except Exception as e:
            logger.debug("Failed to stop playwright: %s", e)
        self._browser = None
        self._context = None
        self._page = None
        self._pw = None

    async def __aenter__(self):
        return await self.start()

    async def __aexit__(self, *args):
        await self.close()
