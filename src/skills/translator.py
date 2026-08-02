"""
Translator Skill — المترجم
=============================
Multi-language translation for real estate communications.
Supports Arabic, English, and basic translation capabilities.
"""

import json
import logging

logger = logging.getLogger("skills.translator")


class TranslatorSkill:
    """Multi-language translation skill."""

    async def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en") -> dict:
        """Translate text using Google Translate (free API)."""
        try:
            import httpx

            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": source_lang,
                "tl": target_lang,
                "dt": "t",
                "q": text[:5000],
            }

            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=10)
                data = resp.json()

                translated = "".join(part[0] for part in data[0] if part[0])
                detected_lang = data[2] if len(data) > 2 else source_lang

                return {
                    "status": "success",
                    "original": text,
                    "translated": translated,
                    "source_lang": detected_lang,
                    "target_lang": target_lang,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def translate_batch(self, texts: list[str], target_lang: str = "en") -> dict:
        """Translate multiple texts."""
        results = []
        for text in texts:
            result = await self.translate(text, target_lang=target_lang)
            results.append(result)

        successful = [r for r in results if r["status"] == "success"]
        return {
            "status": "completed",
            "total": len(texts),
            "translated": len(successful),
            "results": results,
        }

    async def detect_language(self, text: str) -> dict:
        """Detect the language of text."""
        try:
            import httpx

            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": "en",
                "dt": "t",
                "q": text[:1000],
            }

            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=10)
                data = resp.json()
                detected = data[2] if len(data) > 2 else "unknown"

                lang_names = {
                    "ar": "Arabic", "en": "English", "fr": "French",
                    "de": "German", "es": "Spanish", "it": "Italian",
                    "tr": "Turkish", "ru": "Russian", "zh": "Chinese",
                }

                return {
                    "status": "success",
                    "language": detected,
                    "language_name": lang_names.get(detected, detected),
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def localize_property(self, property_data: dict, target_lang: str = "ar") -> dict:
        """Localize property listing for a target market."""
        fields_to_translate = ["title", "description", "location", "features"]

        localized = dict(property_data)
        for field in fields_to_translate:
            if field in localized and isinstance(localized[field], str):
                result = await self.translate(localized[field], target_lang=target_lang)
                if result["status"] == "success":
                    localized[f"{field}_translated"] = result["translated"]

        # Translate features list
        if "features" in localized and isinstance(localized["features"], list):
            translated_features = []
            for feat in localized["features"]:
                result = await self.translate(feat, target_lang=target_lang)
                translated_features.append(result.get("translated", feat) if result["status"] == "success" else feat)
            localized["features_translated"] = translated_features

        return {
            "status": "localized",
            "target_lang": target_lang,
            "property": localized,
        }

    async def translate_whatsapp_message(self, message: str, target_lang: str = "en") -> dict:
        """Translate a WhatsApp message for international clients."""
        result = await self.translate(message, target_lang=target_lang)
        if result["status"] == "success":
            return {
                "status": "success",
                "original": message,
                "translated": result["translated"],
                "detected_lang": result.get("source_lang"),
                "target_lang": target_lang,
            }
        return result

    def get_common_phrases(self, lang: str = "ar") -> dict:
        """Get common real estate phrases in a language."""
        phrases = {
            "ar": {
                "greeting": "مرحباً، كيف حالك؟",
                "property_inquiry": "أ interested في الشقة المعروضة",
                "price_question": "ما هو سعر العقار؟",
                "viewing_request": "هل يمكنني جدولة موعد للزيارة؟",
                "negotiation": "هل يوجد مجال للتفاوض على السعر؟",
                "closing": "أريد إتمام الصفقة",
                "thank_you": "شكراً لك",
            },
            "en": {
                "greeting": "Hello, how are you?",
                "property_inquiry": "I'm interested in the listed property",
                "price_question": "What is the price of the property?",
                "viewing_request": "Can I schedule a viewing?",
                "negotiation": "Is there room for price negotiation?",
                "closing": "I want to proceed with the deal",
                "thank_you": "Thank you",
            },
        }
        return {"language": lang, "phrases": phrases.get(lang, phrases["en"])}


def get_translator_tools():
    """Return CrewAI-compatible tools for translation."""
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class TranslateInput(BaseModel):
        text: str = Field(description="Text to translate")
        target_lang: str = Field(default="en", description="Target language code (en, ar, fr, etc.)")
        source_lang: str = Field(default="auto", description="Source language code or auto")

    class TranslateTool(BaseTool):
        name: str = "translate_text"
        description: str = "Translate text between languages. Supports Arabic, English, French, and more."
        args_schema: type = TranslateInput

        def _run(self, text: str, target_lang: str = "en", source_lang: str = "auto") -> str:
            import asyncio
            skill = TranslatorSkill()
            result = asyncio.run(skill.translate(text, source_lang, target_lang))
            return json.dumps(result, ensure_ascii=False)

    class DetectLanguageInput(BaseModel):
        text: str = Field(description="Text to detect language of")

    class DetectLanguageTool(BaseTool):
        name: str = "detect_language"
        description: str = "Detect the language of a text."
        args_schema: type = DetectLanguageInput

        def _run(self, text: str) -> str:
            import asyncio
            skill = TranslatorSkill()
            result = asyncio.run(skill.detect_language(text))
            return json.dumps(result, ensure_ascii=False)

    class LocalizePropertyInput(BaseModel):
        title: str = Field(description="Property title")
        description: str = Field(default="", description="Property description")
        target_lang: str = Field(default="ar", description="Target language")

    class LocalizePropertyTool(BaseTool):
        name: str = "localize_property_listing"
        description: str = "Translate a property listing to a target language for international clients."
        args_schema: type = LocalizePropertyInput

        def _run(self, title: str, description: str = "", target_lang: str = "ar") -> str:
            import asyncio
            skill = TranslatorSkill()
            result = asyncio.run(skill.localize_property({"title": title, "description": description}, target_lang))
            return json.dumps(result, ensure_ascii=False)

    return [TranslateTool(), DetectLanguageTool(), LocalizePropertyTool()]
