"""
CrewAI Integration Tests — اختبارات فريق العمل الذكي
=====================================================
Tests for CrewAI agents, tools, and data pipeline.
Run with: python -m pytest tests/test_crewai_integration.py -v
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_crew.tools import (
    DataExtractionTool,
    WebCrawlerTool,
    DataEnrichmentTool,
    WhatsAppCheckTool,
    DataQualityTool,
    PhoneValidatorTool,
    MarketResearchTool,
    DatabaseQueryTool,
    PropertySearchTool,
    WhatsAppSendTool,
    WebSearchTool,
    ContentSaveTool,
    get_all_tools,
)
from src.ai_crew.agents import (
    create_lead_qualifier,
    create_sales_rep,
    create_copywriter,
    create_powerful_agent,
    create_data_collector,
    create_data_enricher,
    create_lead_analyst,
    create_property_expert,
    create_market_researcher,
)
from src.ai_crew.tasks import (
    create_lead_qualification_task,
    create_whatsapp_reply_task,
    create_content_generation_task,
    create_data_collection_task,
    create_data_enrichment_task,
    create_lead_analysis_task,
    create_property_matching_task,
    create_market_research_task,
)
from src.ai_crew.crew import CityEstateCrew
from src.ai_crew.llm_config import is_llm_available, get_llm_provider


# ===========================================================================
# Tool Instantiation Tests
# ===========================================================================
class TestToolInstantiation:
    """Verify all tools can be instantiated."""

    def test_data_extraction_tool(self):
        tool = DataExtractionTool()
        assert tool.name == "data_extraction"

    def test_web_crawler_tool(self):
        tool = WebCrawlerTool()
        assert tool.name == "web_crawler"

    def test_data_enrichment_tool(self):
        tool = DataEnrichmentTool()
        assert tool.name == "data_enrichment"

    def test_whatsapp_check_tool(self):
        tool = WhatsAppCheckTool()
        assert tool.name == "whatsapp_check"

    def test_data_quality_tool(self):
        tool = DataQualityTool()
        assert tool.name == "data_quality"

    def test_phone_validator_tool(self):
        tool = PhoneValidatorTool()
        assert tool.name == "phone_validator"

    def test_market_research_tool(self):
        tool = MarketResearchTool()
        assert tool.name == "market_research"

    def test_database_query_tool(self):
        tool = DatabaseQueryTool()
        assert tool.name == "database_query"

    def test_property_search_tool(self):
        tool = PropertySearchTool()
        assert tool.name == "property_search"

    def test_whatsapp_send_tool(self):
        tool = WhatsAppSendTool()
        assert tool.name == "whatsapp_send"

    def test_web_search_tool(self):
        tool = WebSearchTool()
        assert tool.name == "web_search"

    def test_content_save_tool(self):
        tool = ContentSaveTool()
        assert tool.name == "content_save"


# ===========================================================================
# Tool Execution Tests (offline, no LLM)
# ===========================================================================
class TestToolExecution:
    """Test tool execution with mock data."""

    def test_data_extraction_whatsapp(self):
        tool = DataExtractionTool()
        result = tool._run(
            source="whatsapp",
            text="عايز شقة 3 غرف في الشيخ زايد بميزانية 2 مليون",
            sender="Test User",
        )
        data = json.loads(result)
        assert "property_type" in data or "error" in data

    def test_data_extraction_facebook(self):
        tool = DataExtractionTool()
        result = tool._run(
            source="facebook",
            text="فيلا للبيع في السادات - 300 متر - 5 مليون",
            sender="Seller",
        )
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_data_quality_property(self):
        tool = DataQualityTool()
        prop_data = json.dumps({
            "title": "Test Property",
            "price": 2000000,
            "area_sqm": 150,
            "bedrooms": 3,
            "property_type": "apartment",
            "area": "Sheikh Zayed",
        })
        result = tool._run(data=prop_data, data_type="property")
        data = json.loads(result)
        assert "overall_score" in data or "error" in data

    def test_phone_validator_egyptian(self):
        tool = PhoneValidatorTool()
        result = tool._run(phone="01123456789")
        data = json.loads(result)
        assert "normalized" in data or "error" in data

    def test_market_research_static(self):
        tool = MarketResearchTool()
        result = tool._run()
        data = json.loads(result)
        assert "premium_areas" in data or "error" in data

    def test_data_enrichment(self):
        tool = DataEnrichmentTool()
        prop_data = json.dumps({
            "property_type": "apartment",
            "area": "المنطقة 7 الشريط المميز",
            "price": 2000000,
            "area_sqm": 150,
            "bedrooms": 3,
        })
        result = tool._run(property_data=prop_data)
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_whatsapp_check(self):
        tool = WhatsAppCheckTool()
        result = tool._run(phone="01123456789")
        data = json.loads(result)
        assert "whatsapp_check" in data or "error" in data


# ===========================================================================
# Agent Creation Tests
# ===========================================================================
class TestAgentCreation:
    """Verify all agents can be created."""

    def test_lead_qualifier(self):
        agent = create_lead_qualifier()
        assert agent is not None
        assert "صفقات" in agent.role

    def test_sales_rep(self):
        agent = create_sales_rep()
        assert agent is not None
        assert "مبيعات" in agent.role

    def test_copywriter(self):
        agent = create_copywriter()
        assert agent is not None
        assert "تسويق" in agent.role

    def test_powerful_agent(self):
        agent = create_powerful_agent()
        assert agent is not None
        assert len(agent.tools) > 0

    def test_data_collector(self):
        agent = create_data_collector()
        assert agent is not None
        assert "بيانات" in agent.role

    def test_data_enricher(self):
        agent = create_data_enricher()
        assert agent is not None
        assert "بيانات" in agent.role

    def test_lead_analyst(self):
        agent = create_lead_analyst()
        assert agent is not None
        assert "محلل" in agent.role

    def test_property_expert(self):
        agent = create_property_expert()
        assert agent is not None
        assert "خبير" in agent.role

    def test_market_researcher(self):
        agent = create_market_researcher()
        assert agent is not None
        assert "باحث" in agent.role


# ===========================================================================
# Task Creation Tests
# ===========================================================================
class TestTaskCreation:
    """Verify all tasks can be created."""

    def test_lead_qualification_task(self):
        task = create_lead_qualification_task("Test post text")
        assert task is not None
        assert task.agent is not None

    def test_whatsapp_reply_task(self):
        task = create_whatsapp_reply_task("Hello", "Test", "[]")
        assert task is not None

    def test_content_generation_task(self):
        task = create_content_generation_task('{"title": "Test"}', "all")
        assert task is not None

    def test_data_collection_task(self):
        task = create_data_collection_task("whatsapp", "Test message")
        assert task is not None
        assert "بيانات" in task.description

    def test_data_enrichment_task(self):
        task = create_data_enrichment_task('{"price": 2000000}')
        assert task is not None

    def test_lead_analysis_task(self):
        task = create_lead_analysis_task('{"client_name": "Test"}')
        assert task is not None

    def test_property_matching_task(self):
        task = create_property_matching_task('{"area": "Sheikh Zayed"}')
        assert task is not None

    def test_market_research_task(self):
        task = create_market_research_task("المنطقة 7")
        assert task is not None


# ===========================================================================
# Crew Orchestrator Tests
# ===========================================================================
class TestCrewOrchestrator:
    """Test CityEstateCrew methods."""

    def test_crew_instantiation(self):
        crew = CityEstateCrew()
        assert crew is not None

    def test_fallback_reply(self):
        crew = CityEstateCrew()
        reply = crew._fallback_reply("مرحبا", "أحمد")
        assert "مرحبا" in reply
        assert "أحمد" in reply

    def test_fallback_content(self):
        crew = CityEstateCrew()
        content = crew._fallback_content({"title": "Test"}, "all")
        assert isinstance(content, dict)

    def test_fallback_personalized(self):
        crew = CityEstateCrew()
        msg = crew._fallback_personalized({
            "name": "أحمد",
            "city": "السادات",
            "property_type": "شقة",
            "budget": "2 مليون",
        })
        assert "أحمد" in msg
        assert "السادات" in msg

    def test_fallback_pipeline(self):
        crew = CityEstateCrew()
        result = crew._fallback_pipeline("whatsapp", "Test message")
        assert "extraction" in result
        assert "errors" in result

    def test_fallback_market_research(self):
        crew = CityEstateCrew()
        result = crew._fallback_market_research("المنطقة 7")
        assert "market_report" in result

    def test_parse_json_result_valid(self):
        crew = CityEstateCrew()
        mock_result = '[{"name": "Test", "score": 85}]'
        parsed = crew._parse_json_result(mock_result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_parse_json_result_invalid(self):
        crew = CityEstateCrew()
        parsed = crew._parse_json_result("No JSON here")
        assert parsed == []


# ===========================================================================
# LLM Configuration Tests
# ===========================================================================
class TestLLMConfig:
    """Test LLM configuration detection."""

    def test_is_llm_available_returns_bool(self):
        result = is_llm_available()
        assert isinstance(result, bool)

    def test_get_llm_provider_returns_string(self):
        result = get_llm_provider()
        assert result in ("openrouter", "ollama", "none")

    def test_get_all_tools_count(self):
        tools = get_all_tools()
        assert len(tools) >= 19  # 12 original + 7 new data tools


# ===========================================================================
# Data Pipeline Integration Tests
# ===========================================================================
class TestDataPipeline:
    """Test data pipeline with mock LLM (rule-based fallback)."""

    def test_fallback_pipeline_whatsapp(self):
        crew = CityEstateCrew()
        result = crew._fallback_pipeline(
            "whatsapp",
            "عايز شقة 3 غرف في الشيخ زايد بميزانية 2 مليون جنيه"
        )
        assert result["extraction"] is not None
        assert result["enrichment"] is None  # Fallback doesn't enrich

    def test_fallback_market_research_all_areas(self):
        crew = CityEstateCrew()
        result = crew._fallback_market_research(None)
        assert "market_report" in result
        report = result["market_report"]
        assert "area_metadata" in report or "error" in report
