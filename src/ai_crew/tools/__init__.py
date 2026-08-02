"""
CityEstate AI Crew Tools
==========================
Modular tool package for the CrewAI agent system.
"""

import logging

logger = logging.getLogger("cityestate.crew.tools")

from src.ai_crew.tools.content import *
from src.ai_crew.tools.data import *
from src.ai_crew.tools.database import *
from src.ai_crew.tools.market import *
from src.ai_crew.tools.phone import *
from src.ai_crew.tools.properties import *
from src.ai_crew.tools.web import *
from src.ai_crew.tools.whatsapp import *
from src.skills.checklist_builder import get_checklist_tools
from src.skills.computer_use import get_computer_use_tools
from src.skills.decision_matrix import get_decision_tools
from src.skills.document_processing import get_document_tools
from src.skills.email_skill import get_email_tools
from src.skills.goal_tracker import get_goal_tools
from src.skills.google_maps import get_maps_tools
from src.skills.google_search import get_search_tools
from src.skills.image_analysis import get_image_tools
from src.skills.kanban_board import get_kanban_tools
from src.skills.lead_scoring import get_lead_scoring_tools
from src.skills.notes_brainstorming import get_notes_tools
from src.skills.report_generator import get_report_tools
from src.skills.task_manager import get_task_tools
from src.skills.time_tracker import get_time_tools
from src.skills.translator import get_translator_tools
from src.skills.voice_speech import get_voice_tools
from src.skills.web_scraper import get_scraper_tools


def get_all_tools() -> list:
    """Return all available tools: core + powerful skills."""
    core_tools = [
        DatabaseQueryTool(),
        PropertySearchTool(),
        WhatsAppSendTool(),
        WebSearchTool(),
        ContentSaveTool(),
    ]

    # Add all powerful agent skills
    skill_tools = []
    skill_tools.extend(get_computer_use_tools())
    skill_tools.extend(get_search_tools())
    skill_tools.extend(get_scraper_tools())
    skill_tools.extend(get_maps_tools())
    skill_tools.extend(get_email_tools())
    skill_tools.extend(get_document_tools())
    skill_tools.extend(get_image_tools())
    skill_tools.extend(get_voice_tools())
    skill_tools.extend(get_task_tools())
    skill_tools.extend(get_goal_tools())
    skill_tools.extend(get_checklist_tools())
    skill_tools.extend(get_decision_tools())
    skill_tools.extend(get_kanban_tools())
    skill_tools.extend(get_time_tools())
    skill_tools.extend(get_report_tools())
    skill_tools.extend(get_notes_tools())
    skill_tools.extend(get_translator_tools())
    skill_tools.extend(get_lead_scoring_tools())

    # NEW: Data system tools
    data_tools = [
        DataExtractionTool(),
        WebCrawlerTool(),
        DataEnrichmentTool(),
        WhatsAppCheckTool(),
        DataQualityTool(),
        PhoneValidatorTool(),
        MarketResearchTool(),
    ]

    return core_tools + skill_tools + data_tools

