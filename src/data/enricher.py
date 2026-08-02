"""
Data Enricher — مьер غني البيانات
==================================
Enriches extracted property data with additional context:
- Price per sqm calculation
- Area premium scoring
- Developer reputation lookup
- Market price comparison
- Contact verification

El Sadat City premium real estate focus.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("data.enricher")


# ---------------------------------------------------------------------------
# El Sadat City Area Metadata
# ---------------------------------------------------------------------------
AREA_METADATA = {
    "المنطقة 7 الشريط المميز": {
        "type": "premium_residential",
        "avg_price_per_sqm": 25000,
        "premium_score": 95,
        "facilities": ["مدرسة", "مستشفى", "مساجد", "حدائق", "نوادي رياضية"],
    },
    "المنطقة 9 الشريط المميز": {
        "type": "premium_residential",
        "avg_price_per_sqm": 22000,
        "premium_score": 90,
        "facilities": ["مدرسة", "مساجد", "حدائق"],
    },
    "المنطقة 15 الشريط المميز": {
        "type": "premium_residential",
        "avg_price_per_sqm": 20000,
        "premium_score": 85,
        "facilities": ["مدرسة", "مساجد"],
    },
    "الفردوس": {
        "type": "premium_residential",
        "avg_price_per_sqm": 18000,
        "premium_score": 80,
        "facilities": ["مدرسة", "مساجد", "حدائق"],
    },
    "الكوثر": {
        "type": "premium_residential",
        "avg_price_per_sqm": 19000,
        "premium_score": 82,
        "facilities": ["مدرسة", "مساجد"],
    },
    "النخيل": {
        "type": "premium_residential",
        "avg_price_per_sqm": 21000,
        "premium_score": 88,
        "facilities": ["مدرسة", "مستشفى", "مساجد", "حدائق"],
    },
    "البراميتر": {
        "type": "investment",
        "avg_price_per_sqm": 15000,
        "premium_score": 70,
        "facilities": ["طرق رئيسية", "وسائل نقل"],
    },
    "Polaris Parks": {
        "type": "industrial_modern",
        "avg_price_per_sqm": 18000,
        "premium_score": 75,
        "facilities": ["خدمات لوجستية", "warehousing", "IT infrastructure"],
    },
}


# ---------------------------------------------------------------------------
# Developer Reputation
# ---------------------------------------------------------------------------
DEVELOPER_REPUTATION = {
    "مصر إيطاليا": {"rating": 4.5, "projects": 12, "reputation": "ممتاز"},
    "ال عقارية": {"rating": 4.2, "projects": 8, "reputation": "جيد جداً"},
    "بالم هيلز": {"rating": 4.0, "projects": 6, "reputation": "جيد"},
    "مسك": {"rating": 4.3, "projects": 10, "reputation": "ممتاز"},
    "البروج": {"rating": 3.8, "projects": 5, "reputation": "جيد"},
}


# ---------------------------------------------------------------------------
# DataEnricher
# ---------------------------------------------------------------------------
class DataEnricher:
    """
    Enriches property data with additional context and scoring.

    Features:
    - Price per sqm calculation
    - Area premium scoring
    - Developer reputation lookup
    - Market comparison
    - Contact quality check
    """

    def __init__(self):
        self._enrichment_count = 0

    # ------------------------------------------------------------------
    # Main Enrichment
    # ------------------------------------------------------------------
    def enrich(self, property_data: dict) -> dict:
        """
        Enrich a property dict with additional data.

        Args:
            property_data: Raw property dict from extractor.

        Returns:
            Enriched property dict with new fields.
        """
        enriched = property_data.copy()

        # Price per sqm
        enriched["price_per_sqm"] = self._calculate_price_per_sqm(property_data)

        # Area metadata
        area_info = self._get_area_info(property_data.get("area"))
        if area_info:
            enriched["area_type"] = area_info["type"]
            enriched["area_avg_price"] = area_info["avg_price_per_sqm"]
            enriched["area_premium_score"] = area_info["premium_score"]
            enriched["area_facilities"] = area_info["facilities"]

        # Developer reputation
        dev = property_data.get("developer")
        if dev:
            dev_info = self._get_developer_info(dev)
            if dev_info:
                enriched["developer_rating"] = dev_info["rating"]
                enriched["developer_projects"] = dev_info["projects"]
                enriched["developer_reputation"] = dev_info["reputation"]

        # Market comparison
        enriched["market_comparison"] = self._compare_to_market(property_data)

        # Contact quality
        enriched["contact_quality"] = self._assess_contact_quality(property_data)

        # Data completeness score
        enriched["completeness_score"] = self._calculate_completeness(property_data)

        # Premium flag
        enriched["is_premium"] = self._is_premium(property_data)

        # Enrichment timestamp
        enriched["enriched_at"] = datetime.now(timezone.utc).isoformat()

        self._enrichment_count += 1
        logger.info("Enriched property: price_per_sqm=%s, premium=%s",
                     enriched.get("price_per_sqm"), enriched.get("is_premium"))
        return enriched

    def enrich_batch(self, properties: list[dict]) -> list[dict]:
        """Enrich a batch of properties."""
        return [self.enrich(p) for p in properties]

    # ------------------------------------------------------------------
    # Internal Enrichment Methods
    # ------------------------------------------------------------------
    def _calculate_price_per_sqm(self, data: dict) -> float | None:
        """Calculate price per square meter."""
        price = data.get("price")
        area = data.get("area_sqm")
        if price and area and area > 0:
            return round(price / area, 2)
        return None

    def _get_area_info(self, area: str) -> dict | None:
        """Get area metadata."""
        if area and area in AREA_METADATA:
            return AREA_METADATA[area]
        return None

    def _get_developer_info(self, developer: str) -> dict | None:
        """Get developer reputation info."""
        for name, info in DEVELOPER_REPUTATION.items():
            if name in developer or developer in name:
                return info
        return None

    def _compare_to_market(self, data: dict) -> dict:
        """Compare property price to market average."""
        area = data.get("area")
        price = data.get("price")
        area_sqm = data.get("area_sqm")

        if not area or not price:
            return {"status": "unknown", "message": "Insufficient data"}

        area_info = AREA_METADATA.get(area)
        if not area_info:
            return {"status": "unknown", "message": f"No market data for {area}"}

        avg_price = area_info["avg_price_per_sqm"]
        if area_sqm and area_sqm > 0:
            prop_price_per_sqm = price / area_sqm
            diff_pct = ((prop_price_per_sqm - avg_price) / avg_price) * 100

            if diff_pct > 20:
                verdict = "above_market"
            elif diff_pct < -20:
                verdict = "below_market"
            else:
                verdict = "at_market"

            return {
                "status": verdict,
                "diff_percentage": round(diff_pct, 1),
                "market_avg": avg_price,
                "property_avg": round(prop_price_per_sqm, 2),
            }

        return {"status": "unknown", "message": "No area sqm data"}

    def _assess_contact_quality(self, data: dict) -> dict:
        """Assess quality of contact information."""
        score = 0
        reasons = []

        if data.get("contact_phone"):
            score += 40
            reasons.append("phone_available")
        if data.get("contact_name"):
            score += 20
            reasons.append("name_available")
        if data.get("contact_email"):
            score += 20
            reasons.append("email_available")
        if data.get("source_url"):
            score += 20
            reasons.append("source_url_available")

        if score >= 80:
            quality = "high"
        elif score >= 50:
            quality = "medium"
        else:
            quality = "low"

        return {"score": score, "quality": quality, "reasons": reasons}

    def _calculate_completeness(self, data: dict) -> float:
        """Calculate data completeness score (0-100)."""
        required_fields = ["property_type", "area", "price", "bedrooms", "area_sqm"]
        optional_fields = ["contact_phone", "contact_name", "source_url", "developer"]

        score = 0
        for field in required_fields:
            if data.get(field):
                score += 15  # 15 points each = 75 max for required

        for field in optional_fields:
            if data.get(field):
                score += 8.33  # ~8.33 each = ~25 max for optional

        return min(round(score, 1), 100)

    def _is_premium(self, data: dict) -> bool:
        """Determine if property qualifies as premium."""
        price = data.get("price", 0)
        area = data.get("area", "")

        # Minimum price threshold
        if price < 1_500_000:
            return False

        # Premium area
        area_info = AREA_METADATA.get(area)
        if area_info and area_info.get("premium_score", 0) >= 80:
            return True

        # Premium price point (above 3M EGP)
        return price >= 3000000

    @property
    def stats(self) -> dict:
        """Return enrichment statistics."""
        return {"total_enrichments": self._enrichment_count}
