"""
Outreach Module
===============
Multi-channel outreach engine for Egyptian real estate lead engagement.
AI-powered with LLM (CrewAI/OpenRouter) when available,
falls back to rule-based parsing.
"""

from .content_generator import ContentGenerator
from .engine import OutreachEngine
from .intent_parser import IntentParser, ParsedIntent
from .social_radar import SocialRadar

__all__ = [
    "ContentGenerator",
    "IntentParser",
    "OutreachEngine",
    "ParsedIntent",
    "SocialRadar",
]
