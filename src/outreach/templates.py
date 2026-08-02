"""
Message Templates
=================
Static fallback template pools for 5 segments × 3 channels.
Used when LLM generation is unavailable or fails.

Architecture Decision:
- 3-5 variants per segment/channel to avoid repetition
- Variable injection via str.format_map() for safe substitution
- Templates written in English for diaspora/investor, Arabic-ready for buyer/developer
"""

from typing import Any

# =============================================================================
# Template Registry
# =============================================================================
# Each segment has email (subject+body), sms (text), whatsapp (text) variants.
# Variables: {lead_title}, {area}, {budget}, {interest}, {url}, {source}

TEMPLATES: dict[str, dict[str, list[dict[str, str]]]] = {
    # =========================================================================
    # DIASPORA — Aspirational, ROI-focused, "invest in your roots"
    # =========================================================================
    "diaspora": {
        "email": [
            {
                "subject": "Premium Egyptian Real Estate — Exclusive for Diaspora Investors",
                "body": (
                    "Dear Investor,\n\n"
                    "Discover premium real estate opportunities in Egypt's fastest-growing "
                    "markets. {lead_title}\n\n"
                    "Areas like {area} are seeing 12-18% annual appreciation, with flexible "
                    "payment plans designed for overseas buyers.\n\n"
                    "Whether you're looking for a vacation home or a high-yield investment, "
                    "our portfolio offers options starting from {budget}.\n\n"
                    "View details: {url}\n\n"
                    "Best regards,\nCityEstate Team"
                ),
            },
            {
                "subject": "Invest in Your Roots — Egyptian Property Market 2026",
                "body": (
                    "Dear Community Member,\n\n"
                    "The Egyptian real estate market is booming, and now is the perfect time "
                    "to invest. {lead_title}\n\n"
                    "Key highlights:\n"
                    "- Rental yields of 8-15% in prime locations\n"
                    "- Flexible payment plans up to 7 years\n"
                    "- Full legal support for overseas transactions\n\n"
                    "Explore: {url}\n\n"
                    "Warm regards,\nCityEstate Team"
                ),
            },
            {
                "subject": "Your Dream Home in Egypt Awaits — North Coast & New Capital",
                "body": (
                    "Hello,\n\n"
                    "Imagine owning a property in Egypt's most prestigious developments. "
                    "{lead_title}\n\n"
                    "From North Coast beachfront apartments to New Administrative Capital "
                    "smart cities — we help diaspora investors navigate the market with "
                    "confidence.\n\n"
                    "Starting from {budget} with 10% down payment.\n\n"
                    "Learn more: {url}\n\n"
                    "Sincerely,\nCityEstate Team"
                ),
            },
        ],
        "sms": [
            "North Coast homes from {budget}. 12-18% annual ROI. Flexible plans for diaspora investors. Details: {url}",
            "Invest in Egypt from abroad. {area} properties with 8-15% yields. Learn more: {url}",
            "Your dream home in {area} awaits. Premium locations, flexible payments. {url}",
        ],
        "whatsapp": [
            "Hi! Interested in Egyptian real estate investment? {lead_title} We offer diaspora-friendly payment plans and full legal support. Details: {url}",
            "Hello! {area} properties available with 8-15% annual ROI. Perfect for overseas investors. Want more info? {url}",
            "Assalamu alaikum! Investing in Egypt has never been easier. {lead_title} Starting from {budget}. Reply for details!",
        ],
    },

    # =========================================================================
    # INVESTOR — Data-driven, yield-focused, "smart capital allocation"
    # =========================================================================
    "investor": {
        "email": [
            {
                "subject": "High-Yield Real Estate Investment Opportunity — {area}",
                "body": (
                    "Dear Investor,\n\n"
                    "We've identified a high-yield investment opportunity aligned with your "
                    "portfolio strategy. {lead_title}\n\n"
                    "Investment Highlights:\n"
                    "- Location: {area}\n"
                    "- Expected ROI: 12-18% annually\n"
                    "- Entry price: {budget}\n"
                    "- Payment: 20% down, installments over 5 years\n\n"
                    "Full analysis: {url}\n\n"
                    "Regards,\nCityEstate Investment Team"
                ),
            },
            {
                "subject": "Market Analysis: Egyptian Real Estate — Q3 2026 Report",
                "body": (
                    "Dear Valued Investor,\n\n"
                    "Our Q3 2026 market analysis reveals strong fundamentals in Egyptian "
                    "real estate. {lead_title}\n\n"
                    "Key metrics:\n"
                    "- Price growth: 15% YoY in prime areas\n"
                    "- Rental yield: 8-12% in Cairo, 12-18% in North Coast\n"
                    "- Occupancy rates: 85%+ in new developments\n\n"
                    "Download report: {url}\n\n"
                    "Best,\nCityEstate Analytics"
                ),
            },
        ],
        "sms": [
            "{area} investment opportunity. 12-18% ROI. Entry from {budget}. Analysis: {url}",
            "High-yield Egyptian real estate. {lead_title} Smart capital allocation. Details: {url}",
            "Q3 2026 market data: 15% price growth in {area}. Investment brief: {url}",
        ],
        "whatsapp": [
            "Investment alert: {area} properties with 12-18% annual ROI. Entry from {budget}. Want the full analysis? {url}",
            "Smart capital allocation opportunity. {lead_title} Payment plans available. Reply for details!",
            "Market update: Egyptian real estate showing strong Q3 2026 fundamentals. {url}",
        ],
    },

    # =========================================================================
    # DEVELOPER — Partnership, portfolio-focused, "strategic collaboration"
    # =========================================================================
    "developer": {
        "email": [
            {
                "subject": "Strategic Partnership Opportunity — {lead_title}",
                "body": (
                    "Dear Development Team,\n\n"
                    "We're reaching out regarding a potential collaboration in the Egyptian "
                    "real estate market. {lead_title}\n\n"
                    "Our platform connects developers with qualified buyers across:\n"
                    "- Diaspora investors seeking premium properties\n"
                    "- First-time buyers with pre-approved budgets\n"
                    "- Institutional investors for bulk acquisitions\n\n"
                    "Partnership details: {url}\n\n"
                    "Looking forward to discussing this opportunity.\n\n"
                    "Best regards,\nCityEstate Partnerships"
                ),
            },
            {
                "subject": "Expand Your Buyer Pipeline — CityEstate Developer Program",
                "body": (
                    "Dear Partner,\n\n"
                    "CityEstate offers developers access to a curated pool of qualified "
                    "buyers. {lead_title}\n\n"
                    "Benefits:\n"
                    "- Lead qualification and scoring\n"
                    "- Multi-channel outreach (email, SMS, WhatsApp)\n"
                    "- Campaign analytics and reporting\n"
                    "- No upfront costs — pay per qualified lead\n\n"
                    "Join our program: {url}\n\n"
                    "Regards,\nCityEstate Team"
                ),
            },
        ],
        "sms": [
            "Partnership opportunity: Connect with qualified buyers for {area} projects. Details: {url}",
            "Expand your buyer pipeline. CityEstate developer program. {lead_title} Info: {url}",
        ],
        "whatsapp": [
            "Hi! We help developers connect with qualified buyers. {lead_title} Interested in a partnership? {url}",
            "Strategic collaboration opportunity for {area} projects. Pre-qualified leads available. Reply for info!",
        ],
    },

    # =========================================================================
    # BUYER — Value, payment-plan-focused, "affordable homeownership"
    # =========================================================================
    "buyer": {
        "email": [
            {
                "subject": "Your Perfect Home in {area} — Flexible Payment Plans Available",
                "body": (
                    "Dear Future Homeowner,\n\n"
                    "Finding your dream home doesn't have to be overwhelming. "
                    "{lead_title}\n\n"
                    "We've curated properties in {area} that match your criteria:\n"
                    "- Budget: Starting from {budget}\n"
                    "- Interest: {interest}\n"
                    "- Payment: 10% down, up to 7 years installments\n\n"
                    "View properties: {url}\n\n"
                    "Our advisors are ready to help you find the perfect match.\n\n"
                    "Warm regards,\nCityEstate Home Finder"
                ),
            },
            {
                "subject": "Affordable Homes in {area} — Government-Backed Programs",
                "body": (
                    "Dear Home Seeker,\n\n"
                    "Great news! New affordable housing programs are available in {area}. "
                    "{lead_title}\n\n"
                    "Highlights:\n"
                    "- Prices starting from {budget}\n"
                    "- Government-subsidized interest rates\n"
                    "- Up to 30-year payment plans\n"
                    "- Fully finished units available\n\n"
                    "Apply now: {url}\n\n"
                    "Don't miss out — limited units available.\n\n"
                    "Best,\nCityEstate Team"
                ),
            },
            {
                "subject": "First-Time Buyer? We've Got You Covered",
                "body": (
                    "Hello,\n\n"
                    "Buying your first home is a big step — we're here to make it easy. "
                    "{lead_title}\n\n"
                    "What we offer:\n"
                    "- Free property consultation\n"
                    "- Mortgage pre-approval assistance\n"
                    "- Legal document review\n"
                    "- Post-purchase support\n\n"
                    "Start your journey: {url}\n\n"
                    "Congratulations on taking the first step!\n\n"
                    "Cheers,\nCityEstate Team"
                ),
            },
        ],
        "sms": [
            "Dream home in {area} from {budget}. 10% down, 7-year plans. View: {url}",
            "{lead_title} — Affordable {interest} in {area}. Government programs available. {url}",
            "First-time buyer? {area} homes with flexible payments. Free consultation. {url}",
        ],
        "whatsapp": [
            "Hi! Looking for a home in {area}? We have properties from {budget} with flexible payment plans. Interested? {url}",
            "Dream home alert! {lead_title} Starting from {budget}. Reply to learn more!",
            "Assalamu alaikum! Affordable {interest} available in {area}. Government-backed programs. Details: {url}",
        ],
    },

    # =========================================================================
    # UNKNOWN — Generic professional inquiry
    # =========================================================================
    "unknown": {
        "email": [
            {
                "subject": "Egyptian Real Estate Market Update — {lead_title}",
                "body": (
                    "Dear Contact,\n\n"
                    "We came across your interest in the Egyptian real estate market and "
                    "wanted to share some relevant updates. {lead_title}\n\n"
                    "Current market highlights:\n"
                    "- Cairo: 30,000-200,000 EGP/sqm\n"
                    "- North Coast: 50,000-350,000 EGP/sqm\n"
                    "- New Administrative Capital: 40,000-180,000 EGP/sqm\n\n"
                    "For more information: {url}\n\n"
                    "Feel free to reach out if you have any questions.\n\n"
                    "Best regards,\nCityEstate Team"
                ),
            },
            {
                "subject": "Market Intelligence — Egyptian Real Estate 2026",
                "body": (
                    "Hello,\n\n"
                    "The Egyptian real estate market continues to show strong growth "
                    "in 2026. {lead_title}\n\n"
                    "We'd be happy to provide you with:\n"
                    "- Detailed market reports\n"
                    "- Price comparisons by area\n"
                    "- Investment opportunity analysis\n"
                    "- Payment plan options\n\n"
                    "Learn more: {url}\n\n"
                    " regards,\nCityEstate Intelligence"
                ),
            },
        ],
        "sms": [
            "Egyptian real estate update: {lead_title}. Market data and opportunities: {url}",
            "Stay informed on Egyptian property market. Latest trends: {url}",
        ],
        "whatsapp": [
            "Hello! We noticed your interest in Egyptian real estate. {lead_title} Want market insights? {url}",
            "Hi! Egyptian property market updates available. {lead_title} Reply for details!",
        ],
    },
}


# =============================================================================
# Segment Detection
# =============================================================================
SEGMENT_MAP: dict[str, str] = {
    "diaspora": "diaspora",
    "investor": "investor",
    "developer": "developer",
    "buyer": "buyer",
    "seller": "unknown",
    "agency": "developer",
    "unknown": "unknown",
}


def detect_segment(lead_type: str) -> str:
    """Map lead_type to template segment key."""
    normalized = (lead_type or "unknown").lower().strip()
    return SEGMENT_MAP.get(normalized, "unknown")


# =============================================================================
# Template Retrieval
# =============================================================================
# Round-robin index per (segment, channel) to avoid consecutive duplicates
_variant_indices: dict[str, int] = {}


def get_template(segment: str, channel: str) -> dict[str, str] | str:
    """Select next template variant using round-robin rotation.

    Args:
        segment: Template segment (diaspora, investor, developer, buyer, unknown).
        channel: Channel key (email, sms, whatsapp).

    Returns:
        Dict with 'subject' and 'body' keys for email, or plain string for sms/whatsapp.
    """
    pool = TEMPLATES.get(segment, TEMPLATES["unknown"])
    variants = pool.get(channel, pool.get("email", [{"subject": "", "body": ""}]))

    key = f"{segment}:{channel}"
    idx = _variant_indices.get(key, 0)
    template = variants[idx % len(variants)]
    _variant_indices[key] = idx + 1

    return template


# =============================================================================
# Variable Injection
# =============================================================================
def inject_variables(template: dict[str, str] | str, lead: dict[str, Any]) -> dict[str, str]:
    """Replace template placeholders with lead data.

    Handles both dict templates (email) and string templates (sms/whatsapp).
    Safe: unknown variables are left as-is (no KeyError).
    """
    variables = {
        "lead_title": lead.get("title", "Real Estate Opportunity"),
        "area": lead.get("area", "Prime Location"),
        "budget": lead.get("budget", "Competitive Price"),
        "interest": lead.get("interest", "Property"),
        "url": lead.get("url", "#"),
        "source": lead.get("source", "Market Research"),
    }

    # SMS/WhatsApp templates are strings, not dicts
    if isinstance(template, str):
        try:
            return {"subject": "", "body": template.format_map(variables)}
        except (KeyError, ValueError):
            return {"subject": "", "body": template}

    result: dict[str, str] = {}
    for key, value in template.items():
        try:
            result[key] = value.format_map(variables)
        except (KeyError, ValueError):
            result[key] = value
    return result


def render_message(segment: str, channel: str, lead: dict[str, Any]) -> dict[str, str]:
    """Full template render: select + inject variables.

    Returns:
        Dict with 'subject' (email only) and 'body' keys.
    """
    template = get_template(segment, channel)
    return inject_variables(template, lead)
