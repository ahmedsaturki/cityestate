"""
Arabic Intent Parser — محلل النوايا بالعامية المصرية
====================================================
AI-powered parser that extracts property intent from Arabic messages.
Uses LLM (via CrewAI/OpenRouter) when available, falls back to rule-based.

Extracts:
- Property type (شقة, فيلا, دوبلكس, etc.)
- Area (زايد, أكتوبر, التجمع, etc.)
- Budget (3 مليون, 500 الف, etc.)
- Bedrooms (3 غرف, 3BR, etc.)
- Intent (شراء, استفسار, بيع, etc.)
"""

import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger("intent_parser")


@dataclass
class ParsedIntent:
    """Structured intent from a user message."""
    intent: str = "inquiry"          # inquiry, buy, rent, sell, complaint, greeting
    property_type: str | None = None    # apartment, villa, duplex, twin, town, commercial
    area: str | None = None             # Sheikh Zayed, October, etc.
    budget_min: float | None = None
    budget_max: float | None = None
    bedrooms: int | None = None
    keywords: list = field(default_factory=list)
    confidence: float = 0.0
    raw_message: str = ""

    def to_dict(self) -> dict:
        """Serialize the parsed intent to a plain dictionary."""
        return {
            "intent": self.intent,
            "property_type": self.property_type,
            "area": self.area,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "bedrooms": self.bedrooms,
            "keywords": self.keywords,
            "confidence": self.confidence,
        }

    @property
    def has_property_intent(self) -> bool:
        """Return True if the message expresses property buy or inquiry intent."""
        return self.intent in ("buy", "inquiry") and (
            self.property_type or self.area or self.budget_max
        )


class IntentParser:
    """AI-powered Arabic intent parser.

    Tries LLM first for accurate understanding of Egyptian dialect.
    Falls back to rule-based parsing if LLM is unavailable.
    """

    def __init__(self):
        self._llm = None
        self._llm_checked = False

    def _get_llm(self):
        """Lazy-load LLM instance."""
        if not self._llm_checked:
            self._llm_checked = True
            try:
                from src.ai_crew.llm_config import get_llm
                self._llm = get_llm(temperature=0.0)
            except Exception:
                self._llm = None
        return self._llm

    def parse(self, message: str) -> ParsedIntent:
        """Parse a message and extract property intent.

        Tries LLM first, falls back to rule-based.
        """
        llm = self._get_llm()
        if llm:
            try:
                return self._llm_parse(message, llm)
            except Exception as e:
                logger.warning("LLM parse failed, using fallback: %s", e)

        return self._rule_parse(message)

    # ------------------------------------------------------------------
    # LLM-powered parsing
    # ------------------------------------------------------------------
    def _llm_parse(self, message: str, llm) -> ParsedIntent:
        """Use LLM to understand the message intent."""
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompt = """أنت محلل نوايا عقاري مصري محترف.
 مهمتك تحلل رسائل العملاء وتستخرج معلومات العقار المطلوب.

أرجع JSON بالشكل التالي بالضبط (بدون أي نص إضافي):
{
    "intent": "buy" | "rent" | "sell" | "inquiry" | "greeting" | "complaint",
    "property_type": "apartment" | "villa" | "duplex" | "twin_house" | "townhouse" | "studio" | "commercial" | "office" | null,
    "area": "Sheikh Zayed" | "6th October" | "New Cairo" | "New Capital" | "Maadi" | "Heliopolis" | null,
    "budget_min": null | number,
    "budget_max": null | number,
    "bedrooms": null | number,
    "confidence": 0.0-1.0
}

قواعد:
- إذا الرسالة فيها طلب شراء عقار → intent="buy"
- إذا الرسالة استفسار عام → intent="inquiry"
- إذا ترحيب → intent="greeting"
- إذا شكوى → intent="complaint"
- استخرج الميزانية بالجنيه المصري (مثلاً 3 مليون = 3000000)
- إذا الرسالة مش واضحة، حط confidence منخفض"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"حلل هذه الرسالة: {message}"),
        ]

        response = llm.invoke(messages)
        text = str(response.content).strip()

        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            return ParsedIntent(
                intent=data.get("intent", "inquiry"),
                property_type=data.get("property_type"),
                area=data.get("area"),
                budget_min=data.get("budget_min"),
                budget_max=data.get("budget_max"),
                bedrooms=data.get("bedrooms"),
                confidence=float(data.get("confidence", 0.5)),
                raw_message=message,
            )

        raise ValueError("No JSON in LLM response")

    # ------------------------------------------------------------------
    # Rule-based parsing (fallback)
    # ------------------------------------------------------------------
    def _rule_parse(self, message: str) -> ParsedIntent:
        """Rule-based fallback parser."""
        intent = ParsedIntent(raw_message=message)
        text = self._normalize(message)

        intent.intent = self._detect_intent(text)
        intent.property_type = self._extract_property_type(text)
        intent.area = self._extract_area(text)
        intent.budget_min, intent.budget_max = self._extract_budget(text)
        intent.bedrooms = self._extract_bedrooms(text)
        intent.keywords = self._extract_keywords(text)
        intent.confidence = self._calc_confidence(intent)

        return intent

    def _normalize(self, text: str) -> str:
        """Normalize Arabic text."""
        text = re.sub(r"[\u0617-\u061A\u064B-\u0652]", "", text)
        text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        text = text.replace("ة", "ه")
        text = text.replace("ى", "ي")
        text = re.sub(r"\s+", " ", text).strip()
        return text.lower()

    def _detect_intent(self, text: str) -> str:
        """Detect the primary intent from the message."""
        keywords = {
            "buy": ["عايز", "عاوز", "محتاج", "بدور", "ابحث", "هشترى", "هشتري", "اشتري"],
            "rent": ["ايجار", "إيجار", "مستأجر", "لايجار"],
            "sell": ["بيع", "ببيع", "أبيع"],
            "greeting": ["سلام", "مرحبا", "اهلا", "صباح", "مساء"],
            "complaint": ["شكوى", "مشكلة", "متضايق", "زعلان"],
        }
        for intent_name, words in keywords.items():
            for w in words:
                if w in text:
                    return intent_name
        return "inquiry"

    def _extract_property_type(self, text: str) -> str | None:
        types = {
            "شقة": "apartment", "شقه": "apartment", "شقق": "apartment",
            "فيلا": "villa", "دوبلكس": "duplex", "دبلوكس": "duplex",
            "توين هاوس": "twin_house", "تاون هاوس": "townhouse",
            "استوديو": "studio", "محل": "commercial", "مكتب": "office",
            "بنتهاوس": "penthouse", "روف": "roof",
        }
        for ar, en in types.items():
            if ar in text:
                return en
        return None

    def _extract_area(self, text: str) -> str | None:
        areas = {
            "الشيخ زايد": "Sheikh Zayed", "شيخ زايد": "Sheikh Zayed", "زايد": "Sheikh Zayed",
            "اكتوبر": "6th October", "6 اكتوبر": "6th October",
            "التجمع": "New Cairo", "التجمع الخامس": "New Cairo",
            "العاصمه": "New Capital", "العاصمة": "New Capital",
            "المعادي": "Maadi", "مصر الجديدة": "Heliopolis",
            "مدينة نصر": "Nasr City", "الزمالك": "Zamalek",
            "المهندسين": "Mohandessin", "وسط البلد": "Downtown",
        }
        sorted_areas = sorted(areas.keys(), key=len, reverse=True)
        for ar in sorted_areas:
            if ar in text:
                return areas[ar]
        return None

    def _extract_budget(self, text: str) -> tuple[float | None, float | None]:

        # "بين X و Y"
        m = re.search(r"بين\s*(\d+[\.,]?\d*)\s*(و|الى)\s*(\d+[\.,]?\d*)\s*(مليون|الف|k|m)?", text)
        if m:
            u = m.group(4) or "الف"
            mult = {"الف": 1000, "مليون": 1000000, "k": 1000, "m": 1000000}.get(u, 1000)
            return float(m.group(1).replace(",", ".")) * mult, float(m.group(3).replace(",", ".")) * mult

        # "حد اقصى X"
        m = re.search(r"حد\s*ا?قص[يى]\s*(\d+[\.,]?\d*)\s*(مليون|الف|k|m)?", text)
        if m:
            u = m.group(2) or "الف"
            mult = {"الف": 1000, "مليون": 1000000, "k": 1000, "m": 1000000}.get(u, 1000)
            return None, float(m.group(1).replace(",", ".")) * mult

        # "X مليون" or "X الف"
        m = re.search(r"(\d+[\.,]?\d*)\s*(مليون|الف|ك|m|k)", text)
        if m:
            u = m.group(2)
            mult = {"الف": 1000, "مليون": 1000000, "ك": 1000, "k": 1000, "m": 1000000}.get(u, 1000)
            return None, float(m.group(1).replace(",", ".")) * mult

        # Large number
        m = re.search(r"(\d{4,})", text)
        if m:
            v = float(m.group(1))
            if v >= 1000:
                return None, v

        return None, None

    def _extract_bedrooms(self, text: str) -> int | None:
        m = re.search(r"(\d)\s*(?:غرف|غرفه|br|bed)", text)
        return int(m.group(1)) if m else None

    def _extract_keywords(self, text: str) -> list[str]:
        terms = [
            "تشطيب", "سوبر لوكس", "دوبلكس", "روف", "موقف",
            "جراج", "امن", "نادي", "حمام سباحه", "بلكونه",
            "تري فيو", "نيل",
        ]
        return [t for t in terms if t.lower() in text]

    def _calc_confidence(self, intent: ParsedIntent) -> float:
        score = 0.0
        if intent.property_type:
            score += 0.3
        if intent.area:
            score += 0.3
        if intent.budget_max:
            score += 0.25
        if intent.bedrooms:
            score += 0.15
        return min(score, 1.0)
