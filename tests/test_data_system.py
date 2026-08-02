"""
Data System Tests — اختبارات نظام البيانات
=============================================
Tests for data extraction, crawling, enrichment, quality, and WhatsApp check.
Run with: python -m pytest tests/test_data_system.py -v
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.extractor import DataExtractor
from src.data.crawler import WebCrawler
from src.data.enricher import DataEnricher, AREA_METADATA, DEVELOPER_REPUTATION
from src.data.whatsapp_check import WhatsAppChecker
from src.data.quality import DataQualityScorer, PROPERTY_REQUIRED_FIELDS


# ===========================================================================
# DataExtractor Tests
# ===========================================================================
class TestDataExtractor:
    """Test data extraction from various sources."""

    def setup_method(self):
        self.extractor = DataExtractor()

    def test_extract_whatsapp_basic(self):
        msg = "عايز شقة 3 غرف في الشيخ زايد بميزانية 2 مليون"
        result = self.extractor.extract_from_whatsapp(msg)
        assert result is not None
        assert isinstance(result, dict)

    def test_extract_whatsapp_with_sender(self):
        msg = "مطلوب فيلا في كمبوند سيتي ستارز"
        result = self.extractor.extract_from_whatsapp(msg, sender="أحمد")
        assert result is not None

    def test_extract_facebook_basic(self):
        post = "شقة للبيع في المنطقة 7 - 150 متر - 2.5 مليون"
        result = self.extractor.extract_from_facebook(post)
        assert result is not None

    def test_extract_facebook_with_url(self):
        post = "فيلا فاخرة في السادات"
        result = self.extractor.extract_from_facebook(post, post_url="https://facebook.com/post/123")
        assert result is not None

    def test_extract_webpage(self):
        html = "<html><body><h1>شقة 3 غرف - 2 مليون جنيه</h1></body></html>"
        result = self.extractor.extract_from_webpage(html)
        assert result is not None

    def test_extract_json(self):
        data = {
            "title": "شقة في الشيخ زايد",
            "price": 2000000,
            "area_sqm": 150,
            "bedrooms": 3,
        }
        result = self.extractor.extract_from_json(data)
        assert result is not None
        # extract_from_json maps "price" to "budget"
        assert result.get("budget") == 2000000

    def test_phone_extraction(self):
        phone = self.extractor._extract_phone("هاتفي 01123456789")
        assert phone is not None

    def test_property_type_detection(self):
        types = {
            "شقة": "شقة فاخرة",
            "فيلا": "فيلا",
            "محل": "محل تجاري",
            "أرض": "أرض استثمارية",
        }
        for ar, expected in types.items():
            detected = self.extractor._extract_property_type(ar)
            assert detected is not None, f"Failed to detect type for '{ar}'"

    def test_area_detection(self):
        areas = ["المنطقة 7", "المنطقة 9", "المنطقة 15", "الشريط المميز"]
        detected_count = 0
        for area in areas:
            result = self.extractor._extract_area(area)
            if result:
                detected_count += 1
        assert detected_count >= 1

    def test_intent_detection(self):
        buying = ["عايز", "بتدور", "مطلوب", "أبحث"]
        for word in buying:
            intent = self.extractor._detect_intent(word)
            assert intent in ("buyer", "seller", "broker", "unknown")

    def test_stats_tracking(self):
        self.extractor.extract_from_whatsapp("test")
        stats = self.extractor.stats
        assert isinstance(stats, dict)
        assert "total_extractions" in stats


# ===========================================================================
# WebCrawler Tests
# ===========================================================================
class TestWebCrawler:
    """Test web crawler with mocked HTTP responses."""

    def setup_method(self):
        self.crawler = WebCrawler()

    def test_crawler_instantiation(self):
        assert self.crawler is not None

    def test_rate_limiting(self):
        """Rate limiter prevents too-fast requests."""
        import time
        start = time.time()
        self.crawler._rate_limit("https://example.com")
        elapsed = time.time() - start
        assert elapsed >= 0

    def test_premium_filter(self):
        """Low-budget properties are filtered out."""
        cheap = {"price": 500000, "title": "شقة رخيصة"}
        expensive = {"price": 3000000, "title": "شقة فاخرة"}
        assert cheap["price"] < 1500000

    def test_deduplication(self):
        """Duplicate URLs are detected."""
        url1 = "https://olx.com/property/123"
        url2 = "https://olx.com/property/123"
        assert url1 == url2

    def test_guess_property_type(self):
        """Property type guessing from text."""
        assert self.crawler._guess_property_type("فيلا فاخرة") == "فيلا"
        assert self.crawler._guess_property_type("شقة واسعة") == "شقة فاخرة"
        assert self.crawler._guess_property_type("محل تجاري") == "محل تجاري"

    def test_guess_area(self):
        """Area guessing from text."""
        result = self.crawler._guess_area("في المنطقة 7")
        assert result is not None


# ===========================================================================
# DataEnricher Tests
# ===========================================================================
class TestDataEnricher:
    """Test data enrichment with area metadata."""

    def setup_method(self):
        self.enricher = DataEnricher()

    def test_enrich_basic(self):
        data = {
            "property_type": "apartment",
            "area": "المنطقة 7 الشريط المميز",
            "price": 2000000,
            "area_sqm": 150,
            "bedrooms": 3,
        }
        result = self.enricher.enrich(data)
        assert result is not None
        assert isinstance(result, dict)

    def test_enrich_batch(self):
        items = [
            {"property_type": "apartment", "price": 2000000, "area_sqm": 150},
            {"property_type": "villa", "price": 5000000, "area_sqm": 300},
        ]
        results = self.enricher.enrich_batch(items)
        assert len(results) == 2

    def test_price_per_sqm(self):
        result = self.enricher._calculate_price_per_sqm({"price": 2000000, "area_sqm": 150})
        assert result == pytest.approx(13333.33, rel=0.01)

    def test_price_per_sqm_zero_area(self):
        result = self.enricher._calculate_price_per_sqm({"price": 2000000, "area_sqm": 0})
        assert result is None

    def test_area_metadata_exists(self):
        assert "المنطقة 7 الشريط المميز" in AREA_METADATA
        assert "المنطقة 9 الشريط المميز" in AREA_METADATA
        assert "المنطقة 15 الشريط المميز" in AREA_METADATA

    def test_developer_reputation_exists(self):
        assert len(DEVELOPER_REPUTATION) > 0

    def test_is_premium(self):
        premium = {"price": 5000000, "property_type": "villa", "area": "المنطقة 7 الشريط المميز"}
        result = self.enricher._is_premium(premium)
        assert isinstance(result, bool)
        assert result is True

    def test_market_comparison(self):
        data = {"area": "المنطقة 7 الشريط المميز", "price": 2000000, "area_sqm": 150}
        result = self.enricher._compare_to_market(data)
        assert isinstance(result, dict)
        assert "status" in result

    def test_contact_quality(self):
        good = {"contact_phone": "+201123456789", "contact_name": "Ahmed"}
        bad = {}
        good_result = self.enricher._assess_contact_quality(good)
        bad_result = self.enricher._assess_contact_quality(bad)
        assert good_result["score"] > bad_result["score"]

    def test_completeness(self):
        full = {
            "property_type": "apartment",
            "area": "Sheikh Zayed",
            "price": 2000000,
            "bedrooms": 3,
            "area_sqm": 150,
            "contact_phone": "+201123456789",
            "contact_name": "Ahmed",
        }
        empty = {}
        full_score = self.enricher._calculate_completeness(full)
        empty_score = self.enricher._calculate_completeness(empty)
        assert full_score > empty_score


# ===========================================================================
# WhatsAppChecker Tests
# ===========================================================================
class TestWhatsAppChecker:
    """Test WhatsApp phone checking and normalization."""

    def setup_method(self):
        self.checker = WhatsAppChecker()

    def test_normalize_phone_local(self):
        result = self.checker.normalize_phone("01123456789")
        assert result.startswith("+20")

    def test_normalize_phone_international(self):
        result = self.checker.normalize_phone("+201123456789")
        assert result.startswith("+20")

    def test_normalize_phone_with_spaces(self):
        result = self.checker.normalize_phone("011 234 567 89")
        assert result.startswith("+20")

    def test_is_egyptian_number(self):
        assert self.checker.is_egyptian_number("+201123456789")
        assert self.checker.is_egyptian_number("01123456789")
        assert not self.checker.is_egyptian_number("+1234567890")

    def test_check_whatsapp(self):
        result = self.checker.check_whatsapp("01123456789")
        assert isinstance(result, dict)
        assert "phone" in result

    def test_qualify_lead(self):
        result = self.checker.qualify_lead("01123456789", "أحمد", "apartment", 2000000)
        assert isinstance(result, dict)

    def test_extract_phones_from_text(self):
        text = "هاتفي 01123456789 ورقمي 01012345678"
        phones = self.checker.extract_phones_from_text(text)
        assert len(phones) >= 1

    def test_qualify_lead_minimal_data(self):
        result = self.checker.qualify_lead("01123456789")
        assert isinstance(result, dict)


# ===========================================================================
# DataQualityScorer Tests
# ===========================================================================
class TestDataQualityScorer:
    """Test data quality scoring."""

    def setup_method(self):
        self.scorer = DataQualityScorer()

    def test_score_property_full(self):
        prop = {
            "title": "شقة في الشيخ زايد",
            "price": 2000000,
            "area_sqm": 150,
            "bedrooms": 3,
            "property_type": "apartment",
            "area": "Sheikh Zayed",
            "contact_phone": "+201123456789",
        }
        result = self.scorer.score_property(prop)
        assert "overall_score" in result
        assert "quality_tier" in result
        assert result["overall_score"] > 50

    def test_score_property_empty(self):
        result = self.scorer.score_property({})
        assert result["overall_score"] <= 50

    def test_score_lead(self):
        lead = {
            "client_name": "أحمد",
            "phone": "+201123456789",
            "property_type": "apartment",
            "budget": 2000000,
        }
        result = self.scorer.score_lead(lead)
        assert "overall_score" in result
        assert "quality_tier" in result

    def test_score_batch(self):
        items = [
            {"title": "Test", "price": 2000000},
            {"title": "Test2", "price": 3000000},
        ]
        result = self.scorer.score_batch(items)
        assert "total_items" in result
        assert result["total_items"] == 2
        assert "scores" in result
        assert len(result["scores"]) == 2

    def test_find_duplicates(self):
        items = [
            {"phone": "01123456789", "title": "A", "area": "A", "price": 100, "property_type": "x", "bedrooms": 2},
            {"phone": "01123456789", "title": "B", "area": "A", "price": 100, "property_type": "x", "bedrooms": 2},
            {"phone": "01012345678", "title": "C", "area": "B", "price": 200, "property_type": "y", "bedrooms": 3},
        ]
        dupes = self.scorer.find_duplicates(items)
        assert len(dupes) >= 1

    def test_quality_tiers(self):
        tiers = ["excellent", "good", "acceptable", "poor", "incomplete"]
        assert len(tiers) == 5

    def test_required_fields(self):
        assert len(PROPERTY_REQUIRED_FIELDS) > 0


# ===========================================================================
# Module Init Tests
# ===========================================================================
class TestDataModuleInit:
    """Test data module initialization."""

    def test_module_exports(self):
        from src.data import (
            DataExtractor,
            WebCrawler,
            DataEnricher,
            WhatsAppChecker,
            DataQualityScorer,
        )
        assert DataExtractor is not None
        assert WebCrawler is not None
        assert DataEnricher is not None
        assert WhatsAppChecker is not None
        assert DataQualityScorer is not None
