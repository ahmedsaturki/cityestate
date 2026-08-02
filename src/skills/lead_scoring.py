"""
Lead Scoring & Auto-Matching — تقييم العملاء والمطابقة التلقائية
================================================================
AI-powered lead scoring and automatic property matching.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("skills.lead_scoring")

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "lead_scoring"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class LeadScoringSkill:
    """AI-powered lead scoring and auto-matching."""

    def __init__(self):
        self.leads_file = DATA_DIR / "scored_leads.json"
        self.rules_file = DATA_DIR / "scoring_rules.json"
        self._load_rules()

    def _load_rules(self):
        """Load scoring rules."""
        if self.rules_file.exists():
            self.rules = json.loads(self.rules_file.read_text(encoding="utf-8"))
        else:
            self.rules = {
                "budget_weight": 0.25,
                "location_weight": 0.20,
                "urgency_weight": 0.20,
                "engagement_weight": 0.15,
                "recency_weight": 0.10,
                "source_weight": 0.10,
                "source_scores": {
                    "referral": 90,
                    "website": 70,
                    "facebook": 60,
                    "whatsapp": 80,
                    "phone_call": 85,
                    "walk_in": 95,
                    "webhook": 50,
                    "unknown": 30,
                },
                "urgency_signals": [
                    "immediate",
                    "asap",
                    "urgently",
                    "في أسرع وقت",
                    "عاجل",
                    "محتاج دلوقتي",
                ],
            }
            self._save_rules()

    def _save_rules(self):
        """Save scoring rules."""
        self.rules_file.write_text(json.dumps(self.rules, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Lead Scoring
    # ------------------------------------------------------------------
    def score_lead(self, lead_data: dict) -> dict:
        """
        Score a lead based on multiple factors.
        
        Returns:
            {
                "score": 0-100,
                "tier": "hot|warm|cold",
                "breakdown": {...},
                "recommendation": "..."
            }
        """
        score = 0
        breakdown = {}

        # Budget score (0-25)
        budget = lead_data.get("max_budget", 0) or lead_data.get("budget", 0)
        if budget >= 10_000_000:
            budget_score = 25
        elif budget >= 5_000_000:
            budget_score = 20
        elif budget >= 2_000_000:
            budget_score = 15
        elif budget >= 1_000_000:
            budget_score = 10
        else:
            budget_score = 5
        score += budget_score
        breakdown["budget"] = budget_score

        # Location score (0-20)
        area = (lead_data.get("area") or "").lower()
        premium_areas = ["sheikh zayed", "new cairo", "new capital", "madinaty", "90 north", "shorouk"]
        if any(a in area for a in premium_areas):
            location_score = 20
        elif area:
            location_score = 12
        else:
            location_score = 5
        score += location_score
        breakdown["location"] = location_score

        # Urgency score (0-20)
        message = (lead_data.get("message") or "").lower()
        urgency = lead_data.get("urgency", "")
        is_urgent = any(sig in message for sig in self.rules["urgency_signals"]) or urgency == "high"
        urgency_score = 20 if is_urgent else 10
        score += urgency_score
        breakdown["urgency"] = urgency_score

        # Engagement score (0-15)
        engagement = lead_data.get("engagement_score", 50)
        engagement_score = int(engagement * 0.15)
        score += engagement_score
        breakdown["engagement"] = engagement_score

        # Recency score (0-10)
        recency = lead_data.get("recency_hours", 24)
        if recency <= 1:
            recency_score = 10
        elif recency <= 24:
            recency_score = 8
        elif recency <= 72:
            recency_score = 5
        else:
            recency_score = 2
        score += recency_score
        breakdown["recency"] = recency_score

        # Source score (0-10)
        source = (lead_data.get("source") or "unknown").lower()
        source_scores = self.rules.get("source_scores", {})
        source_score = int(source_scores.get(source, 30) * 0.1)
        score += source_score
        breakdown["source"] = source_score

        # Determine tier
        if score >= 70:
            tier = "hot"
            recommendation = "🔥 عميل ساخن! تواصل فوراً عبر WhatsApp"
        elif score >= 45:
            tier = "warm"
            recommendation = "🟡 عميل مهتم. أرسل تفاصيل العقارات المناسبة"
        else:
            tier = "cold"
            recommendation = "❄️ عميل بارد. أضفه لقائمة التسويق الآلي"

        return {
            "score": min(score, 100),
            "tier": tier,
            "breakdown": breakdown,
            "recommendation": recommendation,
        }

    # ------------------------------------------------------------------
    # Auto-Matching
    # ------------------------------------------------------------------
    def match_lead_to_properties(self, lead_data: dict, properties: list[dict]) -> list[dict]:
        """
        Automatically match a lead to the best properties.
        
        Returns list of matched properties sorted by match score.
        """
        matches = []

        for prop in properties:
            score = self._calculate_match_score(lead_data, prop)
            if score > 20:  # Minimum threshold
                matches.append({
                    "property": prop,
                    "score": round(score, 1),
                    "reasons": self._get_match_reasons(lead_data, prop),
                })

        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:5]  # Top 5 matches

    def _calculate_match_score(self, lead: dict, prop: dict) -> float:
        """Calculate match score between lead and property."""
        score = 0

        # Budget match (40% weight)
        budget = lead.get("max_budget", 0) or lead.get("budget", 0)
        price = prop.get("price", 0)
        if budget and price:
            if price <= budget:
                score += 40 * (1 - (budget - price) / budget)
            elif price <= budget * 1.1:  # 10% over budget
                score += 20
            else:
                score += 0

        # Location match (25% weight)
        lead_area = (lead.get("area") or "").lower()
        prop_area = (prop.get("area") or prop.get("location") or "").lower()
        if lead_area and prop_area:
            if lead_area in prop_area or prop_area in lead_area:
                score += 25
            elif any(a in prop_area for a in lead_area.split()):
                score += 15
            else:
                score += 5

        # Bedrooms match (20% weight)
        lead_bedrooms = lead.get("bedrooms")
        prop_bedrooms = prop.get("bedrooms")
        if lead_bedrooms and prop_bedrooms:
            if lead_bedrooms == prop_bedrooms:
                score += 20
            elif abs(lead_bedrooms - prop_bedrooms) <= 1:
                score += 10
            else:
                score += 0

        # Type match (15% weight)
        lead_type = (lead.get("property_type") or "").lower()
        prop_type = (prop.get("property_type") or "").lower()
        if lead_type and prop_type:
            if lead_type == prop_type:
                score += 15
            elif lead_type in ["apartment", "duplex"] and prop_type in ["apartment", "duplex"] or lead_type in ["villa", "townhouse"] and prop_type in ["villa", "townhouse"]:
                score += 10
            else:
                score += 3
        else:
            score += 8  # Unknown type, give partial credit

        return min(score, 100)

    def _get_match_reasons(self, lead: dict, prop: dict) -> list[str]:
        """Get human-readable reasons for match."""
        reasons = []

        budget = lead.get("max_budget", 0) or lead.get("budget", 0)
        price = prop.get("price", 0)
        if budget and price and price <= budget:
            reasons.append(f"السعر مناسب ({price:,.0f} ≤ {budget:,.0f})")

        lead_area = (lead.get("area") or "").lower()
        prop_area = (prop.get("area") or prop.get("location") or "").lower()
        if lead_area and prop_area and (lead_area in prop_area or prop_area in lead_area):
            reasons.append(f"الموقع مطابق ({prop.get('area', '')})")

        lead_bed = lead.get("bedrooms")
        prop_bed = prop.get("bedrooms")
        if lead_bed and prop_bed and lead_bed == prop_bed:
            reasons.append(f"عدد الغرف مطابق ({prop_bed} غرف)")

        return reasons

    # ------------------------------------------------------------------
    # Batch Scoring
    # ------------------------------------------------------------------
    def score_leads_batch(self, leads: list[dict]) -> list[dict]:
        """Score multiple leads at once."""
        scored = []
        for lead in leads:
            result = self.score_lead(lead)
            result["lead"] = lead
            scored.append(result)

        # Sort by score
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def get_scoring_dashboard(self) -> dict:
        """Get scoring overview dashboard."""
        leads_file = DATA_DIR / "scored_leads.json"
        if leads_file.exists():
            leads = json.loads(leads_file.read_text(encoding="utf-8"))
        else:
            leads = []

        hot = sum(1 for l in leads if l.get("tier") == "hot")
        warm = sum(1 for l in leads if l.get("tier") == "warm")
        cold = sum(1 for l in leads if l.get("tier") == "cold")

        return {
            "total_scored": len(leads),
            "hot_leads": hot,
            "warm_leads": warm,
            "cold_leads": cold,
            "avg_score": sum(l.get("score", 0) for l in leads) / len(leads) if leads else 0,
            "conversion_potential": f"{hot + warm}/{len(leads)}" if leads else "0/0",
        }


# ---------------------------------------------------------------------------
# CrewAI Tools
# ---------------------------------------------------------------------------
from crewai.tools import BaseTool
from pydantic import BaseModel
from pydantic import Field as PydanticField


class LeadScoreInput(BaseModel):
    lead_data: str = PydanticField(description="JSON string with lead data (name, phone, area, budget, source, message)")


class LeadScoreTool(BaseTool):
    """Score a lead based on multiple factors (budget, location, urgency, source)."""
    name: str = "lead_score"
    description: str = (
        "Score a lead 0-100 and classify as hot/warm/cold. "
        "Input: JSON with lead data. Returns score, tier, breakdown, and recommendation."
    )
    args_schema: type = LeadScoreInput

    def _run(self, lead_data: str) -> str:
        try:
            data = json.loads(lead_data)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input"})

        skill = LeadScoringSkill()
        result = skill.score_lead(data)
        return json.dumps(result, ensure_ascii=False)


class LeadMatchInput(BaseModel):
    lead_data: str = PydanticField(description="JSON string with lead data")
    properties_json: str = PydanticField(description="JSON string with list of properties")


class LeadMatchTool(BaseTool):
    """Auto-match a lead to the best properties using AI scoring."""
    name: str = "lead_match"
    description: str = (
        "Match a lead to available properties. Returns top 5 matches with scores and reasons. "
        "Input: lead data JSON + properties list JSON."
    )
    args_schema: type = LeadMatchInput

    def _run(self, lead_data: str, properties_json: str) -> str:
        try:
            lead = json.loads(lead_data)
            props = json.loads(properties_json)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input"})

        skill = LeadScoringSkill()
        matches = skill.match_lead_to_properties(lead, props)
        return json.dumps({"matches": matches}, ensure_ascii=False)


class LeadBatchScoreInput(BaseModel):
    leads_json: str = PydanticField(description="JSON string with list of leads")


class LeadBatchScoreTool(BaseTool):
    """Score multiple leads at once and rank them by priority."""
    name: str = "lead_batch_score"
    description: str = (
        "Score and rank multiple leads by conversion potential. "
        "Returns sorted list with scores and tiers."
    )
    args_schema: type = LeadBatchScoreInput

    def _run(self, leads_json: str) -> str:
        try:
            leads = json.loads(leads_json)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input"})

        skill = LeadScoringSkill()
        results = skill.score_leads_batch(leads)
        return json.dumps({"scored_leads": results}, ensure_ascii=False)


class LeadDashboardTool(BaseTool):
    """Get lead scoring dashboard overview."""
    name: str = "lead_scoring_dashboard"
    description: str = (
        "Get overview of lead scoring: total scored, hot/warm/cold distribution, "
        "average score, and conversion potential."
    )

    def _run(self) -> str:
        skill = LeadScoringSkill()
        dashboard = skill.get_scoring_dashboard()
        return json.dumps(dashboard, ensure_ascii=False)


def get_lead_scoring_tools() -> list:
    """Return all lead scoring tools."""
    return [
        LeadScoreTool(),
        LeadMatchTool(),
        LeadBatchScoreTool(),
        LeadDashboardTool(),
    ]
