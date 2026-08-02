"""
Human Simulator
===============
Simulate human behavior for anti-detection.
"""

import asyncio
import random


class HumanSimulator:
    """Simulate human-like behavior for web automation."""

    def __init__(self):
        self.typing_speed_min = 0.05
        self.typing_speed_max = 0.15
        self.scroll_pause_min = 0.5
        self.scroll_pause_max = 2.0

    async def human_type(self, page, selector: str, text: str):
        """Type like a human with variable speed."""
        await page.click(selector)
        for char in text:
            await page.keyboard.type(char)
            delay = random.uniform(self.typing_speed_min, self.typing_speed_max)
            await asyncio.sleep(delay)

    async def human_click(self, page, selector: str):
        """Click with slight delay and position variation."""
        element = await page.query_selector(selector)
        if element:
            box = await element.bounding_box()
            if box:
                x = box["x"] + random.uniform(5, box["width"] - 5)
                y = box["y"] + random.uniform(5, box["height"] - 5)
                await page.mouse.move(x, y, steps=random.randint(5, 15))
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await page.mouse.click(x, y)

    async def human_scroll(self, page, direction: str = "down", amount: int | None = None):
        """Scroll like a human."""
        if amount is None:
            amount = random.randint(300, 800)

        if direction == "up":
            amount = -amount

        await page.evaluate(f"window.scrollBy(0, {amount})")
        await asyncio.sleep(random.uniform(self.scroll_pause_min, self.scroll_pause_max))

    async def random_mouse_movement(self, page):
        """Move mouse randomly on the page."""
        viewport = page.viewport_size
        if viewport:
            for _ in range(random.randint(3, 7)):
                x = random.randint(0, viewport["width"])
                y = random.randint(0, viewport["height"])
                await page.mouse.move(x, y, steps=random.randint(10, 30))
                await asyncio.sleep(random.uniform(0.2, 0.8))

    async def simulate_reading(self, page, duration: float | None = None):
        """Simulate reading content."""
        if duration is None:
            duration = random.uniform(2, 5)
        await asyncio.sleep(duration)

    async def human_form_fill(self, page, fields: dict):
        """Fill a form like a human."""
        for selector, value in fields.items():
            await self.human_type(page, selector, value)
            await asyncio.sleep(random.uniform(0.5, 1.5))

    def random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Get a random delay."""
        return random.uniform(min_sec, max_sec)
