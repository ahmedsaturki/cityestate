"""
LLM Configuration — إعداد نموذج الذكاء الاصطناعي
=================================================
Supports multiple LLM backends:
1. OpenRouter (free models) — default
2. Ollama (100% free, runs locally)
3. Groq (free tier)
4. Google Gemini (free tier)

Falls back to rule-based parsing if no LLM is available.
"""

import logging
import os
from typing import Any

logger = logging.getLogger("ai_crew.llm")


# ---------------------------------------------------------------------------
# Ollama Detection
# ---------------------------------------------------------------------------
def _check_ollama_available() -> bool:
    """Check if Ollama is running locally."""
    try:
        import httpx
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        response = httpx.get(f"{ollama_url}/api/tags", timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def _ensure_openrouter_key() -> None:
    """Set OPENROUTER_API_KEY from ROUTER_API_KEY if not set.

    CrewAI's native OpenRouter provider looks for OPENROUTER_API_KEY.
    """
    if not os.getenv("OPENROUTER_API_KEY") and os.getenv("ROUTER_API_KEY"):
        os.environ["OPENROUTER_API_KEY"] = os.getenv("ROUTER_API_KEY", "")


def get_llm(model: str | None = None, temperature: float = 0.1) -> Any | None:
    """Get a configured LLM instance.

    Tries LLM providers in order:
    1. OpenRouter (if ROUTER_API_KEY set)
    2. Ollama (if running locally)
    3. Returns None (fallback to rule-based)

    For CrewAI agents: returns model name string.
    For IntentParser/ContentGenerator: returns ChatOpenAI instance.

    Args:
        model: Model ID (defaults to ROUTER_MODEL from .env)
        temperature: Creativity level (0.0 = deterministic, 1.0 = creative)

    Returns:
        ChatOpenAI instance, Ollama model string, or None
    """
    # --- Priority 1: OpenRouter ---
    api_key = os.getenv("ROUTER_API_KEY", "")
    if api_key:
        base_url = os.getenv("ROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        model_id = model or os.getenv("ROUTER_MODEL", "inclusionai/ling-3.0-flash:free")

        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=model_id,
                openai_api_key=api_key,
                openai_api_base=base_url,
                temperature=temperature,
                max_tokens=1024,
                request_timeout=120,
            )
            logger.info("LLM configured (OpenRouter): %s", model_id)
            return llm

        except Exception as e:
            logger.error("Failed to initialize OpenRouter LLM: %s", e)

    # --- Priority 2: Ollama (free, local) ---
    if _check_ollama_available():
        ollama_model = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        try:
            from langchain_community.llms import Ollama

            llm = Ollama(
                model=ollama_model,
                base_url=ollama_url,
                temperature=temperature,
            )
            logger.info("LLM configured (Ollama): %s", ollama_model)
            return llm

        except Exception as e:
            logger.error("Failed to initialize Ollama LLM: %s", e)

    # --- No LLM available ---
    logger.warning("No LLM available — using rule-based fallback")
    return None


def get_crewai_model() -> str:
    """Get model name string for CrewAI agents.

    Tries providers in order:
    1. OpenRouter (if ROUTER_API_KEY set)
    2. Ollama (if running locally)
    3. Returns None (CrewAI will use fallback)

    Returns model string or None.
    """
    # --- Priority 1: OpenRouter ---
    api_key = os.getenv("ROUTER_API_KEY", "")
    if api_key:
        _ensure_openrouter_key()
        model_id = os.getenv("ROUTER_MODEL", "inclusionai/ling-3.0-flash:free")
        return f"openrouter/{model_id}"

    # --- Priority 2: Ollama ---
    if _check_ollama_available():
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        return f"ollama/{ollama_model}"

    # --- No LLM ---
    return None


def is_llm_available() -> bool:
    """Check if any LLM is configured and available."""
    if os.getenv("ROUTER_API_KEY"):
        return True
    return bool(_check_ollama_available())


def get_llm_provider() -> str:
    """Get the name of the currently active LLM provider."""
    if os.getenv("ROUTER_API_KEY"):
        return "openrouter"
    if _check_ollama_available():
        return "ollama"
    return "none"
