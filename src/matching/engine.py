"""
Match-Making Engine — محرك المطابقة الآلية
=============================================
Automatically match client requests to available properties.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.database.models import ClientRequest, Property

logger = logging.getLogger("matching")


# ---------------------------------------------------------------------------
# Area Aliases — مرادفات المناطق
# ---------------------------------------------------------------------------
AREA_ALIASES = {
    # General Cairo areas
    "mdr": "madinaty",
    "madinaty": "madinaty",
    "new cairo": "new cairo",
    "cairo new": "new cairo",
    "nac": "new administrative capital",
    "new capital": "new administrative capital",
    "tagamoa": "tagamoa",
    "tagamoa el awal": "tagamoa",
    "5th settlement": "fifth settlement",
    "5th": "fifth settlement",
    "fifth": "fifth settlement",
    "october": "6th october",
    "6th october": "6th october",
    "sheraton": "sheraton",
    "heliopolis": "heliopolis",
    "nasr city": "nasr city",
    "maadi": "maadi",
    "zamalek": "zamalek",
    "downtown": "downtown",
    "ain sokhna": "ain sokhna",
    "sahel": "north coast",
    "north coast": "north coast",
    "el gouna": "el gouna",
    "sidi abd el rahman": "sidi abd el rahman",
    "sheikh zayed": "sheikh zayed",
    "el sheikh zayed": "sheikh zayed",
    "mohandessin": "mohandessin",
    "mohandesin": "mohandessin",
    "dokki": "dokki",
    "doqqi": "dokki",
    "october city": "6th october",
    "6 october": "6th october",
    "shubra": "shubra",
    "ain shams": "ain shams",
    "shams": "ain shams",
    "hadaeq el qobba": "hadaeq el qobba",
    "el rehab": "el rehab",
    "rehab": "el rehab",
    "mountain view": "mountain view",
    "palm hills": "palm hills",
    "palm hill": "palm hills",
    "beverly hills": "beverly hills",
    "beverly": "beverly hills",
    "madinaty": "madinaty",
    "el shorouk": "el shorouk",
    "shorouk": "el shorouk",
    "badr city": "badr city",
    "badr": "badr city",
    "obour": "obour city",
    "obour city": "obour city",
    "10th of ramadan": "10th of ramadan",
    "10th ramadan": "10th of ramadan",
    "tanta": "tanta",
    "alexandria": "alexandria",
    "alex": "alexandria",
    "giza": "giza",
    "faisal": "faisal",
    "haram": "haram",
    
    # El Sadat City Premium Areas
    "الشريط المميز": "المنطقة 7 الشريط المميز",
    "شريط المميز": "المنطقة 7 الشريط المميز",
    "شريط 7": "المنطقة 7 الشريط المميز",
    "شريط 9": "المنطقة 9 الشريط المميز",
    "شريط 15": "المنطقة 15 الشريط المميز",
    "الفردوس": "الفردوس",
    "الكوثر": "الكوثر",
    "النخيل": "النخيل",
    "الروضة": "الروضة",
    "البراميتر": "البراميتر",
    "النرجس": "النرجس",
    "الريحان": "الريحان",
    
    # Industrial Zones
    "الصناعية": "المنطقة الصناعية الأولى",
    "المنطقة الصناعية": "المنطقة الصناعية الأولى",
    "الصناعية الأولى": "المنطقة الصناعية الأولى",
    "الصناعية الثانية": "المنطقة الصناعية الثانية",
    "الصناعية الثالثة": "المنطقة الصناعية الثالثة",
    "الصناعية الرابعة": "المنطقة الصناعية الرابعة",
    "الصناعية الخامسة": "المنطقة الصناعية الخامسة",
    "الصناعية السادسة": "المنطقة الصناعية السادسة",
    "الصناعية السابعة": "المنطقة الصناعية السابعة",
    "بولاريس": "Polaris Parks",
    "بولاريس باركس": "Polaris Parks",
    "polaris": "Polaris Parks",
    "polaris parks": "Polaris Parks",
    
    # City aliases
    "مدينة السادات": "مدينة السادات",
    "السادات": "مدينة السادات",
    "sadat": "مدينة السادات",
    "el sadat": "مدينة السادات",
    "sadat city": "مدينة السادات",
    "الشيخ زايد": "sheikh zayed",
    "زايد": "sheikh zayed",
    "المهندسين": "mohandessin",
    "الدقى": "dokki",
    "مصر الجديدة": "heliopolis",
    "الشروق": "el shorouk",
    "بدر": "badr city",
    "العبور": "obour city",
    "الرحاب": "el rehab",
    "الشروكة": "el shorouk",
    "التجمع الخامس": "fifth settlement",
    "التجمع": "new cairo",
    "القاهرة الجديدة": "new cairo",
    "العاصمة الإدارية": "new administrative capital",
    "العاصمة": "new administrative capital",
    "التجمع الاول": "tagamoa",
    "التجمعة": "tagamoa",
    "العبور": "obour city",
    "شبرا": "shubra",
    "عين شمس": "ain shams",
    "حدائق القبة": "hadaeq el qobba",
    "بالم هيلز": "palm hills",
    "بالم": "palm hills",
    "ماونتن فيو": "mountain view",
    "بيفرلي هيلز": "beverly hills",
    "مدينتي": "madinaty",
    "6 اكتوبر": "6th october",
    "السادس من اكتوبر": "6th october",
    "اكتوبر": "6th october",
    "الزمالك": "zamalek",
    "وسط البلد": "downtown",
    "المعادي": "maadi",
    "حلوان": "helwan",
    "الشروق": "el shorouk",
    "حلوان": "helwan",
    "طنطا": "tanta",
    "الاسكندرية": "alexandria",
    "اسكندرية": "alexandria",
    "جدة": "jeddah",
    "جيزه": "giza",
    "فيصل": "faisal",
    "هرم": "haram",
}


def normalize_area(area: str) -> str:
    """Normalize area name using aliases."""
    if not area:
        return ""
    lower = area.lower().strip()
    return AREA_ALIASES.get(lower, lower)


# ---------------------------------------------------------------------------
# Match Scoring — حساب درجة التطابق
# ---------------------------------------------------------------------------
class MatchScorer:
    """Calculate match scores between requests and properties."""

    # Weights for different factors — must sum to 1.0
    WEIGHTS = {
        "area": 0.25,
        "price": 0.25,
        "type": 0.15,
        "bedrooms": 0.10,
        "area_sqm": 0.10,
        "payment": 0.05,
        "amenities": 0.10,
    }

    def score(self, request: ClientRequest, property: Property) -> float:
        """Calculate total match score (0.0 to 1.0)."""
        scores = {}

        # Area match
        scores["area"] = self._area_score(request, property)

        # Price match
        scores["price"] = self._price_score(request, property)

        # Property type match
        scores["type"] = self._type_score(request, property)

        # Bedrooms match
        scores["bedrooms"] = self._bedroom_score(request, property)

        # Area size match (new)
        scores["area_sqm"] = self._area_sqm_score(request, property)

        # Payment plan preference (new)
        scores["payment"] = self._payment_score(request, property)

        # Amenities/notes match
        scores["amenities"] = self._amenities_score(request, property)

        # Weighted total
        total = sum(
            scores[factor] * weight
            for factor, weight in self.WEIGHTS.items()
        )

        return round(total, 3)

    def _area_score(self, req: ClientRequest, prop: Property) -> float:
        """Score area/location match."""
        if not req.area:
            return 0.5  # No preference = neutral

        req_area = normalize_area(req.area)
        prop_area = normalize_area(prop.area or "")
        prop_district = normalize_area(prop.district or "")

        if req_area == prop_area:
            return 1.0
        if req_area in prop_area or prop_area in req_area:
            return 0.8
        if req_area == prop_district:
            return 0.7
        return 0.0

    def _price_score(self, req: ClientRequest, prop: Property) -> float:
        """Score price match."""
        if not req.min_budget and not req.max_budget:
            return 0.5  # No budget = neutral

        price = prop.price
        min_b = req.min_budget or 0
        max_b = req.max_budget or float("inf")

        if min_b <= price <= max_b:
            return 1.0  # Perfect match

        if price < min_b:
            # Below budget — still good
            ratio = price / min_b if min_b > 0 else 0
            return 0.3 + (0.5 * ratio)

        # Over budget
        if max_b > 0:
            over_ratio = (price - max_b) / max_b
            if over_ratio <= 0.1:  # Within 10% over
                return 0.6
            if over_ratio <= 0.2:  # Within 20% over
                return 0.4
            if over_ratio <= 0.3:  # Within 30% over
                return 0.2
        return 0.0

    def _type_score(self, req: ClientRequest, prop: Property) -> float:
        """Score property type match."""
        if not req.property_type:
            return 0.5

        req_type = req.property_type.lower()
        prop_type = (prop.property_type or "").lower()

        if req_type == prop_type:
            return 1.0
        return 0.0

    def _bedroom_score(self, req: ClientRequest, prop: Property) -> float:
        """Score bedroom count match."""
        if not req.bedrooms:
            return 0.5

        if prop.bedrooms is None:
            return 0.3

        diff = abs(req.bedrooms - prop.bedrooms)
        if diff == 0:
            return 1.0
        if diff == 1:
            return 0.6
        return 0.0

    def _area_sqm_score(self, req: ClientRequest, prop: Property) -> float:
        """Score area size match (sqm)."""
        if not req.min_area_sqm and not req.max_area_sqm:
            return 0.5  # No preference = neutral

        if prop.area_sqm is None:
            return 0.4  # Property has no area data — mild penalty

        min_sqm = req.min_area_sqm or 0
        max_sqm = req.max_area_sqm or float("inf")

        if min_sqm <= prop.area_sqm <= max_sqm:
            return 1.0  # Perfect fit

        if prop.area_sqm < min_sqm:
            ratio = prop.area_sqm / min_sqm if min_sqm > 0 else 0
            return 0.3 + (0.5 * ratio)

        # Over max
        over_ratio = (prop.area_sqm - max_sqm) / max_sqm if max_sqm > 0 else 0
        if over_ratio <= 0.15:
            return 0.6
        if over_ratio <= 0.30:
            return 0.4
        return 0.1

    def _payment_score(self, req: ClientRequest, prop: Property) -> float:
        """Score payment plan preference."""
        if not req.prefer_payment_plan:
            return 0.5  # No preference = neutral

        # Property has a payment plan (down payment or installments)
        has_plan = (prop.down_payment is not None and prop.down_payment > 0) or \
                   (prop.payment_plan_details is not None and prop.payment_plan_details.strip() != "")

        if has_plan:
            return 1.0  # Perfect — client wants plan, property has one

        return 0.2  # Client wants plan but property doesn't offer one

    def _amenities_score(self, req: ClientRequest, prop: Property) -> float:
        """Score based on notes/keywords match."""
        notes = (req.notes or "").lower()
        if not notes:
            return 0.5

        score = 0.5
        text = f"{(prop.title or '')} {(prop.description or '')} {(prop.tags or '')}".lower()

        # Check for keywords
        keywords = ["مسبح", "جيم", "حديقة", "security", "gated", "compound", "فيو"]
        for kw in keywords:
            if kw in notes and kw in text:
                score += 0.1

        return min(score, 1.0)


# ---------------------------------------------------------------------------
# Match-Making Engine — محرك المطابقة الرئيسي
# ---------------------------------------------------------------------------
class MatchMakingEngine:
    """Main engine for matching client requests to properties."""

    def __init__(self, db: Session):
        self.db = db
        self.scorer = MatchScorer()

    def match_request(self, request_id: int) -> dict:
        """
        Find and score all matching properties for a client request.

        Returns:
            dict with matches list, best match, and statistics.
        """
        request = self.db.query(ClientRequest).filter(
            ClientRequest.id == request_id
        ).first()

        if not request:
            return {"status": "error", "message": "Request not found"}

        # Get available properties
        query = self.db.query(Property).filter(Property.status == "available")

        # Apply hard filters
        if request.area:
            area = normalize_area(request.area)
            # Soft filter — include partial matches via ILIKE
            query = query.filter(
                Property.area.ilike(f"%{area}%") |
                Property.district.ilike(f"%{area}%")
            )
        if request.property_type:
            query = query.filter(Property.property_type == request.property_type)

        properties = query.all()

        # Score all matches
        matches = []
        for prop in properties:
            score = self.scorer.score(request, prop)
            if score >= 0.3:  # Minimum threshold
                matches.append({
                    "property_id": prop.id,
                    "property_title": prop.title,
                    "property_area": prop.area,
                    "property_price": prop.price,
                    "property_type": prop.property_type,
                    "score": score,
                    "match_details": {
                        "area": self.scorer._area_score(request, prop),
                        "price": self.scorer._price_score(request, prop),
                        "type": self.scorer._type_score(request, prop),
                        "bedrooms": self.scorer._bedroom_score(request, prop),
                        "area_sqm": self.scorer._area_sqm_score(request, prop),
                        "payment": self.scorer._payment_score(request, prop),
                    },
                })

        # Sort by score
        matches.sort(key=lambda m: m["score"], reverse=True)

        # Update request with best match
        best_match = None
        if matches:
            best = matches[0]
            best_match = {
                "property_id": best["property_id"],
                "property_title": best["property_title"],
                "score": best["score"],
            }

            # Update request status
            request.status = "matched"
            request.matched_property_id = best["property_id"]
            request.matched_at = datetime.now(timezone.utc)
            request.match_score = best["score"]
            self.db.commit()

        return {
            "status": "matched" if matches else "no_matches",
            "request_id": request_id,
            "total_matches": len(matches),
            "matches": matches[:20],  # Top 20
            "best_match": best_match,
        }

    def match_all_pending(self) -> dict:
        """Match all pending client requests."""
        pending = self.db.query(ClientRequest).filter(
            ClientRequest.status == "pending"
        ).all()

        results = []
        for req in pending:
            result = self.match_request(req.id)
            results.append(result)

        matched_count = sum(1 for r in results if r["status"] == "matched")
        return {
            "total_pending": len(pending),
            "matched": matched_count,
            "unmatched": len(pending) - matched_count,
            "results": results,
        }

    def find_properties_for_client(self, client_name: str) -> dict:
        """Find all matching properties for a specific client by name."""
        requests = self.db.query(ClientRequest).filter(
            ClientRequest.client_name == client_name
        ).all()

        if not requests:
            return {"status": "error", "message": "No requests found for client"}

        all_matches = []
        for req in requests:
            result = self.match_request(req.id)
            if result["matches"]:
                all_matches.extend(result["matches"])

        # Deduplicate and sort
        seen = set()
        unique_matches = []
        for m in sorted(all_matches, key=lambda x: x["score"], reverse=True):
            if m["property_id"] not in seen:
                seen.add(m["property_id"])
                unique_matches.append(m)

        return {
            "client_name": client_name,
            "total_requests": len(requests),
            "total_matches": len(unique_matches),
            "matches": unique_matches[:20],
        }

    def get_match_statistics(self) -> dict:
        """Get overall match statistics."""
        total_requests = self.db.query(ClientRequest).count()
        matched = self.db.query(ClientRequest).filter(
            ClientRequest.status == "matched"
        ).count()
        pending = self.db.query(ClientRequest).filter(
            ClientRequest.status == "pending"
        ).count()

        return {
            "total_requests": total_requests,
            "matched": matched,
            "pending": pending,
            "match_rate": round(matched / total_requests * 100, 1) if total_requests > 0 else 0,
        }
