"""
Playwright Selector Registry
=============================
Centralized selector management for WhatsApp and Facebook automation.
Provides fallback selectors and version tracking for DOM resilience.

When a primary selector fails, the system automatically tries fallbacks.
This makes automation more robust against UI changes.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("automation.selectors")


@dataclass
class SelectorChain:
    """A chain of selectors to try in order."""
    name: str
    primary: str
    fallbacks: list[str] = field(default_factory=list)
    description: str = ""
    last_working: str | None = None
    failure_count: int = 0

    def all_selectors(self) -> list[str]:
        """Return all selectors in order of priority."""
        return [self.primary] + self.fallbacks


# ---------------------------------------------------------------------------
# WhatsApp Selectors
# ---------------------------------------------------------------------------
WHATSAPP_SELECTORS = {
    # Message composition
    "message_input": SelectorChain(
        name="message_input",
        primary='div[data-testid="conversation-compose-box-input"]',
        fallbacks=[
            'div[contenteditable="true"][data-tab="10"]',
            'div[role="textbox"][contenteditable="true"]',
            'footer div[contenteditable="true"]',
            'div.compose-box div[contenteditable="true"]',
        ],
        description="WhatsApp message input box",
    ),
    "send_button": SelectorChain(
        name="send_button",
        primary='span[data-testid="send"]',
        fallbacks=[
            'button[data-testid="send"]',
            'div[role="button"][aria-label*="Send"]',
            'span[role="button"][aria-label*="Send"]',
            'div.compose-box button',
        ],
        description="WhatsApp send button",
    ),

    # Chat list
    "unread_badge": SelectorChain(
        name="unread_badge",
        primary='span[data-testid="icon-unread-count"]',
        fallbacks=[
            'span[aria-label*=" unread"]',
            'div[aria-label*="unread message"]',
            'span._1Vzj',
            'div.matched-text ~ span:not(:empty)',
        ],
        description="Unread message count badge",
    ),
    "chat_header_name": SelectorChain(
        name="chat_header_name",
        primary='div[data-testid="chat-header"] span[title]',
        fallbacks=[
            'div[data-testid="chat-header"] span',
            'header span[title]',
            'div.chat-header span:first-child',
        ],
        description="Contact name in chat header",
    ),

    # Messages
    "incoming_message": SelectorChain(
        name="incoming_message",
        primary='div.message-in span.selectable-text',
        fallbacks=[
            'div.message-in span',
            'div[data-testid="msg-container"] span.selectable-text',
            'div.incoming span',
        ],
        description="Incoming message text",
    ),
    "outgoing_message": SelectorChain(
        name="outgoing_message",
        primary='div.message-out span.selectable-text',
        fallbacks=[
            'div.message-out span',
            'div[data-testid="msg-container"] span.selectable-text',
            'div.outgoing span',
        ],
        description="Outgoing message text",
    ),

    # Login detection
    "qr_code": SelectorChain(
        name="qr_code",
        primary='div[data-testid="qrcode"]',
        fallbacks=[
            'canvas[data-ref]',
            'div.qrcode canvas',
            'img[data-ref]',
        ],
        description="QR code for login",
    ),
    "logged_in_indicator": SelectorChain(
        name="logged_in_indicator",
        primary='div[data-testid="chat-list"]',
        fallbacks=[
            'div[title="Search"]',
            'div.side',
            'div._3OtyE',
        ],
        description="Indicator that user is logged in",
    ),

    # Error detection
    "number_not_on_whatsapp": SelectorChain(
        name="number_not_on_whatsapp",
        primary='div[data-testid="match-account-banner"]',
        fallbacks=[
            'div._2Nr1n',
            'div:has-text("not on WhatsApp")',
            'div:has-text("ليس على واتساب")',
        ],
        description="Number not on WhatsApp error banner",
    ),
}


# ---------------------------------------------------------------------------
# Facebook Selectors
# ---------------------------------------------------------------------------
FACEBOOK_SELECTORS = {
    # Posts
    "article_post": SelectorChain(
        name="article_post",
        primary='div[role="article"]',
        fallbacks=[
            'div[data-ad-rendering-role="story_message"]',
            'div.userContent',
            'div.story_body_container',
            'div[data-testid="fbfeed_story"]',
        ],
        description="Facebook group post container",
    ),
    "post_author": SelectorChain(
        name="post_author",
        primary='a[role="link"] span',
        fallbacks=[
            'strong[data-ft] a',
            'a.profileLink',
            'span.fw a',
        ],
        description="Post author name",
    ),
    "post_link": SelectorChain(
        name="post_link",
        primary='a[href*="/posts/"]',
        fallbacks=[
            'a[href*="/permalink/"]',
            'a[href*="story_fbid"]',
            'a[href*="/photos/"]',
        ],
        description="Post permalink",
    ),

    # Group detection
    "group_name": SelectorChain(
        name="group_name",
        primary='h1 span[dir="auto"]',
        fallbacks=[
            'h1 strong a',
            'div[role="banner"] h1',
        ],
        description="Group name in header",
    ),
    "group_loaded": SelectorChain(
        name="group_loaded",
        primary='div[role="feed"]',
        fallbacks=[
            'div[role="main"]',
            'div#group_container',
            'div._4ik4',
        ],
        description="Group feed container (indicates load complete)",
    ),

    # Login detection
    "login_form": SelectorChain(
        name="login_form",
        primary='form#login_form',
        fallbacks=[
            'div#email_container',
            'input[name="email"]',
        ],
        description="Facebook login form",
    ),
    "logged_in_indicator": SelectorChain(
        name="logged_in_indicator",
        primary='div[role="navigation"]',
        fallbacks=[
            'div#blueBarRoot',
            'div._6-xo',
        ],
        description="Facebook logged-in indicator",
    ),

    # Rate limit detection
    "rate_limit_message": SelectorChain(
        name="rate_limit_message",
        primary='div:has-text("slow down")',
        fallbacks=[
            'div:has-text("بطء")',
            'div:has-text("rate limit")',
        ],
        description="Facebook rate limit warning",
    ),
}


class SelectorRegistry:
    """Centralized selector management with fallback support."""

    def __init__(self):
        self._selectors: dict[str, dict[str, SelectorChain]] = {
            "whatsapp": WHATSAPP_SELECTORS,
            "facebook": FACEBOOK_SELECTORS,
        }
        self._stats: dict[str, dict[str, dict]] = {}

    def get(self, platform: str, selector_name: str) -> SelectorChain | None:
        """Get a selector chain by platform and name."""
        platform_selectors = self._selectors.get(platform, {})
        return platform_selectors.get(selector_name)

    def get_all_selectors(self, platform: str, selector_name: str) -> list[str]:
        """Get all selectors to try for a given element."""
        chain = self.get(platform, selector_name)
        if chain:
            return chain.all_selectors()
        return []

    def record_success(self, platform: str, selector_name: str, selector: str):
        """Record that a selector worked."""
        chain = self.get(platform, selector_name)
        if chain:
            chain.last_working = selector
            chain.failure_count = 0
            self._update_stats(platform, selector_name, selector, True)

    def record_failure(self, platform: str, selector_name: str, selector: str):
        """Record that a selector failed."""
        chain = self.get(platform, selector_name)
        if chain:
            chain.failure_count += 1
            self._update_stats(platform, selector_name, selector, False)
            if chain.failure_count >= 3:
                logger.warning(
                    "Selector '%s.%s' has failed %d times. Consider updating.",
                    platform, selector_name, chain.failure_count
                )

    def _update_stats(self, platform: str, selector_name: str, selector: str, success: bool):
        """Update selector statistics."""
        key = f"{platform}.{selector_name}"
        if key not in self._stats:
            self._stats[key] = {"total": 0, "success": 0, "failure": 0}
        self._stats[key]["total"] += 1
        if success:
            self._stats[key]["success"] += 1
        else:
            self._stats[key]["failure"] += 1

    def get_health_report(self) -> dict:
        """Get health report for all selectors."""
        report = {}
        for key, stats in self._stats.items():
            success_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            report[key] = {
                **stats,
                "success_rate": round(success_rate * 100, 1),
                "healthy": success_rate > 0.8,
            }
        return report

    def find_best_selector(self, platform: str, selector_name: str) -> str | None:
        """Find the best selector based on success rate."""
        chain = self.get(platform, selector_name)
        if not chain:
            return None

        # If last_working is known and recent, use it
        if chain.last_working:
            return chain.last_working

        # Otherwise return primary
        return chain.primary


# Global registry instance
registry = SelectorRegistry()


def get_selector(platform: str, name: str) -> str | None:
    """Convenience function to get the best selector."""
    return registry.find_best_selector(platform, name)


def get_all_selectors(platform: str, name: str) -> list[str]:
    """Convenience function to get all selectors to try."""
    return registry.get_all_selectors(platform, name)
