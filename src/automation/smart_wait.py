"""
Smart Wait System - State-Based Verification for Browser Automation
====================================================================
Replaces blind time-based waits with intelligent state verification.

Every wait operation must verify a REAL RESULT before proceeding.
No more asyncio.sleep() — only verified state transitions.

Usage:
    from src.automation.smart_wait import SmartWait
    waiter = SmartWait(page)
    await waiter.wait_for_login("whatsapp")
    await waiter.wait_for_element_visible('div[data-testid="chat-list"]')
"""

import asyncio
import logging
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

logger = logging.getLogger("automation.smart_wait")


class WaitResult(Enum):
    """Result of a wait operation."""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ELEMENT_NOT_FOUND = "element_not_found"
    CONDITION_NOT_MET = "condition_not_met"
    RETRY_EXHAUSTED = "retry_exhausted"


class SmartWait:
    """Intelligent wait system that verifies actual state before proceeding.

    Core principles:
    1. Never wait for time — wait for STATE
    2. Verify success before moving to next step
    3. Retry with exponential backoff on transient failures
    4. Log every state transition for debugging
    """

    def __init__(self, page: Any, default_timeout: int = 30000) -> None:
        """Initialize SmartWait with a Playwright page.

        Args:
            page: Playwright Page object
            default_timeout: Default timeout in milliseconds (30 seconds)
        """
        self.page = page
        self.default_timeout = default_timeout
        self._state_history: list[dict] = []
        self._retry_count = 0

    def _log_state(self, operation: str, result: WaitResult, details: str = "") -> None:
        """Log state transition for debugging."""
        entry = {
            "timestamp": time.time(),
            "operation": operation,
            "result": result.value,
            "details": details,
            "retry_count": self._retry_count,
        }
        self._state_history.append(entry)
        logger.info(
            "[%s] %s — %s%s",
            operation, result.value, details,
            f" (retry #{self._retry_count})" if self._retry_count else ""
        )

    async def wait_for_login(self, platform: str, timeout: int = 120000) -> WaitResult:
        """Wait for user to complete login and verify it happened.

        Args:
            platform: "whatsapp" or "facebook"
            timeout: Max wait time in ms (default 2 minutes)

        Returns:
            WaitResult indicating success or failure
        """
        self._retry_count = 0
        start_time = time.time()
        timeout_sec = timeout / 1000

        # Platform-specific success indicators
        indicators = {
            "whatsapp": {
                "selectors": [
                    'div[data-testid="chat-list"]',
                    'div[data-testid="side"]',
                    '#side',
                    'div[role="application"]',
                ],
                "url_contains": "web.whatsapp.com",
                "negative_indicators": [
                    'div[data-testid="qrcode"]',  # QR code still showing
                    'canvas',  # QR canvas
                ],
            },
            "facebook": {
                "selectors": [
                    'div[role="feed"]',
                    'div[role="navigation"]',
                    '[data-pagelet="FeedUnit"]',
                    'div[aria-label="News Feed"]',
                ],
                "url_contains": "facebook.com",
                "negative_indicators": [
                    'input[name="email"]',  # Login form still showing
                    'input[name="pass"]',
                    '#loginform',
                ],
            },
        }

        config = indicators.get(platform)
        if not config:
            logger.error("Unknown platform: %s", platform)
            return WaitResult.ELEMENT_NOT_FOUND

        print(f"  [SMART WAIT] Waiting for {platform} login...")
        print(f"  Timeout: {timeout_sec:.0f} seconds")

        while (time.time() - start_time) < timeout_sec:
            # Check for negative indicators first (things that mean NOT logged in)
            for neg_selector in config["negative_indicators"]:
                try:
                    elem = await self.page.query_selector(neg_selector)
                    if elem and await elem.is_visible():
                        elapsed = time.time() - start_time
                        print(f"  [WAITING] Login form still visible ({elapsed:.0f}s elapsed)...")
                        await asyncio.sleep(2)
                        continue
                except Exception as e:
                    logger.debug("Smart wait loop error: %s", e)

            # Check for positive indicators (things that mean logged in)
            for selector in config["selectors"]:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem and await elem.is_visible():
                        # Verify URL is correct
                        current_url = self.page.url
                        if config["url_contains"] in current_url:
                            self._log_state(
                                "wait_for_login",
                                WaitResult.SUCCESS,
                                f"Platform: {platform}, URL: {current_url}"
                            )
                            print(f"  [SUCCESS] {platform} login verified!")
                            return WaitResult.SUCCESS
                except Exception as e:
                    logger.debug("Smart wait login check error: %s", e)

            # Also check URL as a fallback
            try:
                current_url = self.page.url
                if config["url_contains"] in current_url and "login" not in current_url.lower():
                    # URL looks right, but we need to verify content
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                logger.debug("Smart wait URL check error: %s", e)

            # Wait before next check
            await asyncio.sleep(2)
            self._retry_count += 1

        # Timeout reached
        self._log_state(
            "wait_for_login",
            WaitResult.TIMEOUT,
            f"Platform: {platform}, waited {timeout_sec:.0f}s"
        )
        print(f"  [TIMEOUT] {platform} login not detected after {timeout_sec:.0f} seconds")
        return WaitResult.TIMEOUT

    async def wait_for_element_visible(
        self,
        selector: str,
        timeout: int | None = None,
        description: str = ""
    ) -> WaitResult:
        """Wait for an element to be visible on the page.

        Args:
            selector: CSS selector to wait for
            timeout: Timeout in ms (uses default if None)
            description: Human-readable description for logging

        Returns:
            WaitResult indicating success or failure
        """
        timeout = timeout or self.default_timeout
        timeout_sec = timeout / 1000
        start_time = time.time()
        desc = description or selector

        print(f"  [SMART WAIT] Waiting for: {desc}")

        while (time.time() - start_time) < timeout_sec:
            try:
                elem = await self.page.query_selector(selector)
                if elem:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        self._log_state(
                            "wait_for_element",
                            WaitResult.SUCCESS,
                            f"Selector: {selector}"
                        )
                        print(f"  [SUCCESS] Element found: {desc}")
                        return WaitResult.SUCCESS
            except Exception as e:
                logger.debug("Element check error: %s", e)

            await asyncio.sleep(0.5)

        self._log_state(
            "wait_for_element",
            WaitResult.TIMEOUT,
            f"Selector: {selector}, waited {timeout_sec:.0f}s"
        )
        print(f"  [TIMEOUT] Element not found: {desc}")
        return WaitResult.TIMEOUT

    async def wait_for_element_hidden(
        self,
        selector: str,
        timeout: int | None = None,
        description: str = ""
    ) -> WaitResult:
        """Wait for an element to become hidden/invisible.

        Useful for waiting for loading spinners, modals, etc.
        """
        timeout = timeout or self.default_timeout
        timeout_sec = timeout / 1000
        start_time = time.time()
        desc = description or selector

        print(f"  [SMART WAIT] Waiting for hidden: {desc}")

        while (time.time() - start_time) < timeout_sec:
            try:
                elem = await self.page.query_selector(selector)
                if not elem:
                    # Element gone from DOM
                    self._log_state("wait_for_hidden", WaitResult.SUCCESS, f"Selector: {selector}")
                    print(f"  [SUCCESS] Element hidden: {desc}")
                    return WaitResult.SUCCESS

                is_visible = await elem.is_visible()
                if not is_visible:
                    self._log_state("wait_for_hidden", WaitResult.SUCCESS, f"Selector: {selector}")
                    print(f"  [SUCCESS] Element hidden: {desc}")
                    return WaitResult.SUCCESS
            except Exception:
                # Element might have been removed
                self._log_state("wait_for_hidden", WaitResult.SUCCESS, "Element removed")
                return WaitResult.SUCCESS

            await asyncio.sleep(0.5)

        self._log_state(
            "wait_for_hidden",
            WaitResult.TIMEOUT,
            f"Selector: {selector}, waited {timeout_sec:.0f}s"
        )
        return WaitResult.TIMEOUT

    async def wait_for_text_present(
        self,
        text: str,
        timeout: int | None = None,
        description: str = ""
    ) -> WaitResult:
        """Wait for specific text to appear on the page.

        Useful for verifying success messages, error messages, etc.
        """
        timeout = timeout or self.default_timeout
        timeout_sec = timeout / 1000
        start_time = time.time()
        desc = description or f"text='{text}'"

        print(f"  [SMART WAIT] Waiting for text: {desc}")

        while (time.time() - start_time) < timeout_sec:
            try:
                page_text = await self.page.inner_text("body")
                if text.lower() in page_text.lower():
                    self._log_state("wait_for_text", WaitResult.SUCCESS, f"Text: {text}")
                    print(f"  [SUCCESS] Text found: {desc}")
                    return WaitResult.SUCCESS
            except Exception as e:
                logger.debug("Smart wait text check error: %s", e)

            await asyncio.sleep(0.5)

        self._log_state(
            "wait_for_text",
            WaitResult.TIMEOUT,
            f"Text: {text}, waited {timeout_sec:.0f}s"
        )
        return WaitResult.TIMEOUT

    async def wait_for_send_success(
        self,
        phone: str,
        timeout: int = 15000
    ) -> WaitResult:
        """Wait for WhatsApp message to be sent (double checkmark).

        Verifies the message was actually sent, not just typed.
        """
        timeout_sec = timeout / 1000
        start_time = time.time()

        print(f"  [SMART WAIT] Verifying message sent to {phone}...")

        # Check for sent indicators
        sent_indicators = [
            'span[data-testid="msg-dblcheck"]',  # Double checkmark
            'span[data-testid="msg-check"]',       # Single checkmark
            'span[data-icon="msg-dblcheck"]',      # Alternative selector
            'span[data-icon="msg-check"]',         # Alternative selector
        ]

        # Check for error indicators
        error_indicators = [
            'div[data-testid="popup-controls"]',   # Error popup
            'span[data-testid="error-icon"]',       # Error icon
        ]

        while (time.time() - start_time) < timeout_sec:
            # Check for errors first
            for selector in error_indicators:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem and await elem.is_visible():
                        self._log_state(
                            "wait_for_send",
                            WaitResult.CONDITION_NOT_MET,
                            f"Error popup detected for {phone}"
                        )
                        print(f"  [ERROR] Send error detected for {phone}")
                        return WaitResult.CONDITION_NOT_MET
                except Exception as e:
                    logger.debug("Smart wait send error check: %s", e)

            # Check for success indicators
            for selector in sent_indicators:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem:
                        self._log_state(
                            "wait_for_send",
                            WaitResult.SUCCESS,
                            f"Message sent to {phone}"
                        )
                        print(f"  [SUCCESS] Message confirmed sent to {phone}")
                        return WaitResult.SUCCESS
                except Exception as e:
                    logger.debug("Smart wait send check error: %s", e)

            await asyncio.sleep(0.5)

        self._log_state(
            "wait_for_send",
            WaitResult.TIMEOUT,
            f"Send verification timed out for {phone}"
        )
        return WaitResult.TIMEOUT

    async def wait_for_group_loaded(self, timeout: int = 10000) -> WaitResult:
        """Wait for a Facebook Group to fully load its posts."""
        timeout_sec = timeout / 1000
        start_time = time.time()

        print("  [SMART WAIT] Waiting for group content to load...")

        while (time.time() - start_time) < timeout_sec:
            try:
                # Check for feed/posts
                posts = await self.page.query_selector_all('div[role="article"]')
                if len(posts) > 0:
                    # Also check for any loading indicators
                    loading = await self.page.query_selector('[role="progressbar"]')
                    if loading and await loading.is_visible():
                        await asyncio.sleep(1)
                        continue

                    self._log_state(
                        "wait_for_group",
                        WaitResult.SUCCESS,
                        f"Found {len(posts)} posts"
                    )
                    print(f"  [SUCCESS] Group loaded with {len(posts)} posts")
                    return WaitResult.SUCCESS
            except Exception as e:
                logger.debug("Smart wait group check error: %s", e)

            await asyncio.sleep(1)

        self._log_state(
            "wait_for_group",
            WaitResult.TIMEOUT,
            "Group content did not load"
        )
        return WaitResult.TIMEOUT

    async def wait_for_chat_open(self, phone: str, timeout: int = 15000) -> WaitResult:
        """Wait for a WhatsApp chat to open after clicking a contact."""
        timeout_sec = timeout / 1000
        start_time = time.time()

        print(f"  [SMART WAIT] Waiting for chat to open with {phone}...")

        while (time.time() - start_time) < timeout_sec:
            try:
                # Check for message input box
                input_box = await self.page.query_selector(
                    'div[data-testid="conversation-compose-box-input"]'
                )
                if input_box and await input_box.is_visible():
                    # Also verify we're in the right chat
                    header = await self.page.query_selector(
                        'div[data-testid="conversation-header"]'
                    )
                    if header:
                        header_text = await header.inner_text()
                        if phone in header_text or phone.lstrip("+") in header_text:
                            self._log_state(
                                "wait_for_chat",
                                WaitResult.SUCCESS,
                                f"Chat open with {phone}"
                            )
                            print(f"  [SUCCESS] Chat open with {phone}")
                            return WaitResult.SUCCESS
            except Exception as e:
                logger.debug("Smart wait chat check error: %s", e)

            await asyncio.sleep(0.5)

        self._log_state(
            "wait_for_chat",
            WaitResult.TIMEOUT,
            f"Chat did not open with {phone}"
        )
        return WaitResult.TIMEOUT

    async def retry_with_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        description: str = ""
    ) -> tuple[bool, Any]:
        """Retry a function with exponential backoff.

        Args:
            func: Async function to retry
            max_retries: Maximum number of retries
            base_delay: Initial delay between retries (seconds)
            max_delay: Maximum delay between retries (seconds)
            description: Description for logging

        Returns:
            Tuple of (success, result)
        """
        desc = description or func.__name__
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = await func()
                if attempt > 0:
                    self._log_state(
                        "retry",
                        WaitResult.SUCCESS,
                        f"{desc} succeeded on attempt {attempt + 1}"
                    )
                    print(f"  [RETRY SUCCESS] {desc} succeeded on attempt {attempt + 1}")
                return True, result
            except Exception as e:
                last_error = e
                self._retry_count = attempt + 1

                if attempt < max_retries:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    self._log_state(
                        "retry",
                        WaitResult.RETRY_EXHAUSTED,
                        f"{desc} failed: {e}, retrying in {delay:.1f}s"
                    )
                    print(f"  [RETRY] {desc} failed: {e}")
                    print(f"    Retrying in {delay:.1f}s (attempt {attempt + 2}/{max_retries + 1})")
                    await asyncio.sleep(delay)

        self._log_state(
            "retry",
            WaitResult.RETRY_EXHAUSTED,
            f"{desc} failed after {max_retries + 1} attempts: {last_error}"
        )
        print(f"  [FAILED] {desc} failed after {max_retries + 1} attempts")
        return False, last_error

    async def scroll_and_load(self, scroll_count: int = 5, scroll_delay: float = 1.0) -> int:
        """Scroll down the page to load more content.

        Returns:
            Number of new elements found after scrolling
        """
        initial_count = 0
        try:
            articles = await self.page.query_selector_all('div[role="article"]')
            initial_count = len(articles)
        except Exception as e:
            logger.debug("Smart wait initial article count error: %s", e)

        print("  [SMART WAIT] Scrolling to load more content...")

        for i in range(scroll_count):
            try:
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(scroll_delay)
            except Exception:
                break

        final_count = 0
        try:
            articles = await self.page.query_selector_all('div[role="article"]')
            final_count = len(articles)
        except Exception as e:
            logger.debug("Smart wait final article count error: %s", e)

        new_items = final_count - initial_count
        print(f"  [SCROLL] Found {final_count} items ({new_items} new)")
        return final_count

    def get_state_history(self) -> list[dict]:
        """Get the full state transition history for debugging."""
        return self._state_history.copy()

    def clear_state_history(self) -> None:
        """Clear state history."""
        self._state_history.clear()
