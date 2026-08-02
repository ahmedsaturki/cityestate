"""
Skills Package — حزم المهارات القوية
====================================
Powerful agent skills for CityEstate automation.
"""

from .checklist_builder import ChecklistSkill, get_checklist_tools
from .computer_use import ComputerUseSkill, get_computer_use_tools
from .decision_matrix import DecisionMatrixSkill, get_decision_tools
from .document_processing import DocumentProcessingSkill, get_document_tools
from .email_skill import EmailSkill, get_email_tools
from .goal_tracker import GoalTrackerSkill, get_goal_tools
from .google_maps import GoogleMapsSkill, get_maps_tools
from .google_search import GoogleSearchSkill, get_search_tools
from .image_analysis import ImageAnalysisSkill, get_image_tools
from .kanban_board import KanbanSkill, get_kanban_tools
from .lead_scoring import LeadScoringSkill, get_lead_scoring_tools
from .notes_brainstorming import NotesSkill, get_notes_tools
from .report_generator import ReportGeneratorSkill, get_report_tools
from .task_manager import TaskManagerSkill, get_task_tools
from .time_tracker import TimeTrackerSkill, get_time_tools
from .translator import TranslatorSkill, get_translator_tools
from .voice_speech import VoiceSpeechSkill, get_voice_tools
from .web_scraper import WebScraperSkill, get_scraper_tools
from .whatsapp_web_skill import WhatsAppWebSkill, get_whatsapp_web_tools

__all__ = [
    # Checklists
    "ChecklistSkill",
    # Computer Use
    "ComputerUseSkill",
    # Decision Matrix
    "DecisionMatrixSkill",
    # Document Processing
    "DocumentProcessingSkill",
    # Email
    "EmailSkill",
    # Goal Tracking
    "GoalTrackerSkill",
    # Maps & Location
    "GoogleMapsSkill",
    # Search
    "GoogleSearchSkill",
    # Image Analysis
    "ImageAnalysisSkill",
    # Kanban Board
    "KanbanSkill",
    # Lead Scoring & Auto-Matching
    "LeadScoringSkill",
    # Notes & Brainstorming
    "NotesSkill",
    # Reports
    "ReportGeneratorSkill",
    # Task Management
    "TaskManagerSkill",
    # Time Tracking
    "TimeTrackerSkill",
    # Translation
    "TranslatorSkill",
    # Voice/Speech
    "VoiceSpeechSkill",
    # Web Scraping
    "WebScraperSkill",
    # WhatsApp Web Browser Automation
    "WhatsAppWebSkill",
    "get_checklist_tools",
    "get_computer_use_tools",
    "get_decision_tools",
    "get_document_tools",
    "get_email_tools",
    "get_goal_tools",
    "get_image_tools",
    "get_kanban_tools",
    "get_lead_scoring_tools",
    "get_maps_tools",
    "get_notes_tools",
    "get_report_tools",
    "get_scraper_tools",
    "get_search_tools",
    "get_task_tools",
    "get_time_tools",
    "get_translator_tools",
    "get_voice_tools",
    "get_whatsapp_web_tools",
]


def get_all_skills():
    """Return all available skill classes."""
    return {
        "computer_use": ComputerUseSkill,
        "google_search": GoogleSearchSkill,
        "web_scraper": WebScraperSkill,
        "google_maps": GoogleMapsSkill,
        "email": EmailSkill,
        "document_processing": DocumentProcessingSkill,
        "image_analysis": ImageAnalysisSkill,
        "voice_speech": VoiceSpeechSkill,
        "task_manager": TaskManagerSkill,
        "goal_tracker": GoalTrackerSkill,
        "checklist": ChecklistSkill,
        "decision_matrix": DecisionMatrixSkill,
        "kanban": KanbanSkill,
        "time_tracker": TimeTrackerSkill,
        "report_generator": ReportGeneratorSkill,
        "notes": NotesSkill,
        "translator": TranslatorSkill,
        "whatsapp_web": WhatsAppWebSkill,
    }


def get_all_tools():
    """Return all CrewAI-compatible tools from all skills."""
    tools = []
    tools.extend(get_computer_use_tools())
    tools.extend(get_search_tools())
    tools.extend(get_scraper_tools())
    tools.extend(get_maps_tools())
    tools.extend(get_email_tools())
    tools.extend(get_document_tools())
    tools.extend(get_image_tools())
    tools.extend(get_voice_tools())
    tools.extend(get_task_tools())
    tools.extend(get_goal_tools())
    tools.extend(get_checklist_tools())
    tools.extend(get_decision_tools())
    tools.extend(get_kanban_tools())
    tools.extend(get_time_tools())
    tools.extend(get_report_tools())
    tools.extend(get_notes_tools())
    tools.extend(get_translator_tools())
    tools.extend(get_whatsapp_web_tools())
    tools.extend(get_lead_scoring_tools())
    return tools
