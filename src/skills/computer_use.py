"""
Computer Use Skill — التحكم في سطح المكتب
==========================================
Allows agents to interact with the desktop: take screenshots, click, type, scroll.
Uses Playwright for browser automation and PIL/pyautogui for desktop interaction.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("skills.computer_use")


class ComputerUseSkill:
    """Desktop interaction skill for agents."""

    def __init__(self):
        self._browser = None
        self._page = None

    async def take_screenshot(self, save_path: str | None = None) -> dict:
        """Take a screenshot of the current screen."""
        try:
            import io

            from PIL import ImageGrab

            screenshot = ImageGrab.grab()
            if save_path:
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                screenshot.save(save_path)
                return {"status": "saved", "path": save_path, "size": screenshot.size}

            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG")
            return {
                "status": "captured",
                "size": screenshot.size,
                "bytes": len(buffer.getvalue()),
            }
        except ImportError:
            return {"status": "error", "error": "Pillow not installed. Run: pip install Pillow"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def take_browser_screenshot(self, url: str, save_path: str | None = None) -> dict:
        """Take a screenshot of a webpage."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(2000)

                if save_path:
                    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=save_path, full_page=True)
                    await browser.close()
                    return {"status": "saved", "path": save_path, "url": url}

                screenshot = await page.screenshot(full_page=True)
                await browser.close()
                return {
                    "status": "captured",
                    "url": url,
                    "bytes": len(screenshot),
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def click_element(self, selector: str, page_url: str | None = None) -> dict:
        """Click an element on a webpage."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                if page_url:
                    await page.goto(page_url, wait_until="networkidle")

                await page.click(selector)
                await page.wait_for_timeout(1000)
                await browser.close()
                return {"status": "clicked", "selector": selector}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def type_text(self, selector: str, text: str, page_url: str | None = None) -> dict:
        """Type text into an input field."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                if page_url:
                    await page.goto(page_url, wait_until="networkidle")

                await page.fill(selector, text)
                await browser.close()
                return {"status": "typed", "selector": selector, "text": text[:50]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def scroll_page(self, direction: str = "down", amount: int = 500) -> dict:
        """Scroll the page up or down."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                if direction == "down":
                    await page.mouse.wheel(0, amount)
                else:
                    await page.mouse.wheel(0, -amount)

                await browser.close()
                return {"status": "scrolled", "direction": direction, "amount": amount}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def extract_page_content(self, url: str) -> dict:
        """Extract all text content from a webpage."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle")

                title = await page.title()
                content = await page.inner_text("body")
                links = await page.eval_on_selector_all("a", "els => els.map(e => ({text: e.innerText, href: e.href}))")

                await browser.close()
                return {
                    "status": "extracted",
                    "url": url,
                    "title": title,
                    "content": content[:5000],
                    "links": links[:50],
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# CrewAI Tool wrapper
def get_computer_use_tools():
    """Return CrewAI-compatible tools for computer use."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class ScreenshotInput(BaseModel):
        url: str | None = Field(default=None, description="URL to screenshot (browser)")
        save_path: str | None = Field(default=None, description="Path to save screenshot")

    class ScreenshotTool(BaseTool):
        name: str = "take_screenshot"
        description: str = "Take a screenshot of a webpage or the desktop. Provide url for browser screenshot."
        args_schema: type = ScreenshotInput

        def _run(self, url: str | None = None, save_path: str | None = None) -> str:
            import asyncio
            skill = ComputerUseSkill()
            if url:
                result = asyncio.run(skill.take_browser_screenshot(url, save_path))
            else:
                result = asyncio.run(skill.take_screenshot(save_path))
            return json.dumps(result, ensure_ascii=False)

    class ExtractPageInput(BaseModel):
        url: str = Field(description="URL to extract content from")

    class ExtractPageTool(BaseTool):
        name: str = "extract_page_content"
        description: str = "Extract all text content and links from a webpage."
        args_schema: type = ExtractPageInput

        def _run(self, url: str) -> str:
            import asyncio
            skill = ComputerUseSkill()
            result = asyncio.run(skill.extract_page_content(url))
            return json.dumps(result, ensure_ascii=False)

    return [ScreenshotTool(), ExtractPageTool()]
