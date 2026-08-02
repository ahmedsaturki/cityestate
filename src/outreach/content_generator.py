"""
Content Generator — صانع المحتوى التلقائي
=========================================
AI-powered content generation for properties across 3 channels:
1. Facebook Post (long, sales-driven, with emojis)
2. Instagram Post (short, hashtag-rich, visual focus)
3. WhatsApp Status (ultra-short, punchy, urgent)

Uses LLM (via CrewAI/OpenRouter) when available,
falls back to template-based generation.
"""

import logging
import random

logger = logging.getLogger("content_generator")


class ContentGenerator:
    """AI-powered content generator for real estate marketing."""

    def __init__(self):
        self._llm = None
        self._llm_checked = False

    def _get_llm(self):
        """Lazy-load LLM instance."""
        if not self._llm_checked:
            self._llm_checked = True
            try:
                from src.ai_crew.llm_config import get_llm
                self._llm = get_llm(temperature=0.7)
            except Exception:
                self._llm = None
        return self._llm

    def generate(self, property_data: dict, channel: str = "all") -> dict:
        """Generate content for a property.

        Args:
            property_data: Dict with property fields
            channel: "facebook", "instagram", "whatsapp", or "all"

        Returns:
            Dict with generated content per channel.
        """
        llm = self._get_llm()
        if llm:
            try:
                return self._llm_generate(property_data, channel, llm)
            except Exception as e:
                logger.warning("LLM content generation failed, using templates: %s", e)

        return self._template_generate(property_data, channel)

    # ------------------------------------------------------------------
    # LLM-powered generation
    # ------------------------------------------------------------------
    def _llm_generate(self, prop: dict, channel: str, llm) -> dict:
        """Use LLM to generate marketing content."""
        from langchain_core.messages import HumanMessage, SystemMessage

        # Build property summary
        title = prop.get("title", "عقار مميز")
        area = prop.get("area", "غير محدد")
        price = prop.get("price", 0)
        prop_type = prop.get("property_type", "")
        bedrooms = prop.get("bedrooms", "")
        area_sqm = prop.get("area_sqm", "")
        developer = prop.get("developer", "")
        description = prop.get("description", "")

        if price >= 1_000_000:
            price_str = f"{price / 1_000_000:.1f} مليون جنيه"
        elif price >= 1_000:
            price_str = f"{price / 1_000:.0f} ألف جنيه"
        else:
            price_str = f"{price:,.0f} جنيه"

        details = f"النوع: {prop_type}, المنطقة: {area}, السعر: {price_str}"
        if bedrooms:
            details += f", غرف: {bedrooms}"
        if area_sqm:
            details += f", المساحة: {area_sqm} م²"
        if developer:
            details += f", المطور: {developer}"

        system_prompt = """أنت كاتب محتوى تسويقي عقاري مصري محترف.
مهمتك كتابة محتوى جذاب وأصلي للعقارات بالعامية المصرية.

قواعد عامة:
- لا تستخدم فصحى — استخدم عامية مصرية طبيعية
- استخدم إيموجي بذكاء (مش مبالغ)
- كل بوست يجب أن يحتوي CTA واضح
- لا تكرر القوالب — كن إبداعياً في كل مرة"""

        channels_text = {
            "facebook": "فيسبوك (200-350 كلمة): بوست طويل تفصيلي يبدأ بـ hook قوي، يذكر التفاصيل والمميزات والسعر، وينتهي بـ CTA.",
            "instagram": "إنستجرام (150-250 كلمة): بوست بصري يركز على المشاعر، يحتوي 10-15 hashtags شائعة في العقارات المصرية.",
            "whatsapp": "واتساب (50-100 كلمة): رسالة قصيرة ومباشرة — السعر والميزة الرئيسية + CTA. بدون hashtags.",
        }

        if channel == "all":
            channels_list = "\n".join(f"- {v}" for v in channels_text.values())
        else:
            channels_list = channels_text.get(channel, channels_text["facebook"])

        user_prompt = f"""اكتب محتوى تسويقي للعقار التالي:

**البيانات:** {details}
**الوصف:** {description[:300] if description else "عقار مميز في منطقة مميزة"}

**القنوات المطلوبة:**
{channels_list}

**المطلوب:** اكتب البوستات جاهزة للنشر. كل بوست منفصل بعنوان واضح."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = llm.invoke(messages)
        result_text = str(response.content).strip()

        # Parse sections
        results = {"raw": result_text}
        if channel in ("all", "facebook"):
            results["facebook"] = self._extract_section(result_text, ["فيسبوك", "Facebook", "1."])
        if channel in ("all", "instagram"):
            results["instagram"] = self._extract_section(result_text, ["إنستجرام", "Instagram", "2."])
        if channel in ("all", "whatsapp"):
            results["whatsapp"] = self._extract_section(result_text, ["واتساب", "WhatsApp", "3."])

        return {
            "property_id": prop.get("id"),
            "property_title": title,
            "content": results,
            "method": "llm",
        }

    def _extract_section(self, text: str, markers: list[str]) -> str:
        """Extract a section from the response by markers."""
        for marker in markers:
            if marker in text:
                parts = text.split(marker, 1)
                if len(parts) > 1:
                    # Take content until next section marker or end
                    section = parts[1]
                    for end_marker in ["**فيسبوك", "**إنستجرام", "**واتساب", "1. **", "2. **", "3. **"]:
                        if end_marker in section:
                            section = section.split(end_marker)[0]
                    return section.strip()[:1000]
        return text[:1000]

    # ------------------------------------------------------------------
    # Template-based generation (fallback)
    # ------------------------------------------------------------------
    def _template_generate(self, prop: dict, channel: str) -> dict:
        """Template-based fallback content generation."""
        ctx = self._build_context(prop)

        results = {}
        if channel in ("all", "facebook"):
            results["facebook"] = self._gen_facebook(ctx)
        if channel in ("all", "instagram"):
            results["instagram"] = self._gen_instagram(ctx)
        if channel in ("all", "whatsapp"):
            results["whatsapp"] = self._gen_whatsapp(ctx)

        return {
            "property_id": prop.get("id"),
            "property_title": prop.get("title", ""),
            "content": results,
            "method": "template",
        }

    def _build_context(self, p: dict) -> dict:
        """Build a rendering context from property data."""
        title = p.get("title", "عقار مميز")
        area = p.get("area", "غير محدد")
        price = p.get("price", 0)
        prop_type = p.get("property_type", "primary")
        bedrooms = p.get("bedrooms")
        area_sqm = p.get("area_sqm")
        developer = p.get("developer")
        description = p.get("description", "")
        down_payment = p.get("down_payment")
        monthly = p.get("monthly_installment")

        if price >= 1_000_000:
            price_display = f"{price / 1_000_000:.1f} مليون جنيه"
        elif price >= 1_000:
            price_display = f"{price / 1_000:.0f} ألف جنيه"
        else:
            price_display = f"{price:,.0f} جنيه"

        type_map = {
            "primary": "عقار أولي", "resale": "بيع ثانوي",
            "compound": "كمبوند", "villa": "فيلا", "apartment": "شقة",
        }
        property_type_ar = type_map.get(prop_type, prop_type or "عقار")

        details = []
        if bedrooms:
            details.append(f"🛏️ غرف: {bedrooms}")
        if area_sqm:
            details.append(f"📐 المساحة: {area_sqm} م²")
        if developer:
            details.append(f"🏢 المطور: {developer}")
        details_block = "\n".join(details)
        details_one_liner = " | ".join(d.replace("🛏️ ", "").replace("📐 ", "").replace("🏢 ", "") for d in details[:3])

        desc_line = description[:200] if description else f"عقار مميز في {area}"
        short_desc = description[:100] if description else f"عقار مميز في {area}"

        payment_line = ""
        payment_line_short = ""
        if down_payment and monthly:
            payment_line = f"💳 دفعة أولى {down_payment:,.0f} + أقساط {monthly:,.0f}/شهر"
            payment_line_short = f"💳 {down_payment:,.0f} + {monthly:,.0f}/شهر"

        cta = random.choice([
            "📞 تواصل معانا دلوقتي قبل ما الفرصة تفوتك!",
            "⏳ العقار ده مش ه يستنى — كلمانا دلوقتي!",
            "📩 راسلنا دلوقتي وهنرد عليك فوراً!",
        ])
        cta_short = random.choice(["📞 رد عالرسالة!", "📩 كلمانا دلوقتي!"])

        area_tag = area.replace(" ", "_")
        hashtags = f"#عقارات #{area_tag} #Egypt #Cairo #عقارات_للبيع"

        return {
            "title": title, "area": area, "price_display": price_display,
            "property_type_ar": property_type_ar, "description_line": desc_line,
            "short_description": short_desc, "details_block": details_block,
            "details_one_liner": details_one_liner, "payment_line": payment_line,
            "payment_line_short": payment_line_short, "cta": cta,
            "cta_short": cta_short, "hashtags": hashtags, "area_tag": area_tag,
            "emoji_location": "📍", "emoji_money": "💰", "emoji_building": "🏢",
            "emoji_heart": "🔥", "emoji_urgency": "⚡",
        }

    def _gen_facebook(self, ctx: dict) -> dict:
        text = (
            f"{ctx['emoji_location']} {ctx['title']} {ctx['emoji_heart']}\n\n"
            f"{ctx['description_line']}\n\n"
            f"{ctx['emoji_money']} السعر: {ctx['price_display']}\n"
            f"{ctx['emoji_building']} النوع: {ctx['property_type_ar']}\n"
            f"{ctx['emoji_location']} المنطقة: {ctx['area']}\n\n"
            f"{ctx['details_block']}\n\n"
            f"{ctx['payment_line']}\n\n"
            f"{ctx['emoji_urgency']} {ctx['cta']}\n\n"
            f"#عقارات #real_estate #{ctx['area_tag']} #Egypt"
        )
        return {"channel": "facebook", "text": text, "char_count": len(text)}

    def _gen_instagram(self, ctx: dict) -> dict:
        text = (
            f"{ctx['emoji_location']} {ctx['title']}\n\n"
            f"{ctx['short_description']}\n\n"
            f"💰 {ctx['price_display']}\n"
            f"📍 {ctx['area']}\n"
            f"{ctx['details_one_liner']}\n\n"
            f"DM for details! 📩\n\n"
            f"{ctx['hashtags']}"
        )
        return {"channel": "instagram", "text": text, "char_count": len(text)}

    def _gen_whatsapp(self, ctx: dict) -> dict:
        text = (
            f"🏢 {ctx['title']}\n"
            f"💰 {ctx['price_display']}\n"
            f"📍 {ctx['area']}\n"
            f"{ctx['details_one_liner']}\n"
            f"{ctx['payment_line_short']}\n"
            f"📞 رد عالرسالة"
        )
        return {"channel": "whatsapp", "text": text, "char_count": len(text)}
