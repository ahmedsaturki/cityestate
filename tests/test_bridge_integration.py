"""
Bridge Handler Integration Tests — اختبارات الجسر (Premium Focus)
==================================================================
Tests the core message processing pipeline for PREMIUM real estate:
  parse_intent → score_lead → match_properties → generate_response

FOCUS: Luxury compounds, villas, commercial hubs, industrial investment.
NO social housing or budget properties.
"""

import pytest


# ---------------------------------------------------------------------------
# Intent Parser Tests (Premium Focus)
# ---------------------------------------------------------------------------
class TestParseIntent:
    """Test Egyptian Arabic intent parsing for PREMIUM properties."""

    def test_area_detection_premium_area(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("عايز شقة في الفردوس")
        assert result["area"] == "الفردوس"

    def test_area_detection_industrial_zone(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("محل تجاري في المنطقة الصناعية الأولى")
        assert result["area"] == "المنطقة الصناعية الأولى"

    def test_area_detection_polaris(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("مستودع في بولاريس باركس")
        assert result["area"] == "Polaris Parks"

    def test_area_detection_shariaf(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("فيلا في الشريط المميز")
        assert result["area"] == "المنطقة 7 الشريط المميز"

    def test_budget_detection_premium(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("ميزانيتي 5 مليون جنيه")
        assert result["budget"] is not None
        assert result["budget"] >= 5000000

    def test_budget_detection_high_end(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("أقدر أدفع 8 مليون")
        assert result["budget"] is not None
        assert result["budget"] >= 8000000

    def test_budget_auto_filter_rejects_low(self):
        """Test that budgets under 1.5M EGP are automatically rejected."""
        from src.api.bridge_handler import parse_intent
        result = parse_intent("عايز شقة بـ 800 ألف جنيه في المنطقة 5")
        assert result is None  # Should be rejected

    def test_budget_auto_filter_rejects_social_housing(self):
        """Test that social housing requests are rejected."""
        from src.api.bridge_handler import parse_intent
        result = parse_intent("عايز شقة إسكان اجتماعي بـ 500 ألف")
        assert result is None  # Should be rejected

    def test_bedrooms_detection(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("عايز 3 غرف نوم في فيلا")
        assert result["bedrooms"] == 3

    def test_bedrooms_detection_five(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("فيلا 5 غرف في الكوثر")
        assert result["bedrooms"] == 5

    def test_property_type_villa(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("عايز فيلا في النخيل")
        assert result["property_type"] == "فيلا"

    def test_property_type_commercial(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("محل تجاري في المنطقة الصناعية")
        assert result["property_type"] == "محل تجاري"

    def test_property_type_warehouse(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("مستودع صناعي في بولاريس")
        assert result["property_type"] == "مستودع"

    def test_urgency_detection_urgent(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("عايز فيلا عاجل جداً في الفردوس")
        assert result["timeline"] == "urgent"

    def test_urgency_detection_flexible(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("مش مستعجل خالص، لو في فرصة كويسة")
        assert result["timeline"] == "flexible"

    def test_broker_detection(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("أنا سمسار عندي عقارات كتير")
        assert result["status"] == "broker"

    def test_buyer_detection(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("عايز أشتري فيلا في الكوثر")
        assert result["status"] == "buyer"

    def test_sale_origin_cairo(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("أنا من القاهرة، عايز فيلا في الفردوس")
        assert result["sale_origin"] == "القاهرة"

    def test_sale_origin_alexandria(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("جاي من الإسكندرية، بدور على استثمار في الصناعية")
        assert result["sale_origin"] == "الإسكندرية"

    def test_empty_message(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("")
        assert result["area"] is None
        assert result["budget"] is None

    def test_premium_property_recognition(self):
        """Test that premium property types are properly recognized."""
        from src.api.bridge_handler import parse_intent
        result = parse_intent("بنتهاوس في الروضة بـ 4 مليون جنيه")
        assert result["property_type"] == "شقة فاخرة"


# ---------------------------------------------------------------------------
# Lead Scoring Tests (Premium Focus)
# ---------------------------------------------------------------------------
class TestScoreLead:
    """Test lead scoring algorithm for PREMIUM leads."""

    def test_platinum_lead(self):
        from src.api.bridge_handler import score_lead
        intent = {
            "area": "الفردوس",
            "budget": 8000000,
            "property_type": "فيلا",
            "timeline": "urgent",
            "status": "buyer",
            "sale_origin": "القاهرة",
        }
        result = score_lead(intent, "عايز فيلا في الفردوس بـ 8 مليون جنيه - عاجل جداً")
        assert result["quality"] == "platinum"
        assert result["score"] >= 80

    def test_gold_lead(self):
        from src.api.bridge_handler import score_lead
        intent = {
            "area": "الكوثر",
            "budget": 5000000,
            "property_type": "شقة فاخرة",
            "timeline": "urgent",
            "status": "buyer",
            "sale_origin": "الإسكندرية",
        }
        result = score_lead(intent, "عايز شقة فاخرة في الكوثر بـ 5 مليون")
        assert result["quality"] == "gold"
        assert result["score"] >= 60

    def test_silver_lead(self):
        from src.api.bridge_handler import score_lead
        intent = {
            "area": "النخيل",
            "budget": 2500000,
            "property_type": "شقة فاخرة",
            "timeline": "flexible",
            "status": "buyer",
            "sale_origin": None,
        }
        result = score_lead(intent, "عايز شقة في النخيل بـ 2.5 مليون")
        assert result["quality"] == "silver"
        assert result["score"] >= 40

    def test_rejected_lead_low_budget(self):
        from src.api.bridge_handler import score_lead
        intent = None  # Low budget = None
        result = score_lead(intent, "عايز شقة بـ 800 ألف")
        assert result["quality"] == "rejected"
        assert result["score"] == 0

    def test_broker_penalty(self):
        from src.api.bridge_handler import score_lead
        intent = {
            "area": "الفردوس",
            "budget": 5000000,
            "property_type": "فيلا",
            "timeline": "urgent",
            "status": "broker",
            "sale_origin": "القاهرة",
        }
        result = score_lead(intent, "أنا سمسار عندي فيلا في الفردوس")
        assert result["score"] < 60  # Broker penalty applied

    def test_phone_bonus(self):
        from src.api.bridge_handler import score_lead
        intent_no_phone = {
            "area": "الكوثر",
            "budget": 3000000,
            "property_type": "شقة فاخرة",
            "timeline": None,
            "status": "buyer",
            "sale_origin": None,
        }
        intent_with_phone = intent_no_phone.copy()
        result_no = score_lead(intent_no_phone, "عايز شقة في الكوثر")
        result_yes = score_lead(intent_with_phone, "عايز شقة في الكوثر 01012345678")
        assert result_yes["score"] > result_no["score"]

    def test_score_clamped_0_100(self):
        from src.api.bridge_handler import score_lead
        intent = {
            "area": "الفردوس",
            "budget": 15000000,
            "property_type": "مول تجاري",
            "timeline": "urgent",
            "status": "buyer",
            "sale_origin": "القاهرة",
        }
        result = score_lead(intent, "عايز مول تجاري في الفردوس بـ 15 مليون جنيه عاجل 01012345678")
        assert 0 <= result["score"] <= 100

    def test_premium_property_bonus(self):
        from src.api.bridge_handler import score_lead
        intent = {
            "area": "المنطقة الصناعية الأولى",
            "budget": 5000000,
            "property_type": "مستودع",
            "timeline": None,
            "status": "buyer",
            "sale_origin": None,
        }
        result = score_lead(intent, "عايز مستودع صناعي بـ 5 مليون")
        assert result["score"] >= 50  # Premium property bonus


# ---------------------------------------------------------------------------
# Property Matching Tests (Premium Focus)
# ---------------------------------------------------------------------------
class TestMatchProperties:
    """Test property matching engine for PREMIUM properties."""

    def test_match_filters_low_price(self):
        """Test that properties under 1.5M EGP are excluded."""
        from src.api.bridge_handler import match_properties
        
        intent = {"area": "الفردوس", "budget": 3000000, "property_type": "شقة فاخرة"}
        properties = [
            {"area": "الفردوس", "price": 1200000, "property_type": "شقة فاخرة"},  # Too low
            {"area": "الفردوس", "price": 2500000, "property_type": "شقة فاخرة"},  # Match
            {"area": "الفردوس", "price": 3500000, "property_type": "شقة فاخرة"},  # Match
        ]
        matches = match_properties(intent, properties)
        assert len(matches) == 2  # Only 2 premium matches
        assert all(m["property"]["price"] >= 1500000 for m in matches)

    def test_match_by_area(self):
        from src.api.bridge_handler import match_properties
        
        intent = {"area": "الفردوس", "budget": 5000000, "property_type": "فيلا"}
        properties = [
            {"area": "الفردوس", "price": 4500000, "property_type": "فيلا"},
            {"area": "الكوثر", "price": 4000000, "property_type": "فيلا"},
            {"area": "الفردوس", "price": 5500000, "property_type": "فيلا"},
        ]
        matches = match_properties(intent, properties)
        assert len(matches) == 2  # Only Al-Ferdous properties
        assert all(m["property"]["area"] == "الفردوس" for m in matches)

    def test_match_by_property_type(self):
        from src.api.bridge_handler import match_properties
        
        intent = {"area": None, "budget": 5000000, "property_type": "فيلا"}
        properties = [
            {"area": "الفردوس", "price": 4500000, "property_type": "فيلا"},
            {"area": "الكوثر", "price": 4000000, "property_type": "شقة فاخرة"},
            {"area": "النخيل", "price": 5500000, "property_type": "فيلا"},
        ]
        matches = match_properties(intent, properties)
        assert len(matches) == 2  # Only villas
        assert all(m["property"]["property_type"] == "فيلا" for m in matches)

    def test_match_respects_budget(self):
        from src.api.bridge_handler import match_properties
        
        intent = {"area": None, "budget": 3000000, "property_type": None}
        properties = [
            {"area": "الفردوس", "price": 2500000, "property_type": "شقة فاخرة"},
            {"area": "الكوثر", "price": 3500000, "property_type": "شقة فاخرة"},
            {"area": "النخيل", "price": 5000000, "property_type": "شقة فاخرة"},
        ]
        matches = match_properties(intent, properties)
        assert len(matches) == 2  # Within 20% tolerance
        for m in matches:
            assert m["property"]["price"] <= 3000000 * 1.2

    def test_match_returns_top_5(self):
        from src.api.bridge_handler import match_properties
        
        intent = {"area": "الفردوس", "budget": 10000000, "property_type": None}
        properties = [
            {"area": "الفردوس", "price": p, "property_type": "شقة فاخرة"}
            for p in range(2000000, 8000000, 500000)
        ]
        matches = match_properties(intent, properties)
        assert len(matches) <= 5  # Max 5 matches

    def test_match_empty_properties(self):
        from src.api.bridge_handler import match_properties
        
        intent = {"area": "الفردوس", "budget": 3000000, "property_type": "شقة فاخرة"}
        matches = match_properties(intent, [])
        assert len(matches) == 0

    def test_match_none_intent(self):
        from src.api.bridge_handler import match_properties
        
        properties = [
            {"area": "الفردوس", "price": 3000000, "property_type": "شقة فاخرة"},
        ]
        matches = match_properties(None, properties)
        assert len(matches) == 0


# ---------------------------------------------------------------------------
# Full Pipeline Test (parse → score → match → fallback response)
# ---------------------------------------------------------------------------
class TestFullPipeline:
    """Test the complete message processing pipeline for PREMIUM leads."""

    def test_hot_lead_full_flow(self):
        from src.api.bridge_handler import parse_intent, score_lead, match_properties

        message = "عايز أشتري فيلا في الفردوس بميزانية 8 مليون واستعجل ومحتاج حد يساعدني 01012345678"

        # Step 1: Parse intent
        intent = parse_intent(message)
        assert intent["area"] == "الفردوس"
        assert intent["property_type"] == "فيلا"
        assert intent["budget"] == 8000000

        # Step 2: Score lead
        lead = score_lead(intent, message)
        assert lead["quality"] == "platinum"
        assert lead["score"] >= 80

        # Step 3: Match properties
        properties = [
            {"area": "الفردوس", "price": 7500000, "property_type": "فيلا", "bedrooms": 5},
            {"area": "الفردوس", "price": 8500000, "property_type": "فيلا", "bedrooms": 5},
        ]
        matches = match_properties(intent, properties)
        assert len(matches) > 0

    def test_cold_lead_full_flow(self):
        from src.api.bridge_handler import parse_intent, score_lead, match_properties

        message = "ازيك"

        intent = parse_intent(message)
        lead = score_lead(intent, message)
        assert lead["tier"] == "cold"

        properties = [
            {"area": "الفردوس", "price": 3000000, "property_type": "شقة فاخرة"},
        ]
        matches = match_properties(intent, properties)
        assert len(matches) == 0

    def test_commercial_investor_flow(self):
        from src.api.bridge_handler import parse_intent, score_lead, match_properties

        message = "أنا من القاهرة، بدور على محل تجاري في المنطقة الصناعية الأولى بـ 4 مليون جنيه"

        # Step 1: Parse intent
        intent = parse_intent(message)
        assert intent["area"] == "المنطقة الصناعية الأولى"
        assert intent["property_type"] == "محل تجاري"
        assert intent["sale_origin"] == "القاهرة"

        # Step 2: Score lead
        lead = score_lead(intent, message)
        assert lead["quality"] in ["silver", "gold", "platinum"]

        # Step 3: Match properties
        properties = [
            {"area": "المنطقة الصناعية الأولى", "price": 3500000, "property_type": "محل تجاري"},
            {"area": "المنطقة الصناعية الأولى", "price": 4500000, "property_type": "محل تجاري"},
        ]
        matches = match_properties(intent, properties)
        assert len(matches) == 2

    def test_social_housing_rejected(self):
        """Test that social housing requests are completely rejected."""
        from src.api.bridge_handler import parse_intent, score_lead

        message = "عايز شقة إسكان اجتماعي في ابني بيتك بـ 400 ألف جنيه"
        
        intent = parse_intent(message)
        assert intent is None  # Rejected
        
        lead = score_lead(intent, message)
        assert lead["quality"] == "rejected"

    def test_low_budget_rejected(self):
        """Test that low budget requests are rejected."""
        from src.api.bridge_handler import parse_intent, score_lead

        message = "عايز شقة بـ 900 ألف جنيه في المنطقة 5"
        
        intent = parse_intent(message)
        assert intent is None  # Rejected
        
        lead = score_lead(intent, message)
        assert lead["quality"] == "rejected"


# ---------------------------------------------------------------------------
# Timeline Tests
# ---------------------------------------------------------------------------
class TestTimeline:
    """Test timeline values are 'urgent' or 'flexible' only."""

    def test_urgent_timeline(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("عايز فيلا عاجل في الفردوس")
        assert result["timeline"] == "urgent"

    def test_flexible_timeline(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("مش مستعجل، لو في فرصة كويسة")
        assert result["timeline"] == "flexible"

    def test_no_timeline(self):
        from src.api.bridge_handler import parse_intent
        result = parse_intent("عايز فيلا في الفردوس بـ 5 مليون")
        assert result["timeline"] is None
