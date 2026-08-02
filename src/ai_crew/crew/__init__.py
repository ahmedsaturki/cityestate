"""
Crew Orchestrator — مدير فريق العمل الذكي
=========================================
Orchestrates CrewAI agents for various real estate automation tasks.
Provides simple functions that the scheduler and API can call.

Includes:
- Lead qualification (Facebook Radar)
- WhatsApp inbound reply generation
- Marketing content generation
- Personalized bulk outreach
- NEW: Data pipeline (collect → enrich → analyze → match)
- NEW: Market research
"""

import json
import logging

from crewai import Crew, Process, Task

from src.ai_crew.agents import (
    create_powerful_agent,
)
from src.ai_crew.llm_config import is_llm_available
from src.ai_crew.outreach_agents import (
    create_buyer_researcher,
    create_message_reviewer,
    create_personalized_writer,
)
from src.ai_crew.outreach_tasks import (
    create_buyer_research_task,
    create_message_review_task,
    create_personalized_writing_task,
)
from src.ai_crew.tasks import (
    create_content_generation_task,
    create_data_collection_task,
    create_data_enrichment_task,
    create_lead_analysis_task,
    create_lead_qualification_task,
    create_market_research_task,
    create_property_matching_task,
    create_whatsapp_reply_task,
)

logger = logging.getLogger("ai_crew.crew")


class CityEstateCrew:
    """Main crew orchestrator for CityEstate AI agents."""

    def __init__(self):
        self._llm_ready = is_llm_available()
        if not self._llm_ready:
            logger.warning("LLM not available — CrewAI agents will use fallback")

    # ------------------------------------------------------------------
    # Lead Qualification (Facebook Radar)
    # ------------------------------------------------------------------
    def qualify_leads(self, posts: list[dict]) -> list[dict]:
        """Qualify Facebook Group posts using AI.

        Args:
            posts: List of raw post dicts from FacebookExpert

        Returns:
            List of qualified lead dicts
        """
        if not posts:
            return []

        if not self._llm_ready:
            return self._fallback_qualify(posts)

        # Format posts for the agent
        posts_text = "\n\n".join(
            f"**منشور {i+1}:**\n"
            f"الكاتب: {p.get('author', 'غير معروف')}\n"
            f"النص: {p.get('text', '')[:500]}\n"
            f"الرابط: {p.get('post_url', '')}"
            for i, p in enumerate(posts)
        )

        try:
            task = create_lead_qualification_task(posts_text)
            crew = Crew(
                agents=[task.agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            )

            result = crew.kickoff()
            return self._parse_json_result(result)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error("Lead qualification failed: %s — using fallback", e)
            return self._fallback_qualify(posts)

    # ------------------------------------------------------------------
    # WhatsApp Reply Generation
    # ------------------------------------------------------------------
    def generate_whatsapp_reply(
        self,
        message: str,
        sender_name: str = "عميل",
        properties: list[dict] | None = None,
    ) -> str:
        """Generate a WhatsApp reply using AI.

        Args:
            message: Incoming WhatsApp message
            sender_name: Sender's name
            properties: List of matching property dicts

        Returns:
            Reply text in Egyptian Arabic
        """
        if not message:
            return ""

        if not self._llm_ready:
            return self._fallback_reply(message, sender_name)

        props_text = json.dumps(
            properties[:3] if properties else [],
            ensure_ascii=False,
            indent=2,
        )

        try:
            task = create_whatsapp_reply_task(message, sender_name, props_text)
            crew = Crew(
                agents=[task.agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            )

            result = crew.kickoff()
            return str(result).strip()

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error("WhatsApp reply generation failed: %s", e)
            return self._fallback_reply(message, sender_name)

    # ------------------------------------------------------------------
    # Marketing Content Generation
    # ------------------------------------------------------------------
    def generate_content(
        self, property_data: dict, channel: str = "all"
    ) -> dict:
        """Generate marketing content using AI.

        Args:
            property_data: Property details dict
            channel: Target channel (facebook, instagram, whatsapp, all)

        Returns:
            Dict with content per channel
        """
        if not property_data:
            return {}

        if not self._llm_ready:
            return self._fallback_content(property_data, channel)

        props_json = json.dumps(property_data, ensure_ascii=False, indent=2)

        try:
            task = create_content_generation_task(props_json, channel)
            crew = Crew(
                agents=[task.agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            )

            result = crew.kickoff()
            return self._parse_content_result(str(result))

        except Exception as e:
            logger.error("Content generation failed: %s", e)
            return self._fallback_content(property_data, channel)

    # ------------------------------------------------------------------
    # Fallback methods (rule-based when LLM unavailable)
    # ------------------------------------------------------------------
    def _fallback_qualify(self, posts: list[dict]) -> list[dict]:
        """Rule-based fallback for lead qualification."""
        from src.outreach.social_radar import SocialRadar

        radar = SocialRadar()
        return radar.scan_posts(posts)

    def _fallback_reply(self, message: str, sender_name: str) -> str:
        """Simple fallback reply."""
        return (
            f"مرحباً {sender_name}! 👋\n"
            "شكراً على رسالتك.\n"
            "هرد عليك في أقرب وقت. 🏠"
        )

    def _fallback_content(self, prop: dict, channel: str) -> dict:
        """Template-based fallback for content generation."""
        from src.outreach.content_generator import ContentGenerator

        gen = ContentGenerator()
        result = gen.generate(prop, channel=channel)
        return result

    # ------------------------------------------------------------------
    # Result parsing helpers
    # ------------------------------------------------------------------
    def _parse_json_result(self, result) -> dict | list:
        """Parse JSON from CrewAI result."""
        try:
            text = str(result)
            # Try JSON array first
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            # Try JSON object
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from crew result")
        return []

    def _parse_content_result(self, result: str) -> dict:
        """Parse content sections from crew result."""
        import re
        content = {"raw": result}

        # Split by numbered section headers (e.g., "1. **فيسبوك**" or "**فيسبوك**")
        section_pattern = r'(?:\d+\.\s*)?\*\*[^*]+\*\*'
        sections = re.split(section_pattern, result)
        section_names = re.findall(section_pattern, result)

        for i, name in enumerate(section_names):
            clean_name = name.replace("**", "").strip()
            body = sections[i + 1].strip() if i + 1 < len(sections) else ""
            # Find the next section header to determine boundaries
            next_match = re.search(section_pattern, body)
            if next_match:
                body = body[:next_match.start()].strip()
            # Remove trailing section numbers/markers
            body = re.split(r'\n\s*\d+\.', body)[0].strip()

            if any(k in clean_name for k in ["فيسبوك", "Facebook", "facebook"]):
                content["facebook"] = body
            elif any(k in clean_name for k in ["إنستجرام", "Instagram", "instagram"]):
                content["instagram"] = body
            elif any(k in clean_name for k in ["واتساب", "WhatsApp", "whatsapp"]):
                content["whatsapp"] = body

        return content

    # ------------------------------------------------------------------
    # Powerful Agent (General Assistant)
    # ------------------------------------------------------------------
    def ask_assistant(self, question: str) -> str:
        """Ask the powerful assistant agent a question.

        Args:
            question: User's question or task description

        Returns:
            Assistant's response
        """
        if not question:
            return ""

        if not self._llm_ready:
            return "LLM not available. Please configure OPENROUTER_API_KEY or install Ollama."

        try:
            agent = create_powerful_agent()
            task = Task(
                description=f"Answer this question about El Sadat City real estate: {question}",
                expected_output="A clear, helpful answer in Arabic or English",
                agent=agent,
            )
            crew = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            )

            result = crew.kickoff()
            return str(result).strip()

        except Exception as e:
            logger.error("Assistant query failed: %s", e)
            return f"Sorry, I encountered an error: {e!s}"

    # ------------------------------------------------------------------
    # Data Pipeline (Phase 5)
    # ------------------------------------------------------------------
    def process_data_pipeline(
        self, source: str, raw_data: str, skip_matching: bool = False
    ) -> dict:
        """Run the full data pipeline: collect → enrich → analyze → match.

        Args:
            source: Data source type ('whatsapp', 'facebook', 'web', 'json')
            raw_data: Raw text/data to process
            skip_matching: Skip property matching step

        Returns:
            Dict with pipeline results
        """
        result = {
            "extraction": None,
            "enrichment": None,
            "analysis": None,
            "matching": None,
            "errors": [],
        }

        if not self._llm_ready:
            return self._fallback_pipeline(source, raw_data)

        # Step 1: Extract data
        try:
            task1 = create_data_collection_task(source, raw_data)
            crew1 = Crew(
                agents=[task1.agent],
                tasks=[task1],
                process=Process.sequential,
                verbose=False,
            )
            extraction = crew1.kickoff()
            result["extraction"] = self._parse_json_result(extraction)
        except Exception as e:
            logger.error("Data extraction failed: %s", e)
            result["errors"].append(f"extraction: {e}")
            return result

        # Step 2: Enrich data
        try:
            task2 = create_data_enrichment_task(json.dumps(result["extraction"], ensure_ascii=False))
            crew2 = Crew(
                agents=[task2.agent],
                tasks=[task2],
                process=Process.sequential,
                verbose=False,
            )
            enrichment = crew2.kickoff()
            result["enrichment"] = self._parse_json_result(enrichment)
        except Exception as e:
            logger.error("Data enrichment failed: %s", e)
            result["errors"].append(f"enrichment: {e}")

        # Step 3: Analyze lead
        try:
            combined_data = result["extraction"]
            if result["enrichment"]:
                enrichment = result["enrichment"]
                if isinstance(enrichment, list):
                    enrichment = enrichment[0] if enrichment else {}
                if isinstance(combined_data, list):
                    combined_data = combined_data[0] if combined_data else {}
                combined_data = {**combined_data, **enrichment}
            task3 = create_lead_analysis_task(json.dumps(combined_data, ensure_ascii=False))
            crew3 = Crew(
                agents=[task3.agent],
                tasks=[task3],
                process=Process.sequential,
                verbose=False,
            )
            analysis = crew3.kickoff()
            result["analysis"] = self._parse_json_result(analysis)
        except Exception as e:
            logger.error("Lead analysis failed: %s", e)
            result["errors"].append(f"analysis: {e}")

        # Step 4: Match properties (optional)
        if not skip_matching and result["analysis"]:
            try:
                extraction = result["extraction"]
                if isinstance(extraction, list):
                    extraction = extraction[0] if extraction else {}
                analysis = result["analysis"]
                if isinstance(analysis, list):
                    analysis = analysis[0] if analysis else {}
                client_data = {
                    **extraction,
                    "analysis": analysis,
                }
                task4 = create_property_matching_task(json.dumps(client_data, ensure_ascii=False))
                crew4 = Crew(
                    agents=[task4.agent],
                    tasks=[task4],
                    process=Process.sequential,
                    verbose=False,
                )
                matching = crew4.kickoff()
                result["matching"] = self._parse_json_result(matching)
            except Exception as e:
                logger.error("Property matching failed: %s", e)
                result["errors"].append(f"matching: {e}")

        return result

    def research_market(self, area: str | None = None) -> dict:
        """Run market research for El Sadat City.

        Args:
            area: Specific area to research (optional)

        Returns:
            Dict with market research data
        """
        if not self._llm_ready:
            return self._fallback_market_research(area)

        try:
            task = create_market_research_task(area)
            crew = Crew(
                agents=[task.agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            )
            result = crew.kickoff()
            parsed = self._parse_json_result(result)
            return parsed if isinstance(parsed, dict) else {"market_report": parsed}
        except Exception as e:
            logger.error("Market research failed: %s", e)
            return self._fallback_market_research(area)

    def _fallback_pipeline(self, source: str, raw_data: str) -> dict:
        """Rule-based fallback for data pipeline."""
        try:
            from src.data.extractor import DataExtractor
            extractor = DataExtractor()
            if source == "whatsapp":
                extracted = extractor.extract_from_whatsapp(raw_data)
            elif source == "facebook":
                extracted = extractor.extract_from_facebook(raw_data)
            else:
                extracted = {"error": "fallback not supported for this source"}
            return {"extraction": extracted, "enrichment": None, "analysis": None, "matching": None, "errors": ["llm_unavailable"]}
        except Exception as e:
            return {"extraction": None, "enrichment": None, "analysis": None, "matching": None, "errors": [str(e)]}

    def _fallback_market_research(self, area: str | None = None) -> dict:
        """Fallback market research using static data."""
        try:
            from src.data.enricher import AREA_METADATA
            return {
                "market_report": {
                    "area": area or "مدينة السادات",
                    "area_metadata": AREA_METADATA.get(area, {}) if area else AREA_METADATA,
                    "source": "static_data",
                }
            }
        except Exception as e:
            return {"market_report": {"error": str(e)}}

    # ------------------------------------------------------------------
    # Personalized Bulk Outreach
    # ------------------------------------------------------------------
    def generate_personalized_message(self, buyer_data: dict) -> str:
        """Generate a unique, personalized message for a single buyer.

        Uses 3-agent pipeline:
        1. Researcher: Gathers market data for buyer's area
        2. Writer: Creates unique message based on research
        3. Reviewer: Ensures quality and uniqueness

        Args:
            buyer_data: Dict with name, city, property_type, budget, etc.

        Returns:
            Personalized message string
        """
        if not buyer_data:
            return ""

        if not self._llm_ready:
            return self._fallback_personalized(buyer_data)

        try:
            # Create agents
            researcher = create_buyer_researcher()
            writer = create_personalized_writer()
            reviewer = create_message_reviewer()

            # Create tasks
            research_task = create_buyer_research_task(researcher, buyer_data)
            writing_task = create_personalized_writing_task(
                writer, buyer_data, [research_task]
            )
            review_task = create_message_review_task(
                reviewer, [writing_task]
            )

            # Run the crew
            crew = Crew(
                agents=[researcher, writer, reviewer],
                tasks=[research_task, writing_task, review_task],
                process=Process.sequential,
                verbose=False,
                memory=True,
            )

            result = crew.kickoff()
            message = str(result).strip()

            # Ensure message is not too long
            if len(message) > 1000:
                message = message[:997] + "..."

            return message

        except Exception as e:
            logger.error("Personalized message generation failed: %s", e)
            return self._fallback_personalized(buyer_data)

    def generate_bulk_messages(self, buyers: list[dict]) -> list[str]:
        """Generate personalized messages for multiple buyers.

        Args:
            buyers: List of buyer dicts

        Returns:
            List of message strings (parallel to buyers list)
        """
        messages = []
        for buyer in buyers:
            message = self.generate_personalized_message(buyer)
            messages.append(message)
        return messages

    def _fallback_personalized(self, buyer: dict) -> str:
        """Fallback personalized message when LLM is unavailable."""
        name = buyer.get("name", "عميل")
        city = buyer.get("city", "منطقتك")
        property_type = buyer.get("property_type", "العقار")
        budget = buyer.get("budget", "ميزانيتك")

        return (
            f"مرحباً {name}! 👋\n\n"
            f"شفنا إنك بتدور على {property_type} في {city} "
            f"بميزانية {budget}.\n\n"
            f"عندنا عروض مميزة في المنطقة — عايز نبعتلك التفاصيل؟\n\n"
            f"رد 'نعم' وهنبعتلك كل حاجة فوراً 🏠"
        )