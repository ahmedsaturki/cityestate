"""
Data Quality Scorer — مقييم جودة البيانات
==========================================
Scores data quality for property listings and lead records.
Identifies missing fields, inconsistencies, and data issues.

El Sadat City premium real estate focus.
"""

import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger("data.quality")


# ---------------------------------------------------------------------------
# Quality Thresholds
# ---------------------------------------------------------------------------
QUALITY_THRESHOLDS = {
    "excellent": 90,
    "good": 75,
    "acceptable": 60,
    "poor": 40,
    "incomplete": 0,
}

# Required fields for a complete property listing
PROPERTY_REQUIRED_FIELDS = [
    "property_type", "area", "price", "bedrooms", "area_sqm",
]

PROPERTY_OPTIONAL_FIELDS = [
    "contact_phone", "contact_name", "developer", "project_name",
    "source_url", "description", "bathrooms", "delivery_date",
]

# Required fields for a lead record
LEAD_REQUIRED_FIELDS = ["client_name", "phone"]

LEAD_OPTIONAL_FIELDS = [
    "email", "area", "property_type", "budget", "bedrooms",
]


# ---------------------------------------------------------------------------
# DataQualityScorer
# ---------------------------------------------------------------------------
class DataQualityScorer:
    """
    Scores data quality for property listings and lead records.

    Features:
    - Completeness scoring (required + optional fields)
    - Freshness scoring (data age)
    - Consistency scoring (cross-field validation)
    - Duplicate detection
    - Quality tier assignment
    """

    def __init__(self):
        self._score_count = 0

    # ------------------------------------------------------------------
    # Property Quality Scoring
    # ------------------------------------------------------------------
    def score_property(self, property_data: dict) -> dict:
        """
        Score the quality of a property listing.

        Args:
            property_data: Property dict.

        Returns:
            dict with:
                - overall_score: 0-100
                - completeness: 0-100
                - freshness: 0-100
                - consistency: 0-100
                - quality_tier: excellent/good/acceptable/poor/incomplete
                - issues: list of identified issues
                - recommendations: list of improvement suggestions
        """
        issues = []
        recommendations = []

        # 1. Completeness Score (40% weight)
        completeness = self._score_completeness(
            property_data, PROPERTY_REQUIRED_FIELDS, PROPERTY_OPTIONAL_FIELDS
        )
        if completeness < 50:
            issues.append("low_completeness")
            recommendations.append("Add more property details")

        # 2. Freshness Score (20% weight)
        freshness = self._score_freshness(property_data)
        if freshness < 30:
            issues.append("stale_data")
            recommendations.append("Update property listing")

        # 3. Consistency Score (30% weight)
        consistency = self._score_property_consistency(property_data)
        if consistency < 50:
            issues.append("inconsistent_data")
            recommendations.append("Verify cross-field consistency")

        # 4. Format Score (10% weight)
        format_score = self._score_property_format(property_data)
        if format_score < 50:
            issues.append("format_issues")
            recommendations.append("Fix formatting issues")

        # Overall score (weighted)
        overall = (
            completeness * 0.40 +
            freshness * 0.20 +
            consistency * 0.30 +
            format_score * 0.10
        )

        # Quality tier
        quality_tier = self._assign_tier(overall)

        # Premium validation
        if property_data.get("price", 0) < 1_500_000:
            issues.append("below_minimum_price")
            recommendations.append("Remove or update: below 1.5M EGP minimum")

        self._score_count += 1
        result = {
            "overall_score": round(overall, 1),
            "completeness": round(completeness, 1),
            "freshness": round(freshness, 1),
            "consistency": round(consistency, 1),
            "format_score": round(format_score, 1),
            "quality_tier": quality_tier,
            "issues": issues,
            "recommendations": recommendations,
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("Property quality: %.1f (%s) — %d issues",
                     overall, quality_tier, len(issues))
        return result

    # ------------------------------------------------------------------
    # Lead Quality Scoring
    # ------------------------------------------------------------------
    def score_lead(self, lead_data: dict) -> dict:
        """
        Score the quality of a lead record.

        Args:
            lead_data: Lead/client request dict.

        Returns:
            dict with quality score, tier, issues, and recommendations.
        """
        issues = []
        recommendations = []

        # 1. Completeness (50% weight)
        completeness = self._score_completeness(
            lead_data, LEAD_REQUIRED_FIELDS, LEAD_OPTIONAL_FIELDS
        )
        if completeness < 50:
            issues.append("low_completeness")
            recommendations.append("Add missing contact information")

        # 2. Phone quality (25% weight)
        phone_score = self._score_phone_quality(lead_data.get("phone", ""))
        if phone_score < 50:
            issues.append("invalid_phone")
            recommendations.append("Verify phone number format")

        # 3. Intent clarity (25% weight)
        intent_score = self._score_intent_clarity(lead_data)
        if intent_score < 50:
            issues.append("vague_intent")
            recommendations.append("Clarify buyer requirements")

        # Overall
        overall = completeness * 0.50 + phone_score * 0.25 + intent_score * 0.25
        quality_tier = self._assign_tier(overall)

        self._score_count += 1
        return {
            "overall_score": round(overall, 1),
            "completeness": round(completeness, 1),
            "phone_quality": round(phone_score, 1),
            "intent_clarity": round(intent_score, 1),
            "quality_tier": quality_tier,
            "issues": issues,
            "recommendations": recommendations,
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Batch Scoring
    # ------------------------------------------------------------------
    def score_batch(self, items: list[dict], item_type: str = "property") -> dict:
        """
        Score a batch of items and return aggregate stats.

        Args:
            items: List of property or lead dicts.
            item_type: "property" or "lead".

        Returns:
            dict with aggregate stats and per-item scores.
        """
        scores = []
        for item in items:
            if item_type == "property":
                result = self.score_property(item)
            else:
                result = self.score_lead(item)
            scores.append(result)

        # Aggregate stats
        overall_scores = [s["overall_score"] for s in scores]
        tier_counts = {}
        for s in scores:
            tier = s["quality_tier"]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        return {
            "total_items": len(items),
            "avg_score": round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else 0,
            "min_score": min(overall_scores) if overall_scores else 0,
            "max_score": max(overall_scores) if overall_scores else 0,
            "tier_distribution": tier_counts,
            "scores": scores,
        }

    # ------------------------------------------------------------------
    # Duplicate Detection
    # ------------------------------------------------------------------
    def find_duplicates(self, items: list[dict], key_fields: list[str] | None = None) -> list[list[int]]:
        """
        Find duplicate items based on key fields.

        Args:
            items: List of item dicts.
            key_fields: Fields to compare for duplicates.

        Returns:
            List of lists, each inner list contains indices of duplicate items.
        """
        if not key_fields:
            key_fields = ["area", "price", "property_type", "bedrooms"]

        # Build signature map
        sig_map: dict[str, list[int]] = {}
        for i, item in enumerate(items):
            sig_parts = []
            for field in key_fields:
                val = item.get(field)
                sig_parts.append(str(val).lower() if val else "")
            sig = "|".join(sig_parts)
            if sig not in sig_map:
                sig_map[sig] = []
            sig_map[sig].append(i)

        # Return groups with >1 item
        return [indices for indices in sig_map.values() if len(indices) > 1]

    # ------------------------------------------------------------------
    # Internal Scoring Methods
    # ------------------------------------------------------------------
    def _score_completeness(self, data: dict, required: list[str],
                             optional: list[str]) -> float:
        """Score field completeness."""
        score = 0

        # Required fields (15 points each)
        for field in required:
            if data.get(field):
                score += 15

        # Optional fields (8.33 points each)
        for field in optional:
            if data.get(field):
                score += 8.33

        return min(score, 100)

    def _score_freshness(self, data: dict) -> float:
        """Score data freshness based on timestamps."""
        now = datetime.now(timezone.utc)

        # Check various timestamp fields
        for field in ["created_at", "updated_at", "crawled_at", "extracted_at"]:
            ts = data.get(field)
            if ts:
                try:
                    if isinstance(ts, str):
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    else:
                        dt = ts
                    age_days = (now - dt).days
                    if age_days <= 1:
                        return 100
                    elif age_days <= 7:
                        return 80
                    elif age_days <= 30:
                        return 60
                    elif age_days <= 90:
                        return 40
                    else:
                        return 20
                except (ValueError, TypeError):
                    continue

        return 50  # Default if no timestamp found

    def _score_property_consistency(self, data: dict) -> float:
        """Score cross-field consistency for properties."""
        score = 100
        issues = []

        # Price vs area consistency
        price = data.get("price")
        area = data.get("area_sqm")
        if price and area and area > 0:
            price_per_sqm = price / area
            if price_per_sqm < 5000:
                issues.append("very_low_price_per_sqm")
                score -= 20
            elif price_per_sqm > 100000:
                issues.append("very_high_price_per_sqm")
                score -= 20

        # Bedrooms vs area consistency
        bedrooms = data.get("bedrooms")
        if bedrooms is not None and area:
            if bedrooms == 0 and area > 100:
                issues.append("studio_too_large")
                score -= 10
            elif bedrooms >= 4 and area < 80:
                issues.append("too_many_bedrooms_for_area")
                score -= 10

        # Budget range consistency
        min_budget = data.get("min_budget")
        max_budget = data.get("max_budget")
        if min_budget and max_budget and min_budget > max_budget:
            issues.append("inverted_budget_range")
            score -= 15

        return max(score, 0)

    def _score_property_format(self, data: dict) -> float:
        """Score formatting consistency."""
        score = 100

        # Title format
        title = data.get("title", "")
        if title and len(title) < 10:
            score -= 10

        # Description format
        desc = data.get("description", "")
        if desc and len(desc) < 20:
            score -= 10

        # Phone format
        phone = data.get("contact_phone", "")
        if phone and not phone.startswith("+"):
            score -= 5

        return max(score, 0)

    def _score_phone_quality(self, phone: str) -> float:
        """Score phone number quality."""
        if not phone:
            return 0

        # Check Egyptian format
        cleaned = re.sub(r"[\s\-\(\)]", "", phone)
        if re.match(r"^\+20\d{10}$", cleaned):
            return 100
        elif re.match(r"^01\d{9}$", cleaned):
            return 80
        elif re.match(r"^\d{11}$", cleaned):
            return 60
        else:
            return 30

    def _score_intent_clarity(self, data: dict) -> float:
        """Score how clear the buyer intent is."""
        score = 0

        if data.get("property_type"):
            score += 30
        if data.get("area"):
            score += 25
        if data.get("budget") or data.get("max_budget"):
            score += 25
        if data.get("bedrooms"):
            score += 20

        return min(score, 100)

    def _assign_tier(self, score: float) -> str:
        """Assign quality tier based on score."""
        if score >= QUALITY_THRESHOLDS["excellent"]:
            return "excellent"
        elif score >= QUALITY_THRESHOLDS["good"]:
            return "good"
        elif score >= QUALITY_THRESHOLDS["acceptable"]:
            return "acceptable"
        elif score >= QUALITY_THRESHOLDS["poor"]:
            return "poor"
        else:
            return "incomplete"

    @property
    def stats(self) -> dict:
        """Return scoring statistics."""
        return {"total_scores": self._score_count}
