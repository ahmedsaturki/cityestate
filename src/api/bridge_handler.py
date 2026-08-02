"""
Bridge Handler — معالج الجسر (Premium Focus)
=============================================
Processes messages between the Chrome Extension and the AI Brain.
FOCUS: Premium properties, luxury compounds, villas, commercial hubs.
NO social housing or budget properties.

Flow:
1. Extension sends incoming WhatsApp/Facebook message
2. Bridge Handler runs intent parsing + lead scoring
3. Generates AI response via CrewAI
4. Returns response to Extension for human-like typing
"""

import asyncio
import logging
import re

logger = logging.getLogger("cityestate.bridge")


# ---------------------------------------------------------------------------
# Premium Property Types (NO social housing)
# ---------------------------------------------------------------------------
SADAT_PROPERTY_TYPES = {
    "شقة فاخرة": ["شقة فاخرة", "شقة واسعة", "شقة دوبلكس", "بنتهاوس", "شقة"],
    "فيلا": ["فيلا", "فيلا مستقلة", "فيلا دوبلكس", "تاون هاوس", "توين هاوس"],
    "أرض استثمارية": ["أرض", "أرض استثمارية", "أرض تجارية", "ارض"],
    "محل تجاري": ["محل", "محل تجاري", "محل في مول", "محل تجاري"],
    "مكتب": ["مكتب", "مكتب تجاري", "استوديو", "مكتب إداري"],
    "مستودع": ["مستودع", "مخازن", "unit صناعي", "مستودع صناعي"],
    "مول تجاري": ["مول", "مركز تجاري", "كומרشال", "مول تجاري"],
}


# ---------------------------------------------------------------------------
# El Sadat City Premium Areas
# ---------------------------------------------------------------------------
SADAT_PREMIUM_AREAS = {
    "المنطقة 7 الشريط المميز": {"type": "premium_residential", "avg_price": 25000},
    "المنطقة 9 الشريط المميز": {"type": "premium_residential", "avg_price": 22000},
    "المنطقة 15 الشريط المميز": {"type": "premium_residential", "avg_price": 20000},
    "الفردوس": {"type": "premium_residential", "avg_price": 18000},
    "الكوثر": {"type": "premium_residential", "avg_price": 19000},
    "النخيل": {"type": "premium_residential", "avg_price": 21000},
    "الروضة": {"type": "premium_residential", "avg_price": 20000},
    "البراميتر": {"type": "investment", "avg_price": 15000},
    "النرجس": {"type": "premium_residential", "avg_price": 17000},
    "الريحان": {"type": "premium_residential", "avg_price": 16000},
}


# ---------------------------------------------------------------------------
# Industrial/Commercial Zones
# ---------------------------------------------------------------------------
SADAT_COMMERCIAL_ZONES = {
    "المنطقة الصناعية الأولى": {"type": "industrial", "avg_price": 8000},
    "المنطقة الصناعية الثانية": {"type": "industrial", "avg_price": 9000},
    "المنطقة الصناعية الثالثة": {"type": "industrial", "avg_price": 10000},
    "المنطقة الصناعية الرابعة": {"type": "industrial", "avg_price": 11000},
    "المنطقة الصناعية الخامسة": {"type": "industrial", "avg_price": 12000},
    "المنطقة الصناعية السادسة": {"type": "industrial", "avg_price": 13000},
    "المنطقة الصناعية السابعة": {"type": "industrial", "avg_price": 14000},
    "المنطقة الصناعية Extension": {"type": "industrial", "avg_price": 15000},
    "Polaris Parks": {"type": "industrial_modern", "avg_price": 18000},
    "بولاريس": {"type": "industrial_modern", "avg_price": 18000},
    "بولاريس باركس": {"type": "industrial_modern", "avg_price": 18000},
}


# ---------------------------------------------------------------------------
# Premium Price Ranges (2026) - MIN 1.5M EGP
# ---------------------------------------------------------------------------
SADAT_PRICE_RANGES = {
    "شقة فاخرة": {"min": 1500000, "max": 5000000, "currency": "EGP"},
    "فيلا": {"min": 2500000, "max": 15000000, "currency": "EGP"},
    "أرض استثمارية": {"min": 1500000, "max": 20000000, "currency": "EGP"},
    "محل تجاري": {"min": 2500000, "max": 10000000, "currency": "EGP"},
    "مكتب": {"min": 1500000, "max": 8000000, "currency": "EGP"},
    "مستودع": {"min": 2000000, "max": 12000000, "currency": "EGP"},
    "مول تجاري": {"min": 5000000, "max": 50000000, "currency": "EGP"},
}


# ---------------------------------------------------------------------------
# Buyer Origin Cities (Wealthy Segments)
# ---------------------------------------------------------------------------
SALE_ORIGIN_AREAS = {
    "القاهرة": {"type": "major_city", "wealth_level": "high"},
    "الإسكندرية": {"type": "major_city", "wealth_level": "high"},
    "شبين الكوم": {"type": "governorate_capital", "wealth_level": "medium_high"},
    "المنوفية": {"type": "governorate", "wealth_level": "medium_high"},
    "البحيرة": {"type": "governorate", "wealth_level": "medium"},
    "الجيزة": {"type": "major_city", "wealth_level": "high"},
    "القليوبية": {"type": "governorate", "wealth_level": "medium"},
}


# ---------------------------------------------------------------------------
# Combined Area Keywords for Detection
# ---------------------------------------------------------------------------
ALL_AREAS = {}
ALL_AREAS.update(SADAT_PREMIUM_AREAS)
ALL_AREAS.update(SADAT_COMMERCIAL_ZONES)

# Alias mapping for Polaris
POLARIS_ALIASES = {
    "بولاريس": "Polaris Parks",
    "بولاريس باركس": "Polaris Parks",
    "polaris": "Polaris Parks",
    "polaris parks": "Polaris Parks",
}


# ---------------------------------------------------------------------------
# Bedroom Keywords
# ---------------------------------------------------------------------------
BEDROOM_KEYWORDS = {
    "استوديو": 0, "استودييه": 0,
    "غرفة واحدة": 1, "1 غرفة": 1, "1 نوم": 1, "غرف نوم 1": 1,
    "غرفتين": 2, "2 غرفة": 2, "2 نوم": 2, "غرف نوم 2": 2,
    "تلات غرف": 3, "3 غرفة": 3, "3 نوم": 3, "3 غرف نوم": 3, "غرف نوم 3": 3,
    "أربع غرف": 4, "4 غرفة": 4, "4 نوم": 4, "4 غرف نوم": 4, "غرف نوم 4": 4,
    "خمس غرف": 5, "5 غرفة": 5, "5 نوم": 5, "5 غرف": 5, "5 غرف نوم": 5, "غرف نوم 5": 5,
}


# ---------------------------------------------------------------------------
# Budget Patterns (MIN 1.5M EGP)
# ---------------------------------------------------------------------------
BUDGET_PATTERNS = [
    (r"(\d+)\s*(مليون)", lambda m: int(m.group(1)) * 1_000_000),
    (r"(\d+)\s*(الف|ألف)", lambda m: int(m.group(1)) * 1000),
    (r"(\d[\d,.]+)\s*(جنيه|ج.م|EGP|pound)", lambda m: int(m.group(1).replace(",", ""))),
    (r"(\d+)\s*(k)", lambda m: int(m.group(1)) * 1000),
    (r"(\d+)\s*(مليون|alf)", lambda m: int(m.group(1)) * (1_000_000 if "مليون" in m.group(2) else 1000)),
]


# ---------------------------------------------------------------------------
# Timeline Keywords (urgent/flexible only) - ORDER MATTERS!
# Check flexible patterns FIRST (before urgent)
# ---------------------------------------------------------------------------
TIMELINE_KEYWORDS = {
    # Flexible patterns FIRST (longer matches)
    "مش مستعجل": "flexible",
    "مفيش استعجال": "flexible",
    "بمبدأ": "flexible",
    "لو في فرصة": "flexible",
    "مرن": "flexible",
    "lexible": "flexible",
    # Urgent patterns
    "عاجل": "urgent",
    "سريع": "urgent",
    "النهاردة": "urgent",
    "اليوم": "urgent",
    "فوراً": "urgent",
    "مستعجل": "urgent",
    "فوري": "urgent",
    "على طول": "urgent",
}


# ---------------------------------------------------------------------------
# Broker/Buyer Signals
# ---------------------------------------------------------------------------
BROKER_SIGNALS = ["سمسار", "عقارات", "عندي عقارات", "مطور عقاري", "للإيجار", "أجار"]
BUYER_SIGNALS = ["مطلوب", "عايز", "أبحث", "أدور", "محتاج", "ابعتلي", "ممكن تبعت", "عندكم", "فيه شقة", "بتدور"]


# ---------------------------------------------------------------------------
# Intent Parser (Premium Focus)
# ---------------------------------------------------------------------------
def parse_intent(message: str, phone: str | None = None) -> dict:
    """Parse Egyptian Arabic message for real estate intent.
    
    PREMIUM FOCUS: Only luxury properties, no social housing.
    
    Returns:
        dict with property_type, area, budget, bedrooms, bathrooms,
        status, timeline, sale_origin, urgency_score
    """
    text = message.lower().strip()
    result = {
        "phone": phone,
        "property_type": None,
        "area": None,
        "budget": None,
        "bedrooms": None,
        "bathrooms": None,
        "status": None,
        "timeline": None,
        "sale_origin": None,
        "urgency_score": 0,
    }

    # 1. Property type detection (PREMIUM ONLY)
    for ptype, keywords in SADAT_PROPERTY_TYPES.items():
        for keyword in keywords:
            if keyword in text:
                result["property_type"] = ptype
                break
        if result["property_type"]:
            break

    # 2. Area detection (PREMIUM AREAS + COMMERCIAL ZONES)
    # Check Polaris aliases FIRST (before general areas)
    for alias, area in POLARIS_ALIASES.items():
        if alias in text:
            result["area"] = area
            break
    
    # Then check other areas
    if not result["area"]:
        for area_name in ALL_AREAS:
            if area_name in text:
                result["area"] = area_name
                break
    
    # Also check other aliases
    if not result["area"]:
        other_aliases = {
            "شريط المميز": "المنطقة 7 الشريط المميز",
            "شريط 7": "المنطقة 7 الشريط المميز",
            "شريط 9": "المنطقة 9 الشريط المميز",
            "شريط 15": "المنطقة 15 الشريط المميز",
            "المنطقة 7": "المنطقة 7 الشريط المميز",
            "المنطقة 9": "المنطقة 9 الشريط المميز",
            "المنطقة 15": "المنطقة 15 الشريط المميز",
            "الصناعية": "المنطقة الصناعية الأولى",
            "المنطقة الصناعية": "المنطقة الصناعية الأولى",
        }
        for alias, area in other_aliases.items():
            if alias in text:
                result["area"] = area
                break

    # 3. Budget detection (MIN 1.5M EGP)
    for pattern, extractor in BUDGET_PATTERNS:
        match = re.search(pattern, text)
        if match:
            budget = extractor(match)
            # AUTO-FILTER: Reject budgets under 1.5M EGP
            if budget < 1500000:
                return None
            result["budget"] = budget
            break

    # 4. Bedrooms detection
    for pattern, count in BEDROOM_KEYWORDS.items():
        if pattern in text:
            result["bedrooms"] = count
            break

    # 5. Timeline detection (urgent/flexible only)
    for keyword, timeline in TIMELINE_KEYWORDS.items():
        if keyword in text:
            result["timeline"] = timeline
            break

    # 6. Sale origin detection
    for origin in SALE_ORIGIN_AREAS:
        if origin in text:
            result["sale_origin"] = origin
            break

    # 7. Classify intent
    has_buyer_signal = any(s in text for s in BUYER_SIGNALS)
    has_broker_signal = any(s in text for s in BROKER_SIGNALS)

    if has_broker_signal:
        result["status"] = "broker"
    elif has_buyer_signal or result["budget"] and result["area"]:
        result["status"] = "buyer"

    # 8. Urgency score calculation
    urgency_score = 0
    if result["timeline"] == "urgent":
        urgency_score += 30
    if result["budget"] and result["budget"] >= 5000000:
        urgency_score += 25
    if result["property_type"] in ["فيلا", "محل تجاري", "مستودع", "مول تجاري"]:
        urgency_score += 20
    if result["sale_origin"] in ["القاهرة", "الإسكندرية"]:
        urgency_score += 15
    
    result["urgency_score"] = min(100, urgency_score)

    return result


# ---------------------------------------------------------------------------
# Lead Scoring (Premium Focus)
# ---------------------------------------------------------------------------
def score_lead(intent: dict, message: str, phone: str | None = None) -> dict:
    """Score a lead from 0-100 based on intent and message quality.
    
    PREMIUM FOCUS: Only high-value leads pass.
    Returns:
        dict with score, breakdown, tier, quality, reasons
    """
    if intent is None:
        return {"score": 0, "tier": "rejected", "quality": "rejected", "reasons": ["ميزانية منخفضة جداً"]}
    
    score = 0
    breakdown = {}
    reasons = []

    # Property type premium score
    premium_types = ["فيلا", "شقة فاخرة", "محل تجاري", "مستودع", "مول تجاري", "أرض استثمارية", "مكتب"]
    if intent.get("property_type") in premium_types:
        score += 20
        breakdown["property_type"] = 20
        reasons.append("نوع عقار فاخر")

    # Budget premium score
    budget = intent.get("budget") or 0
    if budget >= 8000000:
        score += 35
        breakdown["budget"] = 35
        reasons.append("ميزانية عالية جداً")
    elif budget >= 5000000:
        score += 25
        breakdown["budget"] = 25
        reasons.append("ميزانية ممتازة")
    elif budget >= 2500000:
        score += 15
        breakdown["budget"] = 15
        reasons.append("ميزانية جيدة جداً")
    elif budget >= 1500000:
        score += 8
        breakdown["budget"] = 8
        reasons.append("ميزانية جيدة")
    elif budget > 0:
        return {"score": 0, "tier": "rejected", "quality": "rejected", "reasons": ["ميزانية منخفضة جداً"]}
    # If budget is 0 or None, continue scoring (don't reject)

    # Timeline urgency score
    if intent.get("timeline") == "urgent":
        score += 10
        breakdown["urgency"] = 10
    elif intent.get("timeline") == "flexible":
        score += 5
        breakdown["urgency"] = 5

    # Area premium score
    if intent.get("area"):
        score += 10
        breakdown["area"] = 10
        reasons.append("منطقة محددة")

    # Sale origin score (major cities = wealthier)
    wealthy_origins = ["القاهرة", "الإسكندرية", "الجيزة"]
    if intent.get("sale_origin") in wealthy_origins:
        score += 10
        breakdown["origin"] = 10
        reasons.append("من مدينة رئيسية")

    # Serious language bonus
    serious_phrases = [
        "أسجل عربون", "عايز أشتري", "جاهز", "محتاج حد", "مفيش تأخير",
        "عايز شراء", "جاهز أدفع", "كاش", "بمقدم", "دفعات مريحة",
    ]
    if any(phrase in message for phrase in serious_phrases):
        score += 10
        breakdown["seriousness"] = 10
        reasons.append("جدية عالية")

    # Contact info provided
    phone_pattern = r"(01[0-9]{9}|\+20[0-9]{10})"
    if re.search(phone_pattern, message) or phone:
        score += 5
        breakdown["contact"] = 5
        reasons.append("معلومات الاتصال متوفرة")

    # Broker penalty
    if intent.get("status") == "broker":
        score -= 30
        breakdown["broker_penalty"] = -30
        reasons.append("سمسار - عميل غير مرغوب")

    # Clamp score
    score = max(0, min(100, score))

    # Determine quality tier
    if score >= 80:
        tier = "hot"
        quality = "platinum"
    elif score >= 60:
        tier = "warm"
        quality = "gold"
    elif score >= 40:
        tier = "warm"
        quality = "silver"
    else:
        tier = "cold"
        quality = "rejected"

    return {
        "score": score,
        "breakdown": breakdown,
        "tier": tier,
        "quality": quality,
        "reasons": reasons,
        "timeline": intent.get("timeline", "flexible"),
    }


# ---------------------------------------------------------------------------
# Property Matching (Premium Focus)
# ---------------------------------------------------------------------------
def match_properties(intent: dict, all_properties: list) -> list:
    """Match user intent against available properties.
    
    PREMIUM PROPERTIES ONLY - no social housing.
    Returns top 5 matching properties sorted by score.
    """
    if intent is None:
        return []
    
    # If no filters at all, don't match anything
    if not intent.get("area") and not intent.get("budget") and not intent.get("property_type"):
        return []
    
    matches = []

    for prop in all_properties:
        # Skip non-premium properties (price < 1.5M EGP)
        prop_price = prop.get("price", 0)
        if prop_price < 1500000:
            continue

        # Property type match
        if intent.get("property_type") and prop.get("property_type") != intent["property_type"]:
            continue

        # Area match
        if intent.get("area") and prop.get("area") != intent["area"]:
            continue

        # Budget match (within 20% tolerance)
        if intent.get("budget"):
            budget = intent["budget"]
            if prop_price < budget * 0.8 or prop_price > budget * 1.2:
                continue

        # Bedrooms match
        if intent.get("bedrooms") is not None and prop.get("bedrooms") is not None and abs(intent["bedrooms"] - prop["bedrooms"]) > 1:
            continue

        # Calculate match score
        score = calculate_match_score(intent, prop)
        matches.append({"property": prop, "score": score})

    # Sort by score (highest first)
    matches.sort(key=lambda x: x["score"], reverse=True)

    return matches[:5]  # Return top 5 matches


def calculate_match_score(intent: dict, prop: dict) -> int:
    """Calculate match score between intent and property."""
    score = 0
    
    # Property type match (exact)
    if intent.get("property_type") == prop.get("property_type"):
        score += 40
    
    # Area match (exact)
    if intent.get("area") == prop.get("area"):
        score += 30
    
    # Budget match (closer = better)
    if intent.get("budget") and prop.get("price"):
        budget = intent["budget"]
        price = prop["price"]
        ratio = price / budget
        if 0.9 <= ratio <= 1.1:
            score += 20
        elif 0.8 <= ratio <= 1.2:
            score += 10
    
    # Bedrooms match
    if (
        intent.get("bedrooms") is not None
        and prop.get("bedrooms") is not None
        and intent["bedrooms"] == prop["bedrooms"]
    ):
        score += 10
    
    return score


def find_matching_properties(intent: dict, db_session) -> list[dict]:
    """Find top 3 matching properties from database.
    
    Uses simple weighted scoring:
    - Area match: +40
    - Price range match: +30
    - Bedrooms match: +20
    - Available status: +10
    """
    try:
        from src.database.models import Property

        candidates = db_session.query(Property).filter(
            Property.status == "available"
        ).all()

        # Convert to list of dicts for match_properties
        props_list = []
        for prop in candidates:
            props_list.append({
                "id": prop.id,
                "title": prop.title,
                "area": prop.area,
                "price": prop.price,
                "bedrooms": prop.bedrooms,
                "area_sqm": prop.area_sqm,
                "developer": prop.developer,
                "project_name": prop.project_name,
                "property_type": getattr(prop, "property_type", None),
            })

        # Use match_properties for premium filtering
        matches = match_properties(intent, props_list)
        
        return [
            {
                "id": m["property"]["id"],
                "title": m["property"]["title"],
                "area": m["property"]["area"],
                "price": m["property"]["price"],
                "bedrooms": m["property"]["bedrooms"],
                "area_sqm": m["property"]["area_sqm"],
                "developer": m["property"]["developer"],
                "project_name": m["property"]["project_name"],
                "match_score": m["score"],
            }
            for m in matches[:3]
        ]

    except Exception as e:
        logger.error("Property matching failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# AI Response Generation
# ---------------------------------------------------------------------------
async def generate_response(
    message: str,
    sender_name: str,
    intent: dict,
    lead_score: dict,
    matched_properties: list[dict],
    db_session,
) -> str:
    """Generate an AI response using CrewAI.

    Args:
        message: Original WhatsApp message
        sender_name: Sender's name
        intent: Parsed intent dict
        lead_score: Lead scoring result
        matched_properties: Top matching properties
        db_session: Database session

    Returns:
        Response text in Egyptian Arabic
    """
    try:
        from src.error_handling import circuit_breakers

        llm_cb = circuit_breakers["llm"]

        if not llm_cb.can_execute():
            logger.warning("LLM circuit breaker is open — using fallback reply")
            return (
                f"مرحباً {sender_name}! 👋\n"
                "شكراً على رسالتك.\n"
                "هرد عليك في أقرب وقت. 🏠"
            )

        from src.ai_crew.crew import CityEstateCrew

        crew = CityEstateCrew()
        response = await asyncio.wait_for(
            asyncio.to_thread(
                crew.generate_whatsapp_reply,
                message=message,
                sender_name=sender_name,
                properties=matched_properties,
            ),
            timeout=15.0,
        )
        llm_cb.record_success()
        return response

    except Exception as e:
        logger.error("AI response generation failed: %s", e)
        try:
            from src.error_handling import circuit_breakers
            circuit_breakers["llm"].record_failure()
        except Exception as e:
            logger.debug("Circuit breaker record_failure failed: %s", e)
        return (
            f"مرحباً {sender_name}! 👋\n"
            "شكراً على رسالتك.\n"
            "هرد عليك في أقرب وقت. 🏠"
        )


# ---------------------------------------------------------------------------
# Main Bridge Processor
# ---------------------------------------------------------------------------
async def process_incoming_message(
    profile_id: str,
    chat_id: str,
    sender_name: str,
    message_text: str,
    platform: str,
    db_session,
) -> dict:
    """Process an incoming message from the Chrome Extension.

    This is the main entry point for the Bridge Handler.

    Args:
        profile_id: Chrome Profile ID
        chat_id: Chat identifier (WhatsApp phone or Facebook user ID)
        sender_name: Name of the message sender
        message_text: The actual message content
        platform: "whatsapp" or "facebook"
        db_session: Database session

    Returns:
        dict with response, lead_score, matched_properties, needs_handoff
    """
    logger.info(
        "Processing incoming: platform=%s, sender=%s, profile=%s",
        platform, sender_name, profile_id
    )

    # 1. Parse intent
    intent = parse_intent(message_text)

    # 2. Score the lead
    lead_score_result = score_lead(intent, message_text)

    # 3. Find matching properties (if we have intent data)
    matched = []
    if intent and (intent.get("area") or intent.get("budget")):
        matched = find_matching_properties(intent, db_session)

    # 4. Determine if human handoff needed
    needs_handoff = lead_score_result["tier"] == "hot"

    # 5. Generate AI response (ALWAYS — even for hot leads)
    # Hot leads get an immediate reply to keep them engaged,
    # PLUS a handoff notification so the human can take over.
    response = await generate_response(
        message=message_text,
        sender_name=sender_name,
        intent=intent,
        lead_score=lead_score_result,
        matched_properties=matched,
        db_session=db_session,
    )

    # 6. Log to database
    try:
        from src.database.models import MessageLog

        msg_log = MessageLog(
            channel=platform,
            message=message_text,
            message_type="inbound",
            status="processed",
            recipient_name=sender_name,
        )
        db_session.add(msg_log)
        db_session.commit()
    except Exception as e:
        logger.error("Failed to log message: %s", e)
        db_session.rollback()

    return {
        "response": response,
        "intent": intent,
        "lead_score": lead_score_result,
        "matched_properties": matched,
        "needs_handoff": needs_handoff,
        "sender_name": sender_name,
        "chat_id": chat_id,
        "platform": platform,
    }
