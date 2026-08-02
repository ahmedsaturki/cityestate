"""
Unit Tests for Playwright Selector Registry
============================================
Tests for selector fallback chains and health tracking.
"""

import pytest
from src.automation.selectors import (
    SelectorChain,
    SelectorRegistry,
    WHATSAPP_SELECTORS,
    FACEBOOK_SELECTORS,
    registry,
    get_selector,
    get_all_selectors,
)


class TestSelectorChain:
    """Test SelectorChain dataclass."""

    def test_chain_creation(self):
        chain = SelectorChain(
            name="test",
            primary="div.test",
            fallbacks=["span.test", "p.test"],
            description="Test selector",
        )
        assert chain.name == "test"
        assert chain.primary == "div.test"
        assert len(chain.fallbacks) == 2

    def test_all_selectors(self):
        chain = SelectorChain(
            name="test",
            primary="div.primary",
            fallbacks=["span.fallback1", "span.fallback2"],
        )
        selectors = chain.all_selectors()
        assert selectors == ["div.primary", "span.fallback1", "span.fallback2"]

    def test_empty_fallbacks(self):
        chain = SelectorChain(name="test", primary="div.test")
        selectors = chain.all_selectors()
        assert selectors == ["div.test"]


class TestSelectorRegistry:
    """Test SelectorRegistry class."""

    def test_get_whatsapp_selector(self):
        chain = registry.get("whatsapp", "message_input")
        assert chain is not None
        assert chain.name == "message_input"
        assert "data-testid" in chain.primary

    def test_get_facebook_selector(self):
        chain = registry.get("facebook", "article_post")
        assert chain is not None
        assert chain.name == "article_post"
        assert 'role="article"' in chain.primary

    def test_get_nonexistent_selector(self):
        chain = registry.get("whatsapp", "nonexistent")
        assert chain is None

    def test_get_all_selectors(self):
        selectors = registry.get_all_selectors("whatsapp", "message_input")
        assert len(selectors) >= 1
        assert selectors[0] == 'div[data-testid="conversation-compose-box-input"]'

    def test_record_success(self):
        chain = registry.get("whatsapp", "message_input")
        initial_count = chain.failure_count
        registry.record_success("whatsapp", "message_input", chain.primary)
        assert chain.failure_count == 0
        assert chain.last_working == chain.primary

    def test_record_failure(self):
        chain = SelectorChain(
            name="test",
            primary="div.test",
            fallbacks=[],
            failure_count=0,
        )
        registry._selectors["test"] = {"test": chain}
        registry.record_failure("test", "test", "div.test")
        assert chain.failure_count == 1

    def test_health_report(self):
        report = registry.get_health_report()
        assert isinstance(report, dict)

    def test_find_best_selector(self):
        # Record a working selector
        registry.record_success("whatsapp", "message_input", "div.custom")
        best = registry.find_best_selector("whatsapp", "message_input")
        assert best == "div.custom"


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_get_selector(self):
        # Reset any health data from prior tests to get the primary selector
        for platform_selectors in registry._selectors.values():
            for chain in platform_selectors.values():
                chain.last_working = None
                chain.failure_count = 0
        selector = get_selector("whatsapp", "message_input")
        assert selector is not None
        assert "data-testid" in selector

    def test_get_all_selectors_function(self):
        selectors = get_all_selectors("whatsapp", "message_input")
        assert len(selectors) >= 1


class TestWhatsAppSelectors:
    """Test WhatsApp selector definitions."""

    def test_message_input(self):
        assert "message_input" in WHATSAPP_SELECTORS
        chain = WHATSAPP_SELECTORS["message_input"]
        assert len(chain.all_selectors()) >= 2

    def test_send_button(self):
        assert "send_button" in WHATSAPP_SELECTORS
        chain = WHATSAPP_SELECTORS["send_button"]
        assert len(chain.all_selectors()) >= 2

    def test_unread_badge(self):
        assert "unread_badge" in WHATSAPP_SELECTORS

    def test_all_have_selectors(self):
        for name, chain in WHATSAPP_SELECTORS.items():
            selectors = chain.all_selectors()
            assert len(selectors) >= 1, f"{name} has no selectors"


class TestFacebookSelectors:
    """Test Facebook selector definitions."""

    def test_article_post(self):
        assert "article_post" in FACEBOOK_SELECTORS
        chain = FACEBOOK_SELECTORS["article_post"]
        assert len(chain.all_selectors()) >= 2

    def test_post_author(self):
        assert "post_author" in FACEBOOK_SELECTORS

    def test_post_link(self):
        assert "post_link" in FACEBOOK_SELECTORS

    def test_all_have_selectors(self):
        for name, chain in FACEBOOK_SELECTORS.items():
            selectors = chain.all_selectors()
            assert len(selectors) >= 1, f"{name} has no selectors"
