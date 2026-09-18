"""
Data Extractor — محرك استخراج البيانات
======================================
Extracts property data from various sources: WhatsApp messages, Facebook posts,
web pages, CSV files, and JSON APIs.

El Sadat City premium real estate focus — NO social housing.
"""

import json
import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger("data.extractor")


# ---------------------------------------------------------------------------
# Phone Number Patterns (Egypt)
# ---------------------------------------------------------------------------
PHONE_PATTERNS = [
    r"(\+20\s*\d{10})",
    r"(20\d{10})",
    r"(01\d{9})",
    r"(01[0-9]\d{8})",
]


# ---------------------------------------------------------------------------
# DataExtractor
# ---------------------------------------------------------------------------
class DataExtractor:
    """
    Extracts structured property data from unstructured sources.

    Supports:
    - WhatsApp messages (Arabic/English)
    - Facebook group posts
    - Web page HTML/markdown
    - CSV/JSON files
    """

    def __init__(self):
        self._extraction_count = 0

    # ------------------------------------------------------------------
    # WhatsApp Message Extraction
    # ------------------------------------------------------------------
    def extract_from_whatsapp(self, message: str, sender: str | None = None) -> dict:
        """
        Extract property data from a WhatsApp message.

        Args:
            message: Raw WhatsApp message text.
            sender: Sender phone number or name.

        Returns:
            dict with extracted fields: property_type, area, budget,
            bedrooms, contact_info, intent, raw_message.
        """
        text = message.strip()
        result = {
            "source": "whatsapp",
            "sender": sender,
            "raw_message": text,
            "property_type": None,
            "area": None,
            "budget": None,
            "bedrooms": None,
            "contact_phone": self._extract_phone(text),
            "intent": self._detect_intent(text),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

        # Property type
        result["property_type"] = self._extract_property_type(text)

        # Area
        result["area"] = self._extract_area(text)

        # Budget
        result["budget"] = self._extract_budget(text)

        # Bedrooms
        result["bedrooms"] = self._extract_bedrooms(text)

        self._extraction_count += 1
        logger.info("Extracted from WhatsApp: type=%s area=%s budget=%s",
                     result["property_type"], result["area"], result["budget"])
        return result

    # ------------------------------------------------------------------
    # Facebook Post Extraction
    # ------------------------------------------------------------------
    def extract_from_facebook(self, post_text: str, author: str | None = None,
                               post_url: str | None = None) -> dict:
        """
        Extract property data from a Facebook group post.

        Args:
            post_text: Raw Facebook post text.
            author: Post author name.
            post_url: URL of the Facebook post.

        Returns:
            dict with extracted fields.
        """
        text = post_text.strip()
        result = {
            "source": "facebook",
            "author": author,
            "post_url": post_url,
            "raw_message": text,
            "property_type": None,
            "area": None,
            "budget": None,
            "bedrooms": None,
            "contact_phone": self._extract_phone(text),
            "intent": self._detect_intent(text),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

        result["property_type"] = self._extract_property_type(text)
        result["area"] = self._extract_area(text)
        result["budget"] = self._extract_budget(text)
        result["bedrooms"] = self._extract_bedrooms(text)

        self._extraction_count += 1
        logger.info("Extracted from Facebook: type=%s area=%s budget=%s",
                     result["property_type"], result["area"], result["budget"])
        return result

    # ------------------------------------------------------------------
    # Web Page Extraction
    # ------------------------------------------------------------------
    def extract_from_webpage(self, html: str, url: str | None = None) -> dict:
        """
        Extract property data from a web page (HTML or markdown).

        Args:
            html: HTML or markdown content.
            url: Source URL.

        Returns:
            dict with extracted fields.
        """
        # Strip HTML tags for basic extraction
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()

        result = {
            "source": "web",
            "source_url": url,
            "raw_message": text[:2000],  # Truncate long pages
            "property_type": None,
            "area": None,
            "budget": None,
            "bedrooms": None,
            "contact_phone": self._extract_phone(text),
            "intent": self._detect_intent(text),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

        result["property_type"] = self._extract_property_type(text)
        result["area"] = self._extract_area(text)
        result["budget"] = self._extract_budget(text)
        result["bedrooms"] = self._extract_bedrooms(text)

        self._extraction_count += 1
        return result

    # ------------------------------------------------------------------
    # JSON/CSV Extraction
    # ------------------------------------------------------------------
    def extract_from_json(self, data: dict) -> dict:
        """Extract property data from a JSON object."""
        result = {
            "source": "json",
            "raw_message": json.dumps(data, ensure_ascii=False)[:2000],
            "property_type": data.get("property_type") or data.get("type"),
            "area": data.get("area") or data.get("location"),
            "budget": data.get("budget") or data.get("price"),
            "bedrooms": data.get("bedrooms") or data.get("rooms"),
            "contact_phone": data.get("phone") or data.get("contact"),
            "contact_name": data.get("name") or data.get("contact_name"),
            "intent": data.get("intent", "unknown"),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._extraction_count += 1
        return result

    def extract_from_csv_row(self, row: dict) -> dict:
        """Extract property data from a CSV row (dict)."""
        return self.extract_from_json(row)

    # ------------------------------------------------------------------
    # Internal Extraction Helpers
    # ------------------------------------------------------------------
    def _extract_phone(self, text: str) -> str | None:
        """Extract Egyptian phone number from text."""
        for pattern in PHONE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                phone = match.group(1).replace(" ", "")
                if not phone.startswith("+"):
                    phone = "+20" + phone.lstrip("0")
                return phone
        return None

    def _extract_property_type(self, text: str) -> str | None:
        """Extract property type from text."""
        type_keywords = {
            "شقة فاخرة": ["شقة فاخرة", "شقة واسعة", "شقة دوبلكس", "بنتهاوس", "شقة"],
            "فيلا": ["فيلا", "فيل独立", "فيلا دوبلكس", "تاون هاوس", "توين هاوس"],
            "أرض استثمارية": ["أرض", "أرض استثمارية", "أرض تجارية"],
            "محل تجاري": ["محل", "محل تجاري", "محل في مول"],
            "مكتب": ["مكتب", "مكتب تجاري", "استوديو", "مكتب إداري"],
            "مستودع": ["مستودع", "مخازن", "مستودع صناعي"],
            "مول تجاري": ["مول", "مركز تجاري", "كומרشال"],
        }
        text_lower = text.lower()
        for ptype, keywords in type_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    return ptype
        return None

    def _extract_area(self, text: str) -> str | None:
        """Extract area from text (El Sadat City + Greater Cairo + Alexandria)."""
        areas = {
            # Greater Cairo — English
            "sheikh zayed": ["sheikh zayed", "el sheikh zayed", "sheikh zayd", "الشيخ زايد", "زايد"],
            "new cairo": ["new cairo", "cairo new", "القاهرة الجديدة", "التجمع"],
            "6th october": ["october", "6th october", "6 october", "6 اكتوبر", "اكتوبر"],
            "maadi": ["maadi", "المعادي", "ma'adi"],
            "heliopolis": ["heliopolis", "مصر الجديدة", "مصر الجديده"],
            "nasr city": ["nasr city", "مدينة نصر"],
            "mohandessin": ["mohandessin", "mohandesin", "المهندسين"],
            "dokki": ["dokki", "doqqi", "الدقى", "الدقى"],
            "zamalek": ["zamalek", "الزمالك"],
            "downtown": ["downtown", "وسط البلد", "وسط البلد"],
            "fifth settlement": ["5th settlement", "fifth settlement", "التجمع الخامس", "التجمع 5"],
            "tagamoa": ["tagamoa", "التجمعة", "التجمع الاول", "التجمع الأول"],
            "new administrative capital": ["new capital", "العاصمة الإدارية", "العاصمة الادارية", "العاصمة"],
            "el rehab": ["el rehab", "rehab", "الرحاب", "rehab city"],
            "el shorouk": ["el shorouk", "shorouk", "الشروق", "الشروكة"],
            "mountain view": ["mountain view", "ماونتن فيو", "mountainview"],
            "palm hills": ["palm hills", "palm hill", "بالم هيلز", "بالم هيل"],
            "beverly hills": ["beverly hills", "beverly", "بيفرلي هيلز"],
            "madinaty": ["madinaty", "mdr", "مدينتي", "مدينة"],
            "ain shams": ["ain shams", "شمس", "عين شمس"],
            "shubra": ["shubra", "شبرا"],
            "hadaeq el qobba": ["hadaeq el qobba", "حدائق القبة"],
            "badr city": ["badr city", "badr", "بدر", "مدينة بدر"],
            "obour city": ["obour", "obour city", "العبور", "مدينة العبور"],
            "10th of ramadan": ["10th of ramadan", "10th ramadan", "العاشر من رمضان"],
            "helwan": ["helwan", "حلوان"],
            "ain sokhna": ["ain sokhna", "عين سخنة"],
            "el gouna": ["el gouna", "الجونة", "gouna"],
            "north coast": ["sahel", "north coast", "الساحل", "الساحل الشمالي"],
            "sidi abd el rahman": ["sidi abd el rahman", "سيدي عبد الرحمن"],
            "giza": ["giza", "جيزه", "جيزة"],
            "faisal": ["faisal", "فيصل", "شارع فيصل"],
            "haram": ["haram", "هرم", "شارع الهرم"],
            # Greater Cairo — Arabic
            "alexandria": ["alexandria", "alex", "الاسكندرية", "اسكندرية", "اسكندريه"],
            "tanta": ["tanta", "طنطا"],
            # El Sadat City
            "المنطقة 7 الشريط المميز": ["منطقة 7", "المنطقة 7", "شريط 7", "شريط المميز"],
            "المنطقة 9 الشريط المميز": ["منطقة 9", "المنطقة 9", "شريط 9"],
            "المنطقة 15 الشريط المميز": ["منطقة 15", "المنطقة 15", "شريط 15"],
            "الفردوس": ["الفردوس", "فردوس"],
            "الكوثر": ["الكوثر", "كوثر"],
            "النخيل": ["النخيل", "نخيل"],
            "الروضة": ["الروضة", "روضة"],
            "البراميتر": ["البراميتر", "براميتر", "barameter"],
            "النرجس": ["النرجس", "نرجس"],
            "الريحان": ["الريحان", "ريحان"],
            "Polaris Parks": ["بولاريس", "polaris", "polaris parks"],
            "المنطقة الصناعية الأولى": ["الصناعية", "المنطقة الصناعية"],
        }
        for area, keywords in areas.items():
            for kw in keywords:
                if kw in text:
                    return area
        return None

    def _extract_budget(self, text: str) -> float | None:
        """Extract budget amount from text."""
        patterns = [
            (r"(\d+(?:\.\d+)?)\s*مليون", lambda m: float(m.group(1)) * 1_000_000),
            (r"(\d+(?:\.\d+)?)\s*(الف|ألف)", lambda m: float(m.group(1)) * 1000),
            (r"(\d[\d,.]+)\s*(جنيه|ج\.م|EGP)", lambda m: int(m.group(1).replace(",", ""))),
            (r"(\d+(?:\.\d+)?)\s*k", lambda m: float(m.group(1)) * 1000),
            (r"(\d+(?:\.\d+)?)\s*M", lambda m: float(m.group(1)) * 1_000_000),
        ]
        for pattern, extractor in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                budget = extractor(match)
                if budget >= 1_500_000:
                    return budget
        return None

    def _extract_bedrooms(self, text: str) -> int | None:
        """Extract bedroom count from text."""
        bedroom_keywords = {
            0: ["استوديو", "استودييه", "studio"],
            1: ["غرفة واحدة", "1 غرفة", "1 نوم", "غرفة", "bedroom", "1br", "1 bedroom"],
            2: ["غرفتين", "2 غرفة", "2 نوم", "غرفين", "2br", "2 bedroom"],
            3: ["تلات غرف", "3 غرفة", "3 نوم", "3 غرف", "3br", "3 bedroom"],
            4: ["أربع غرف", "4 غرفة", "4 نوم", "4 غرف", "4br", "4 bedroom"],
            5: ["خمس غرف", "5 غرفة", "5 نوم", "5 غرف", "5br", "5 bedroom"],
        }
        for count, keywords in bedroom_keywords.items():
            for kw in keywords:
                if kw in text:
                    return count
        return None

    def _detect_intent(self, text: str) -> str:
        """Detect buyer/seller/broker intent."""
        buyer_signals = ["مطلوب", "عايز", "أبحث", "أدور", "محتاج", "ابعتلي", "عندكم"]
        seller_signals = ["للبيع", "بياع", "أبيع", "ببيع"]
        broker_signals = ["سمسار", "عقارات", "عندي عقارات"]

        text_lower = text.lower()
        for signal in broker_signals:
            if signal in text_lower:
                return "broker"
        for signal in buyer_signals:
            if signal in text_lower:
                return "buyer"
        for signal in seller_signals:
            if signal in text_lower:
                return "seller"
        return "unknown"

    @property
    def stats(self) -> dict:
        """Return extraction statistics."""
        return {"total_extractions": self._extraction_count}
