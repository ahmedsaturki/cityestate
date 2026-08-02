"""
MessageWriterExpert - LLM-Powered Personalized Message Generation
=================================================================
Domain expert for writing personalized Arabic/English messages.

Secrets & Expertise:
    - LLM-first with template fallback
    - Egyptian Arabic dialect for consumers, formal for B2B
    - Personalization: name, project, area, price
    - Avoid spam triggers (no ALL CAPS, no excessive punctuation)
    - A/B testing: generate 2 variants per lead
    - Cultural sensitivity: appropriate greetings per segment
"""

import logging
import os
import re

logger = logging.getLogger("automation.experts.writer")


# LLM configuration
OPENROUTER_API_KEY = os.getenv("ROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("ROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("ROUTER_MODEL", "inclusionai/ling-3.0-flash:free")

# Cultural greeting patterns
GREETINGS = {
    "Developer": {
        "ar": "السلام عليكم {name}،",
        "en": "Dear {name},",
    },
    "Investor": {
        "ar": "مرحبًا {name}،",
        "en": "Hi {name},",
    },
    "Buyer": {
        "ar": "أهلاً {name}،",
        "en": "Hello {name},",
    },
    "Agency": {
        "ar": "السلام عليكم فريق {name}،",
        "en": "Dear {name} Team,",
    },
    "Unknown": {
        "ar": "مرحبًا {name}،",
        "en": "Hi {name},",
    },
}

# Professional closing patterns
CLOSINGS = {
    "Developer": {
        "ar": "مع تحياتنا،\nفريق CityEstate للتسويق العقاري الرقمي",
        "en": "Best regards,\nCityEstate Digital Real Estate Marketing",
    },
    "Investor": {
        "ar": "نتطلع لتعاونا،\nفريق CityEstate",
        "en": "Looking forward to working together,\nCityEstate Team",
    },
    "Buyer": {
        "ar": "في انتظار ردكم،\nفريق CityEstate",
        "en": "Waiting for your reply,\nCityEstate Team",
    },
    "Agency": {
        "ar": "مع خالص التحيات،\nفريق CityEstate",
        "en": "Sincerely,\nCityEstate Team",
    },
    "Unknown": {
        "ar": "مع تحياتنا،\nفريق CityEstate",
        "en": "Best regards,\nCityEstate Team",
    },
}


class MessageWriterExpert:
    """LLM-powered message writer with cultural intelligence.

    This expert:
    - Generates personalized messages using LLM
    - Falls back to templates when LLM fails
    - Uses Egyptian Arabic for consumers, formal for B2B
    - Avoids spam triggers
    - Generates A/B test variants
    - Validates message quality before sending
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str = "",
    ) -> None:
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or OPENROUTER_MODEL
        self.base_url = base_url or OPENROUTER_BASE_URL

        # Stats
        self._llm_calls = 0
        self._llm_failures = 0
        self._template_fallbacks = 0

    def _extract_lead_info(self, lead: dict) -> dict:
        """Extract and normalize lead information."""
        title = lead.get("title", "")

        # Extract name (first 2 meaningful words)
        name_parts = []
        for word in title.split()[:5]:
            if len(word) > 2 and word.isalpha():
                name_parts.append(word)
                if len(name_parts) >= 2:
                    break
        name = " ".join(name_parts) if name_parts else "عميلنا العزيز"

        # Extract area
        area_match = re.search(
            r"(New Cairo|New Capital|October|Sahel|North Coast|Alexandria|Cairo|Giza|Sheikh Zayed)",
            title, re.IGNORECASE
        )
        area = area_match.group(1) if area_match else "مصر"

        # Extract project
        project_match = re.search(
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Developments?|Project|Tower|Compound)",
            title
        )
        project = project_match.group(1) if project_match else "مشروعكم"

        # Extract price
        price = lead.get("budget")
        price_str = f"{price:,.0f} جنيه" if price else "سعر تنافسي"

        return {
            "name": name,
            "area": area,
            "project": project,
            "price": price_str,
            "segment": lead.get("lead_type", "Unknown"),
        }

    def _generate_with_llm(self, lead_info: dict, channel: str, lang: str = "ar") -> dict | None:
        """Generate message using LLM."""
        if not self.api_key:
            return None

        segment = lead_info["segment"]
        greeting = GREETINGS.get(segment, GREETINGS["Unknown"])[lang]
        closing = CLOSINGS.get(segment, CLOSINGS["Unknown"])[lang]

        # Build prompt
        if lang == "ar":
            system_prompt = """أنت خبير تسويق عقاري في مصر. تكتب رسائل تسويقية احترافية بالعامية المصرية.
- تجنب الرسمية الزائدة
- استخدم عبارات مقنعة ومحسّنة
- لا تستخدم علامات تعجب كثيرة
- لا تكتب بحروف كبيرة بالكامل
- اذكر معلومات محددة عن العميل"""

            user_prompt = f"""اكتب رسالة تسويقية عقارية بالعربية المصرية:

العميل: {lead_info['name']}
الشريحة: {segment}
المشروع: {lead_info['project']}
المنطقة: {lead_info['area']}
السعر: {lead_info['price']}
القناة: {channel}

ابدأ بـ: {greeting}
اختتم بـ: {closing}

اكتب الرسالة فقط، بدون شرح."""
        else:
            system_prompt = """You are an expert real estate marketer in Egypt. Write professional marketing messages.
- Be concise and persuasive
- Avoid spam triggers (no ALL CAPS, no excessive punctuation)
- Include specific details about the lead
- Use appropriate tone for the segment"""

            user_prompt = f"""Write a real estate marketing message in English:

Lead: {lead_info['name']}
Segment: {segment}
Project: {lead_info['project']}
Area: {lead_info['area']}
Price: {lead_info['price']}
Channel: {channel}

Start with: {greeting}
End with: {closing}

Write only the message, no explanation."""

        try:
            import httpx
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.7,
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                message = data["choices"][0]["message"]["content"].strip()

                # Validate message quality
                if self._validate_message(message):
                    self._llm_calls += 1
                    return {
                        "subject": f"فرصة عقارية في {lead_info['area']}" if channel == "email" else "",
                        "body": message,
                        "source": "llm",
                    }

            self._llm_failures += 1
            return None

        except Exception as e:
            logger.debug("LLM generation failed: %s", e)
            self._llm_failures += 1
            return None

    def _validate_message(self, message: str) -> bool:
        """Validate message quality and spam triggers."""
        # Check length
        if len(message) < 20 or len(message) > 500:
            return False

        # Check for spam triggers
        spam_triggers = ["!!!", "؟؟؟", "限时", "立即", "ACT NOW", "URGENT", "FREE"]
        for trigger in spam_triggers:
            if trigger in message:
                return False

        # Check for ALL CAPS (more than 30% of message)
        words = message.split()
        caps_count = sum(1 for w in words if w.isupper() and len(w) > 2)
        return not caps_count / max(len(words), 1) > 0.3

    def _generate_template(self, lead_info: dict, channel: str, lang: str = "ar") -> dict:
        """Generate message from template (LLM fallback)."""
        segment = lead_info["segment"]
        greeting = GREETINGS.get(segment, GREETINGS["Unknown"])[lang]
        closing = CLOSINGS.get(segment, CLOSINGS["Unknown"])[lang]

        if lang == "ar":
            templates = {
                "Developer": f"""{greeting}

نود أن نقدم لكم خدماتنا في التسويق الرقمي العقاري. مشروعكم في {lead_info['area']} يستحق حضورًا رقميًا قويًا.

فريق CityEstate متخصص في تسويق المشاريع العقارية في مصر.

{closing}""",

                "Investor": f"""{greeting}

نقدم لكم فرصًا استثمارية واعدة في {lead_info['area']} بعوائد مجزية.

فريق CityEstate للتسويق العقاري الرقمي.

{closing}""",

                "Buyer": f"""{greeting}

وجدنا عقارات تناسب احتياجاتكم في {lead_info['area']} بأسعار تنافسية.

فريق CityEstate في خدمتكم.

{closing}""",

                "Unknown": f"""{greeting}

نحن CityEstate للتسويق العقاري الرقمي. نقدم خدمات تسويقية متكاملة في مصر.

{closing}""",
            }
        else:
            templates = {
                "Developer": f"""{greeting}

We offer digital real estate marketing services for your project in {lead_info['area']}.

CityEstate Digital Real Estate Marketing.

{closing}""",

                "Investor": f"""{greeting}

We have investment opportunities in {lead_info['area']} with attractive returns.

CityEstate Team.

{closing}""",

                "Buyer": f"""{greeting}

We found properties matching your needs in {lead_info['area']} at competitive prices.

CityEstate Team.

{closing}""",

                "Unknown": f"""{greeting}

We are CityEstate for digital real estate marketing in Egypt.

{closing}""",
            }

        body = templates.get(segment, templates["Unknown"])
        self._template_fallbacks += 1

        return {
            "subject": f"Real Estate Opportunity in {lead_info['area']}" if channel == "email" else "",
            "body": body,
            "source": "template",
        }

    def generate(self, lead: dict, channel: str = "whatsapp", lang: str = "ar") -> dict:
        """Generate a personalized message for a lead.

        Args:
            lead: Lead dict with title, lead_type, budget, etc.
            channel: "whatsapp", "email", or "sms"
            lang: "ar" for Arabic, "en" for English

        Returns:
            Dict with subject, body, and source
        """
        lead_info = self._extract_lead_info(lead)

        # Try LLM first
        if self.api_key:
            llm_result = self._generate_with_llm(lead_info, channel, lang)
            if llm_result:
                return llm_result

        # Fallback to template
        return self._generate_template(lead_info, channel, lang)

    def generate_variants(self, lead: dict, channel: str = "whatsapp", lang: str = "ar", count: int = 2) -> list[dict]:
        """Generate multiple message variants for A/B testing.

        Returns:
            List of message dicts
        """
        variants = []
        for i in range(count):
            variant = self.generate(lead, channel, lang)
            variant["variant_id"] = i + 1
            variants.append(variant)
        return variants

    def get_stats(self) -> dict:
        """Get writer statistics."""
        return {
            "llm_calls": self._llm_calls,
            "llm_failures": self._llm_failures,
            "template_fallbacks": self._template_fallbacks,
            "llm_success_rate": self._llm_calls / max(self._llm_calls + self._llm_failures, 1),
        }
