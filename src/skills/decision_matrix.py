"""
Decision Matrix Skill — مصفوفة القرارات
==========================================
Weighted scoring for real estate decisions: property comparison,
investment analysis, and vendor selection.
"""

import json
import logging

logger = logging.getLogger("skills.decision_matrix")


class DecisionMatrixSkill:
    """Decision analysis with weighted scoring."""

    def compare_properties(self, properties: list[dict], criteria: list[dict] | None = None) -> dict:
        """
        Compare multiple properties using weighted scoring.

        properties: [{"id": "1", "name": "Property A", "scores": {"price": 8, "location": 9}}]
        criteria: [{"name": "price", "weight": 0.3}, {"name": "location", "weight": 0.25}]
        """
        if not criteria:
            criteria = [
                {"name": "price", "weight": 0.25, "description": "Price competitiveness"},
                {"name": "location", "weight": 0.25, "description": "Location quality"},
                {"name": "size", "weight": 0.15, "description": "Size/area"},
                {"name": "condition", "weight": 0.15, "description": "Property condition"},
                {"name": "amenities", "weight": 0.1, "description": "Amenities and features"},
                {"name": "potential", "weight": 0.1, "description": "Investment potential"},
            ]

        total_weight = sum(c["weight"] for c in criteria)
        if total_weight > 0:
            for c in criteria:
                c["normalized_weight"] = round(c["weight"] / total_weight, 3)

        results = []
        for prop in properties:
            scores = prop.get("scores", {})
            weighted_sum = 0
            breakdown = {}

            for c in criteria:
                score = scores.get(c["name"], 5)
                weighted = score * c["normalized_weight"]
                weighted_sum += weighted
                breakdown[c["name"]] = {"score": score, "weight": c["normalized_weight"], "weighted": round(weighted, 3)}

            results.append({
                "id": prop.get("id"),
                "name": prop.get("name"),
                "total_score": round(weighted_sum, 3),
                "breakdown": breakdown,
                "grade": self._score_to_grade(weighted_sum),
            })

        results.sort(key=lambda x: x["total_score"], reverse=True)

        return {
            "criteria": criteria,
            "results": results,
            "winner": results[0] if results else None,
            "comparison_count": len(results),
        }

    def analyze_investment(self, property_data: dict) -> dict:
        """
        Analyze property investment potential.

        property_data: {
            "purchase_price": 2000000,
            "expected_rental": 15000,
            "annual_expenses": 30000,
            "expected_appreciation": 0.08,
            "hold_years": 5,
        }
        """
        price = property_data.get("purchase_price", 0)
        monthly_rent = property_data.get("expected_rental", 0)
        annual_expenses = property_data.get("annual_expenses", 0)
        appreciation_rate = property_data.get("expected_appreciation", 0.05)
        hold_years = property_data.get("hold_years", 5)

        annual_rental = monthly_rent * 12
        net_annual_income = annual_rental - annual_expenses
        gross_yield = (annual_rental / price * 100) if price > 0 else 0
        net_yield = (net_annual_income / price * 100) if price > 0 else 0

        # Future value with appreciation
        future_value = price * ((1 + appreciation_rate) ** hold_years)
        total_appreciation = future_value - price
        total_rental_income = net_annual_income * hold_years
        total_return = total_appreciation + total_rental_income
        total_roi = (total_return / price * 100) if price > 0 else 0
        annual_roi = (total_roi / hold_years) if hold_years > 0 else 0

        # Cap rate
        cap_rate = net_yield

        # Cash on cash return (if financed)
        down_payment_pct = property_data.get("down_payment_pct", 0.2)
        down_payment = price * down_payment_pct
        cash_on_cash = (net_annual_income / down_payment * 100) if down_payment > 0 else 0

        return {
            "property": property_data,
            "analysis": {
                "gross_yield_percent": round(gross_yield, 2),
                "net_yield_percent": round(net_yield, 2),
                "cap_rate_percent": round(cap_rate, 2),
                "cash_on_cash_return_percent": round(cash_on_cash, 2),
                "future_value": round(future_value),
                "total_appreciation": round(total_appreciation),
                "total_rental_income": round(total_rental_income),
                "total_return": round(total_return),
                "total_roi_percent": round(total_roi, 2),
                "annual_roi_percent": round(annual_roi, 2),
            },
            "verdict": self._investment_verdict(total_roi, annual_roi),
        }

    def score_vendor(self, vendor_data: dict) -> dict:
        """Score a vendor/supplier using weighted criteria."""
        criteria = {
            "price": {"weight": 0.25, "score": vendor_data.get("price_score", 5)},
            "quality": {"weight": 0.25, "score": vendor_data.get("quality_score", 5)},
            "reliability": {"weight": 0.2, "score": vendor_data.get("reliability_score", 5)},
            "speed": {"weight": 0.15, "score": vendor_data.get("speed_score", 5)},
            "support": {"weight": 0.15, "score": vendor_data.get("support_score", 5)},
        }

        total = sum(c["weight"] * c["score"] for c in criteria.values())

        return {
            "vendor": vendor_data.get("name", "Unknown"),
            "total_score": round(total, 2),
            "max_possible": 5,
            "grade": self._score_to_grade(total),
            "criteria": {k: {"score": v["score"], "weighted": round(v["weight"] * v["score"], 3)} for k, v in criteria.items()},
            "recommendation": "Recommended" if total >= 3.5 else "Consider alternatives" if total >= 2.5 else "Not recommended",
        }

    def pros_cons_analysis(self, options: list[dict]) -> dict:
        """Generate pros/cons analysis for options."""
        results = []
        for option in options:
            pros = option.get("pros", [])
            cons = option.get("cons", [])
            pros_score = len(pros) * 1
            cons_score = len(cons) * -1
            net_score = pros_score + cons_score

            results.append({
                "name": option.get("name"),
                "pros": pros,
                "cons": cons,
                "pros_count": len(pros),
                "cons_count": len(cons),
                "net_score": net_score,
                "recommendation": "Favor" if net_score > 0 else "Avoid" if net_score < 0 else "Neutral",
            })

        results.sort(key=lambda x: x["net_score"], reverse=True)
        return {"options": results, "winner": results[0] if results else None}

    def _score_to_grade(self, score: float) -> str:
        if score >= 4.5: return "A+"
        if score >= 4.0: return "A"
        if score >= 3.5: return "B+"
        if score >= 3.0: return "B"
        if score >= 2.5: return "C"
        if score >= 2.0: return "D"
        return "F"

    def _investment_verdict(self, total_roi: float, annual_roi: float) -> str:
        if annual_roi >= 15: return "Excellent investment"
        if annual_roi >= 10: return "Good investment"
        if annual_roi >= 7: return "Average investment"
        if annual_roi >= 4: return "Below average"
        return "Poor investment"


def get_decision_tools():
    """Return CrewAI-compatible tools for decision analysis."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class ComparePropertiesInput(BaseModel):
        properties: str = Field(description="JSON array of properties with scores")
        criteria: str = Field(default="", description="JSON array of criteria with weights (optional)")

    class ComparePropertiesTool(BaseTool):
        name: str = "compare_properties"
        description: str = "Compare properties using weighted scoring. Returns ranked results with winner."
        args_schema: type = ComparePropertiesInput

        def _run(self, properties: str, criteria: str = "") -> str:
            skill = DecisionMatrixSkill()
            props = json.loads(properties)
            crits = json.loads(criteria) if criteria else None
            result = skill.compare_properties(props, crits)
            return json.dumps(result, ensure_ascii=False)

    class AnalyzeInvestmentInput(BaseModel):
        purchase_price: float = Field(description="Property purchase price")
        expected_rental: float = Field(description="Expected monthly rental income")
        annual_expenses: float = Field(default=0, description="Annual expenses")
        expected_appreciation: float = Field(default=0.08, description="Expected annual appreciation rate")
        hold_years: int = Field(default=5, description="Years to hold")

    class AnalyzeInvestmentTool(BaseTool):
        name: str = "analyze_investment"
        description: str = "Analyze property investment: ROI, yield, cap rate, cash-on-cash return."
        args_schema: type = AnalyzeInvestmentInput

        def _run(self, purchase_price: float, expected_rental: float, annual_expenses: float = 0, expected_appreciation: float = 0.08, hold_years: int = 5) -> str:
            skill = DecisionMatrixSkill()
            result = skill.analyze_investment({
                "purchase_price": purchase_price,
                "expected_rental": expected_rental,
                "annual_expenses": annual_expenses,
                "expected_appreciation": expected_appreciation,
                "hold_years": hold_years,
            })
            return json.dumps(result, ensure_ascii=False)

    return [ComparePropertiesTool(), AnalyzeInvestmentTool()]
