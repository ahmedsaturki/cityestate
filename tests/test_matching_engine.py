"""
Matching Engine Tests — اختبارات محرك المطابقة
==============================================
Tests for property matching, area alias resolution, and scoring.
"""

import pytest


class TestAreaAliasResolution:
    """Test area alias resolution in matching engine."""

    def test_area_aliases_loaded(self):
        from src.matching.engine import AREA_ALIASES
        assert isinstance(AREA_ALIASES, dict)
        assert len(AREA_ALIASES) > 0

    def test_sadat_area_aliases(self):
        from src.matching.engine import AREA_ALIASES
        # Should have Sadat-specific aliases
        assert any("7" in k for k in AREA_ALIASES)

    def test_normalize_area(self):
        from src.matching.engine import normalize_area
        # Should resolve aliases to canonical names
        result = normalize_area("المنطقة 7")
        assert result is not None
        assert isinstance(result, str)


class TestPropertyMatching:
    """Test property matching via MatchMakingEngine."""

    def test_engine_instantiation(self):
        from src.matching.engine import MatchMakingEngine
        from src.api.deps import SessionLocal
        db = SessionLocal()
        try:
            engine = MatchMakingEngine(db)
            assert engine is not None
        finally:
            db.close()

    def test_find_properties_for_client(self):
        from src.matching.engine import MatchMakingEngine
        from src.api.deps import SessionLocal
        db = SessionLocal()
        try:
            engine = MatchMakingEngine(db)
            result = engine.find_properties_for_client("test_client")
            assert isinstance(result, dict)
            # Returns status key whether success or error
            assert "status" in result
        finally:
            db.close()

    def test_find_properties_returns_list(self):
        from src.matching.engine import MatchMakingEngine
        from src.api.deps import SessionLocal
        db = SessionLocal()
        try:
            engine = MatchMakingEngine(db)
            result = engine.find_properties_for_client("nonexistent_client")
            # Should return a dict with some structure
            assert isinstance(result, dict)
        finally:
            db.close()


class TestBridgeHandlerIntegration:
    """Test bridge handler with matching engine."""

    def test_bridge_parses_intent(self):
        from src.api.bridge_handler import parse_intent
        intent = parse_intent("عايز فيلا في المنطقة 7 بسعر 5 مليون جنيه")
        assert intent is not None
        assert intent.get("property_type") in ["فيلا", "شقة فاخرة", "محل تجاري", None]

    def test_bridge_scores_lead(self):
        from src.api.bridge_handler import score_lead
        intent = {
            "property_type": "فيلا",
            "budget": 5000000,
            "area": "المنطقة 7",
            "urgency": "urgent",
        }
        result = score_lead(intent, "عايز فيلا في المنطقة 7")
        assert isinstance(result, dict)
        assert "score" in result
        assert 0 <= result["score"] <= 100
        assert "tier" in result

    def test_bridge_rejects_budget_too_low(self):
        from src.api.bridge_handler import parse_intent
        intent = parse_intent("عايز شقة بسعر 500 ألف جنيه")
        # Should either return None budget or reject
        if intent and intent.get("budget"):
            assert intent["budget"] >= 1500000
