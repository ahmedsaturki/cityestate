"""
AI Crew Module — فريق العمل الذكي
===================================
CrewAI-powered agents for Egyptian real estate automation.
Replaces regex-based parsing with LLM-driven intelligence.
"""

from .crew import CityEstateCrew
from .llm_config import get_llm

__all__ = ["CityEstateCrew", "get_llm"]
