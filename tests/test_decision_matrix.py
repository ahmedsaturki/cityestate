"""
Tests for Decision Matrix Skill
"""
import pytest
from src.skills.decision_matrix import DecisionMatrixSkill


@pytest.fixture
def skill():
    return DecisionMatrixSkill()


class TestPropertyComparison:
    def test_compare_properties(self, skill):
        props = [
            {"id": "1", "name": "Property A", "scores": {"price": 8, "location": 9}},
            {"id": "2", "name": "Property B", "scores": {"price": 9, "location": 7}},
        ]
        result = skill.compare_properties(props)
        assert result["winner"] is not None
        assert len(result["results"]) == 2
        assert result["results"][0]["grade"] in ["A+", "A", "B+", "B", "C", "D", "F"]

    def test_compare_with_custom_criteria(self, skill):
        props = [{"id": "1", "name": "A", "scores": {"custom": 10}}]
        criteria = [{"name": "custom", "weight": 1.0}]
        result = skill.compare_properties(props, criteria)
        assert result["results"][0]["total_score"] > 0

    def test_empty_comparison(self, skill):
        result = skill.compare_properties([])
        assert result["winner"] is None


class TestInvestmentAnalysis:
    def test_analyze_investment(self, skill):
        data = {
            "purchase_price": 2000000,
            "expected_rental": 15000,
            "annual_expenses": 30000,
            "expected_appreciation": 0.08,
            "hold_years": 5,
        }
        result = skill.analyze_investment(data)
        assert "analysis" in result
        assert result["analysis"]["gross_yield_percent"] > 0
        assert result["analysis"]["total_roi_percent"] > 0
        assert result["verdict"] in ["Excellent investment", "Good investment", "Average investment", "Below average", "Poor investment"]

    def test_investment_with_zero_price(self, skill):
        result = skill.analyze_investment({"purchase_price": 0, "expected_rental": 0})
        assert result["analysis"]["gross_yield_percent"] == 0


class TestVendorScoring:
    def test_score_vendor(self, skill):
        vendor = {
            "name": "Vendor A",
            "price_score": 8,
            "quality_score": 9,
            "reliability_score": 7,
            "speed_score": 6,
            "support_score": 8,
        }
        result = skill.score_vendor(vendor)
        assert result["total_score"] > 0
        assert result["recommendation"] in ["Recommended", "Consider alternatives", "Not recommended"]


class TestProsCons:
    def test_pros_cons(self, skill):
        options = [
            {"name": "Option A", "pros": ["Good price", "Great location"], "cons": ["Small"]},
            {"name": "Option B", "pros": ["Big"], "cons": ["Expensive", "Bad location"]},
        ]
        result = skill.pros_cons_analysis(options)
        assert result["winner"]["name"] == "Option A"

    def test_empty_pros_cons(self, skill):
        result = skill.pros_cons_analysis([])
        assert result["winner"] is None
