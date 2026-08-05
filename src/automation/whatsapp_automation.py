"""
WhatsApp Automation
===================
WhatsApp Web automation.
"""

import asyncio
import logging
import random

logger = logging.getLogger("cityestate.automation.whatsapp")


class WhatsAppAutomation:
    """Automate WhatsApp Web for property marketing."""

    def __init__(self):
        self._browser = None
        self._page = None
        self._pw = None

    async def start(self):
        """Start WhatsApp Web automation."""
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=False)
        context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 720},
        )
        self._page = await context.new_page()
        await self._page.goto("https://web.whatsapp.com", wait_until="networkidle")
        return self

    async def wait_for_login(self, timeout: int = 60):
        """Wait for user to scan QR code."""
        try:
            await self._page.wait_for_selector('[data-testid="chat-list"]', timeout=timeout * 1000)
            return {"status": "logged_in"}
        except Exception:
            return {"status": "timeout"}

    async def send_message(self, phone: str, message: str) -> dict:
        """Send a message to a phone number."""
        try:
            from urllib.parse import quote
            encoded_msg = quote(message)
            url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}"
            await self._page.goto(url, wait_until="networkidle")
            await asyncio.sleep(2)
            await self._page.click('[data-testid="send"]', timeout=5000)
            return {"status": "sent", "phone": phone}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def send_property_message(self, phone: str, property_data: dict) -> dict:
        """Send a property listing message."""
        message = f"""🏢 *{property_data.get('title', 'عقار متاح')}*

📍 {property_data.get('location', '')}
💰 {property_data.get('price', '')} جنيه
📐 {property_data.get('area', '')} م²

📞 للتواصل: {property_data.get('phone', '')}"""
        return await self.send_message(phone, message)

    async def send_bulk_messages(self, contacts: list[dict], message_template: str) -> list[dict]:
        """Send messages to multiple contacts."""
        results = []
        for contact in contacts:
            personalized = message_template
            for key, value in contact.items():
                personalized = personalized.replace(f"{{{key}}}", str(value))
            result = await self.send_message(contact.get("phone", ""), personalized)
            results.append(result)
            await asyncio.sleep(random.uniform(3, 7))
        return results

    async def get_contacts(self) -> list[dict]:
        """Get WhatsApp contacts."""
        try:
            contacts = await self._page.evaluate("""
                () => {
                    const items = document.querySelectorAll('[data-testid="cell-frame-container"]');
                    return Array.from(items).slice(0, 100).map(item => ({
                        name: item.querySelector('[data-testid="cell-frame-title"]')?.textContent || '',
                        phone: item.querySelector('[data-testid="cell-frame-secondary"]')?.textContent || '',
                    }));
                }
            """)
            return contacts
        except Exception:
            return []

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
        self._page = None
        self._pw = None
