"""
Social Radar — رادار الجروبات العقارية
========================================
Scans Facebook Groups for buyer-intent posts, filters out
sellers/brokers, and creates Leads + ClientRequests automatically.

Pipeline:
1. FacebookExpert.scrape_group_posts() → raw posts
2. IntentParser.parse() → extract intent from each post
3. Smart filter → keep buyer/inquiry, reject seller/broker
4. Create Lead + ClientRequest in DB
5. Return hot leads for dashboard display
"""

import logging
import re
from datetime import datetime

from src.outreach.intent_parser import IntentParser, ParsedIntent

logger = logging.getLogger("outreach.social_radar")


# ---------------------------------------------------------------------------
# Seller / Broker signal words (to EXCLUDE)
# ---------------------------------------------------------------------------
SELLER_SIGNALS = [
    # Arabic seller keywords
    "للبيع", "يُباع", "يبيع", "للبيع المباشر",
    "متاح للبيع", "السعر المطلوب", "السعر النهائي",
    " negotiated", "قابل للتفاوض",
    # Broker / developer marketing
    "سعر المطور", "كمباوند", "جاري بناء", "جاهز للسكن",
    "استلام فوري", "تسهيلات", "مقدم بسيط",
    "-unit", "unit available", "available now",
    "developer price", "special offer", "عقار مميز",
    "للايجار", "للإيجار", "مؤجر",
    # Ads / marketing
    "إعلان ممول", "Sponsored", "AD",
    "عرض خاص", "عرض لفترة محدودة",
]


def is_seller_post(text: str) -> bool:
    """Check if a post is from a seller/broker (not a buyer)."""
    text_lower = text.lower()
    for signal in SELLER_SIGNALS:
        if signal.lower() in text_lower:
            return True
    return False


def normalize_phone(text: str) -> str | None:
    """Extract and normalize Egyptian phone from text."""
    patterns = [
        r"\+20\s*1[0125]\d{8}",
        r"01[0125]\d{8}",
        r"201[0125]\d{8}",
    ]
    arabic_map = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            phone = match.group(0).translate(arabic_map)
            phone = re.sub(r"[^\d+]", "", phone)
            if phone.startswith("0"):
                phone = "+20" + phone[1:]
            elif not phone.startswith("+"):
                phone = "+20" + phone
            if len(phone) == 13:
                return phone

    # Try Arabic numerals
    arabic_match = re.search(r"[٠١٢٣٤٥٦٧٨٩]{11}", text)
    if arabic_match:
        phone = arabic_match.group(0).translate(arabic_map)
        phone = "+20" + phone[1:]
        if len(phone) == 13:
            return phone

    return None


class SocialRadar:
    """Facebook Groups radar for discovering buyer-intent leads.

    Scans posts, filters for buyer signals, creates CRM leads.
    """

    def __init__(self):
        self.parser = IntentParser()
        self._stats = {
            "posts_scanned": 0,
            "buyer_posts_found": 0,
            "leads_created": 0,
            "requests_created": 0,
            "seller_posts_filtered": 0,
            "greeting_posts_filtered": 0,
        }

    def scan_posts(
        self, posts: list[dict], db_session=None
    ) -> list[dict]:
        """Scan scraped posts for buyer intent.

        Args:
            posts: Raw posts from FacebookExpert.scrape_group_posts()
            db_session: SQLAlchemy session for DB operations

        Returns:
            List of matched leads with intent data
        """
        from src.database.ingester import Lead
        from src.database.models import ClientRequest

        matched = []

        for post in posts:
            text = post.get("text", "")
            if not text or len(text) < 30:
                continue

            self._stats["posts_scanned"] += 1

            # 1. Skip seller/broker posts
            if is_seller_post(text):
                self._stats["seller_posts_filtered"] += 1
                continue

            # 2. Parse intent
            intent: ParsedIntent = self.parser.parse(text)

            # 3. Skip greetings and complaints
            if intent.intent in ("greeting", "complaint"):
                self._stats["greeting_posts_filtered"] += 1
                continue

            # 4. Must have some property signal
            if not intent.has_property_intent:
                continue

            self._stats["buyer_posts_found"] += 1

            # 5. Extract phone
            phone = normalize_phone(text)

            # 6. Build lead record
            lead_record = {
                "text": text[:500],
                "author": post.get("author", ""),
                "post_url": post.get("post_url", ""),
                "group_url": post.get("group_url", ""),
                "phone": phone,
                "intent": intent.to_dict(),
                "source": "facebook_radar",
                "timestamp": post.get("timestamp", datetime.now().isoformat()),
            }

            # 7. Save to DB if session provided
            if db_session:
                try:
                    # Create Lead — use correct model fields
                    lead = Lead(
                        title=post.get("author", "") or f"FB-{(phone or 'none')[-4:]}",
                        url=post.get("post_url", ""),
                        phone=phone or "",
                        lead_type=intent.property_type or "Unknown",
                        area=intent.area or "",
                        source="facebook_radar",
                        status="new",
                    )
                    db_session.add(lead)
                    db_session.flush()

                    lead_record["lead_id"] = lead.id
                    self._stats["leads_created"] += 1

                    # Create ClientRequest if has property intent
                    if intent.has_property_intent:
                        request = ClientRequest(
                            client_name=post.get("author", "") or f"FB-{(phone or 'none')[-4:]}",
                            phone=phone or "",
                            property_type=intent.property_type or "apartment",
                            area=intent.area or "",
                            min_budget=intent.budget_min or 0,
                            max_budget=intent.budget_max or 0,
                            bedrooms=intent.bedrooms or 0,
                            notes=text[:500],
                            status="pending",
                        )
                        db_session.add(request)
                        db_session.flush()
                        lead_record["request_id"] = request.id
                        self._stats["requests_created"] += 1

                    db_session.commit()

                except Exception as e:
                    db_session.rollback()
                    logger.error("Failed to save radar lead: %s", e)
                    lead_record["db_error"] = str(e)

            matched.append(lead_record)
            logger.info(
                "Radar hit: %s | %s | %s | conf=%.2f",
                intent.property_type, intent.area,
                intent.intent, intent.confidence,
            )

        return matched

    def get_stats(self) -> dict:
        """Get radar statistics."""
        return self._stats.copy()

    def reset_stats(self):
        """Reset statistics counters."""
        for key in self._stats:
            self._stats[key] = 0
