"""
Configuration Loader
====================
Loads YAML configs and environment variables for the CrewAI system.
"""

import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

logger = logging.getLogger("config")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = PROJECT_ROOT / "logs"


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
def load_environment() -> dict:
    """Load .env and return configuration dictionary.

    Raises ConfigurationError if required files or env vars are missing
    instead of calling sys.exit(), so callers can handle the error
    gracefully (e.g. return a meaningful HTTP 500 in an API context).
    """
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        logger.warning(".env file not found — using environment variables directly.")

    api_key = os.getenv("ROUTER_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        raise ConfigurationError(
            "ROUTER_API_KEY is not configured properly in .env "
            "or environment. Set it to a valid OpenRouter API key."
        )

    # Bridge to LiteLLM's expected env var
    os.environ["OPENROUTER_API_KEY"] = api_key

    # Disable OpenTelemetry BEFORE any CrewAI import
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["OTEL_TRACES_EXPORTER"] = "none"
    os.environ["OTEL_METRICS_EXPORTER"] = "none"
    os.environ["OTEL_LOGS_EXPORTER"] = "none"

    return {
        "base_url": os.getenv("ROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "api_key": api_key,
        "model": os.getenv("ROUTER_MODEL", "google/gemini-2.0-flash-001"),
        "jina_api_key": os.getenv("JINA_API_KEY", ""),
    }


# ---------------------------------------------------------------------------
# LLM Factory
# ---------------------------------------------------------------------------
def create_llm(config: dict):
    """Create LLM with low temperature to minimize hallucinations."""
    from crewai import LLM

    model = config["model"]

    # Route through OpenRouter
    if not model.startswith("openrouter/"):
        model = f"openrouter/{model}"

    return LLM(
        model=model,
        api_key=config["api_key"],
        timeout=120,
        temperature=0.1,
        max_tokens=8192,
    )


# ---------------------------------------------------------------------------
# YAML Loaders
# ---------------------------------------------------------------------------
def load_agents_config() -> dict:
    """Load agents.yaml configuration."""
    agents_file = CONFIG_DIR / "agents.yaml"
    with open(agents_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # Support both flat format and nested (agents: {...})
    return data.get("agents", data) if isinstance(data, dict) else data


def load_tasks_config() -> dict:
    """Load tasks.yaml configuration."""
    tasks_file = CONFIG_DIR / "tasks.yaml"
    with open(tasks_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # Support both flat format and nested (tasks: {...})
    return data.get("tasks", data) if isinstance(data, dict) else data


# ---------------------------------------------------------------------------
# Directory Setup
# ---------------------------------------------------------------------------
def ensure_directories():
    """Create required directories if they don't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
