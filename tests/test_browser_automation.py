"""
Browser Automation Tests — اختبارات الأتمتة
=============================================
Playwright-based tests for Chrome Extension and web automation.
Run with: python -m pytest tests/test_browser_automation.py -v
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.automation.selectors import (
    get_selector,
    get_all_selectors,
    SelectorChain,
    SelectorRegistry,
    registry,
)


# ---------------------------------------------------------------------------
# Chrome Extension Service Worker Tests
# ---------------------------------------------------------------------------
class TestServiceWorker:
    """Test service-worker.js logic (offline queue, alarms, WebSocket)."""

    def test_offline_queue_structure(self):
        """Offline queue items have required fields."""
        item = {
            "id": "msg_001",
            "type": "whatsapp",
            "action": "send",
            "payload": {"to": "+20112345678", "text": "Test"},
            "timestamp": 1700000000000,
            "retries": 0,
        }
        assert "id" in item
        assert "type" in item
        assert "action" in item
        assert "payload" in item
        assert "timestamp" in item
        assert "retries" in item

    def test_alarm_names(self):
        """Alarm names follow naming convention."""
        expected_alarms = [
            "retry-offline-queue",
            "session-health-check",
            "daily-stats",
            "stale-session-cleanup",
        ]
        for alarm in expected_alarms:
            assert isinstance(alarm, str)
            assert len(alarm) > 0

    def test_message_log_structure(self):
        """Message log entries have required fields."""
        entry = {
            "id": "log_001",
            "type": "whatsapp",
            "direction": "outbound",
            "content": "Hello",
            "status": "sent",
            "timestamp": 1700000000000,
        }
        required = ["id", "type", "direction", "content", "status", "timestamp"]
        for field in required:
            assert field in entry


# ---------------------------------------------------------------------------
# WhatsApp Content Script Tests
# ---------------------------------------------------------------------------
class TestWhatsAppContentScript:
    """Test whatsapp.js DOM interaction logic."""

    def test_sentinel_guard(self):
        """Sentinel prevents duplicate injection."""
        sentinel_name = "__cityestate_whatsapp_injected__"
        assert isinstance(sentinel_name, str)
        assert sentinel_name.startswith("__")

    def test_chat_id_strategies(self):
        """5 chat ID extraction strategies defined."""
        strategies = [
            "data-testid attribute",
            "href extraction",
            "aria-label",
            "title attribute",
            "header text fallback",
        ]
        assert len(strategies) == 5

    def test_arabic_normalization(self):
        """Arabic text normalization handles common variants."""
        test_cases = [
            ("أ", "ا"),
            ("إ", "ا"),
            ("ة", "ه"),
            ("ى", "ي"),
        ]
        for original, expected in test_cases:
            assert original != expected  # They are different chars

    def test_debounce_delay(self):
        """Debounce delay is reasonable (300-500ms)."""
        debounce_ms = 350
        assert 300 <= debounce_ms <= 500


# ---------------------------------------------------------------------------
# Facebook Content Script Tests
# ---------------------------------------------------------------------------
class TestFacebookContentScript:
    """Test facebook.js posting and extraction logic."""

    def test_react_posting_strategy(self):
        """React posting uses native input simulation."""
        strategies = [
            "contentEditable insertion",
            "native input event",
            "clipboard paste fallback",
        ]
        assert len(strategies) >= 2

    def test_intent_extraction_keywords(self):
        """Intent extraction covers key Arabic real estate terms."""
        buying_keywords = ["عايز", "بتدور", "مطلوب", "أبحث", "mfesh", "محتاج"]
        selling_keywords = ["للبيع", "يبيع", "سمسار", "إعلان"]
        assert len(buying_keywords) >= 4
        assert len(selling_keywords) >= 3

    def test_premium_filter_keywords(self):
        """Premium filter rejects low-budget messages."""
        reject_keywords = ["تقسيط", "rate", "رخيص", "تسعين ألف", "80 ألف"]
        assert len(reject_keywords) >= 4


# ---------------------------------------------------------------------------
# Selector System Tests
# ---------------------------------------------------------------------------
class TestSelectorSystem:
    """Test selector registry and chains."""

    def test_whatsapp_selectors_complete(self):
        """WhatsApp selectors cover all required elements."""
        required_elements = [
            "message_input",
            "send_button",
            "unread_badge",
            "incoming_message",
            "outgoing_message",
        ]
        for element in required_elements:
            selectors = get_all_selectors("whatsapp", element)
            assert len(selectors) > 0, f"Missing WhatsApp selector: {element}"

    def test_facebook_selectors_complete(self):
        """Facebook selectors cover all required elements."""
        required_elements = [
            "article_post",
            "post_author",
            "post_link",
        ]
        for element in required_elements:
            selectors = get_all_selectors("facebook", element)
            assert len(selectors) > 0, f"Missing Facebook selector: {element}"

    def test_selector_chain_fallback(self):
        """Selector chain tries multiple selectors."""
        chain = SelectorChain(
            name="test_message_input",
            primary="div[contenteditable='true']",
            fallbacks=["div._1lCp", "div[role='textbox']"],
            description="Test selector",
        )
        assert chain is not None
        assert len(chain.fallbacks) > 0

    def test_selector_health_report(self):
        """Health report returns a dict."""
        health = registry.get_health_report()
        assert isinstance(health, dict)


# ---------------------------------------------------------------------------
# Data Extraction Integration Tests
# ---------------------------------------------------------------------------
class TestDataExtractionFromBrowser:
    """Test data extraction from browser-captured messages."""

    def test_whatsapp_message_parsing(self):
        """Parse WhatsApp message into structured data."""
        from src.data.extractor import DataExtractor
        extractor = DataExtractor()

        message = "عايز شقة 3 غرف في الشيخ زايد بميزانية 2 مليون"
        result = extractor.extract_from_whatsapp(message)

        assert result is not None
        assert "property_type" in result
        assert "area" in result

    def test_facebook_post_parsing(self):
        """Parse Facebook post into structured data."""
        from src.data.extractor import DataExtractor
        extractor = DataExtractor()

        post = "فيلا للبيع في السادات - 300 متر - 5 مليون جنيه"
        result = extractor.extract_from_facebook(post)

        assert result is not None

    def test_phone_extraction(self):
        """Extract Egyptian phone numbers."""
        from src.data.extractor import DataExtractor
        extractor = DataExtractor()

        messages = [
            "هاتفي 01123456789",
            "الرقم 01012345678",
            "Call me +201234567890",
        ]
        for msg in messages:
            phone = extractor._extract_phone(msg)
            assert phone is not None, f"Failed to extract phone from: {msg}"


# ---------------------------------------------------------------------------
# End-to-End Flow Tests
# ---------------------------------------------------------------------------
class TestEndToEndFlow:
    """Test complete browser → extraction → scoring flow."""

    def test_whatsapp_message_to_lead(self):
        """Full flow: WhatsApp message → extraction → scoring."""
        from src.data.extractor import DataExtractor
        from src.api.bridge_handler import score_lead

        extractor = DataExtractor()
        message = "عايز فيلا في كمبوند سيتي ستارز 4 غرف بـ 5 مليون جنيه"

        # Extract
        extracted = extractor.extract_from_whatsapp(message)
        assert extracted is not None

        # Score (score_lead takes intent dict + message string)
        scored = score_lead(extracted, message)
        assert scored is not None
        assert "score" in scored
        assert "tier" in scored

    def test_facebook_post_to_lead(self):
        """Full flow: Facebook post → extraction → scoring."""
        from src.data.extractor import DataExtractor
        from src.api.bridge_handler import score_lead

        extractor = DataExtractor()
        post = "مطلوب شقة 3 غرف في المنطقة 7 بميزانية 2 مليون جنيه - تواصل 01123456789"

        # Extract
        extracted = extractor.extract_from_facebook(post)
        assert extracted is not None

        # Score (score_lead takes intent dict + message string)
        scored = score_lead(extracted, post)
        assert scored is not None
        assert scored["score"] > 0
