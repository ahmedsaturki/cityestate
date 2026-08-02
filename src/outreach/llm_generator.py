"""
LLM Message Generator
=====================
Generates unique per-lead messages using OpenRouter API.
Falls back to None on failure, triggering template fallback in engine.

Architecture Decision:
- Structured JSON output parsing with regex fallback
- Segment-specific prompts for tone calibration
- Channel-aware formatting (email subject+body, SMS 160 chars, WhatsApp 500 chars)
- Timeout protection against hanging API calls
"""

import json
import logging
import os
import re

import requests

logger = logging.getLogger("outreach.llm_generator")

# Segment tone descriptions for prompt injection
SEGMENT_TONES: dict[str, str] = {
    "diaspora": (
        "Aspirational and ROI-focused. Emphasize investing in one's roots, "
        "heritage connection, and premium returns. Tone: warm, respectful, proud."
    ),
    "investor": (
        "Data-driven and yield-focused. Emphasize metrics, market fundamentals, "
        "and smart capital allocation. Tone: professional, analytical, confident."
    ),
    "developer": (
        "Partnership and portfolio-focused. Emphasize collaboration, qualified "
        "buyer access, and market reach. Tone: professional, forward-looking."
    ),
    "buyer": (
        "Value and affordability-focused. Emphasize payment plans, government "
        "programs, and homeownership accessibility. Tone: friendly, encouraging, supportive."
    ),
    "unknown": (
        "Professional and informative. Provide market overview and invite "
        "further conversation. Tone: neutral, helpful, professional."
    ),
}

# Channel constraints for prompt injection
CHANNEL_CONSTRAINTS: dict[str, str] = {
    "email": (
        "Write a subject line (max 60 characters, compelling) and a body "
        "(max 500 characters, structured with greeting, value proposition, and CTA)."
    ),
    "sms": (
        "Write a single SMS message (max 160 characters). Be concise. "
        "Include a value hook and placeholder for link."
    ),
    "whatsapp": (
        "Write a WhatsApp message (max 500 characters). Use 1-2 emojis. "
        "Be friendly and conversational. Include CTA."
    ),
}


class LLMGenerator:
    """Generate unique outreach messages via OpenRouter API.

    Uses structured prompts with segment tone and channel constraints.
    Returns None on any failure to trigger graceful fallback.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "google/gemini-2.0-flash-exp:free",
        temperature: float = 0.7,
        timeout: int = 30,
    ) -> None:
        """
        Args:
            api_key: OpenRouter API key. Falls back to ROUTER_API_KEY env var.
            model: Model identifier (auto-prefixed with openrouter/ if missing).
            temperature: Generation temperature (0.7 = creative but coherent).
            timeout: API request timeout in seconds.
        """
        self.api_key = api_key or os.getenv("ROUTER_API_KEY", "")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

        if not self.model.startswith("openrouter/"):
            self.model = f"openrouter/{self.model}"

        # Strip openrouter/ prefix for API call (API expects bare model ID)
        self._api_model = self.model.replace("openrouter/", "")

        self._request_count: int = 0
        self._error_count: int = 0

    def _build_prompt(self, lead: dict, channel: str, segment: str) -> str:
        """Construct the system+user prompt for message generation.

        Includes lead context, segment tone, and channel constraints.
        """
        tone = SEGMENT_TONES.get(segment, SEGMENT_TONES["unknown"])
        constraints = CHANNEL_CONSTRAINTS.get(channel, CHANNEL_CONSTRAINTS["email"])

        lead_title = lead.get("title", "Real estate opportunity")
        area = lead.get("area", "Prime Location")
        budget = lead.get("budget", "Competitive Price")
        interest = lead.get("interest", "Property")
        url = lead.get("url", "#")

        prompt = (
            f"You are an expert Egyptian real estate marketing copywriter.\n\n"
            f"TASK: Write a single {channel} outreach message for this lead.\n\n"
            f"LEAD CONTEXT:\n"
            f"- Title: {lead_title}\n"
            f"- Area: {area}\n"
            f"- Budget: {budget}\n"
            f"- Interest: {interest}\n"
            f"- Reference URL: {url}\n\n"
            f"SEGMENT TONE:\n{tone}\n\n"
            f"CHANNEL CONSTRAINTS:\n{constraints}\n\n"
            f"OUTPUT FORMAT:\n"
            f"Return ONLY a JSON object with these keys:\n"
            f'{{"subject": "...", "body": "..."}}\n\n'
            f'For SMS and WhatsApp, "subject" can be an empty string "".\n'
            f"Do NOT include any text outside the JSON object."
        )

        return prompt

    def _parse_response(self, content: str) -> dict[str, str] | None:
        """Extract JSON from LLM response with multiple fallback strategies.

        Handles: clean JSON, markdown code blocks, embedded JSON in text.
        """
        # Strategy 1: Direct JSON parse
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "body" in data:
                return {"subject": data.get("subject", ""), "body": data["body"]}
        except (json.JSONDecodeError, TypeError):
            pass

        # Strategy 2: Extract from markdown code block
        code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if code_block:
            try:
                data = json.loads(code_block.group(1))
                if isinstance(data, dict) and "body" in data:
                    return {"subject": data.get("subject", ""), "body": data["body"]}
            except (json.JSONDecodeError, TypeError):
                pass

        # Strategy 3: Find JSON-like object in text
        json_match = re.search(r"\{[^{}]*\"body\"[^{}]*\}", content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if isinstance(data, dict) and "body" in data:
                    return {"subject": data.get("subject", ""), "body": data["body"]}
            except (json.JSONDecodeError, TypeError):
                pass

        # Strategy 4: Use entire response as body if it's short enough
        stripped = content.strip()
        if stripped and len(stripped) <= 1000:
            logger.warning("Could not parse JSON, using raw response as body")
            return {"subject": "", "body": stripped}

        return None

    def generate(self, lead: dict, channel: str, segment: str) -> dict[str, str] | None:
        """Generate a unique message for a lead via OpenRouter API.

        Args:
            lead: Lead dict with title, area, budget, interest, url fields.
            channel: Target channel (email, sms, whatsapp).
            segment: Segment key (diaspora, investor, developer, buyer, unknown).

        Returns:
            Dict with 'subject' and 'body' keys, or None on failure.
        """
        if not self.api_key:
            logger.warning("No API key configured, cannot generate LLM message")
            return None

        prompt = self._build_prompt(lead, channel, segment)

        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://cityestate.com",
                    "X-Title": "CityEstate Outreach Engine",
                },
                json={
                    "model": self._api_model,
                    "messages": [
                        {"role": "system", "content": "You are a JSON-only output generator. Return only valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": self.temperature,
                    "max_tokens": 600,
                },
                timeout=self.timeout,
            )
            self._request_count += 1

            if response.status_code != 200:
                logger.warning(
                    "LLM API returned status %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                self._error_count += 1
                return None

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not content:
                logger.warning("LLM returned empty content")
                self._error_count += 1
                return None

            result = self._parse_response(content)
            if result:
                # Enforce channel length constraints
                if channel == "sms" and len(result["body"]) > 160:
                    result["body"] = result["body"][:157] + "..."
                elif channel == "whatsapp" and len(result["body"]) > 500:
                    result["body"] = result["body"][:497] + "..."
                elif channel == "email" and len(result["body"]) > 2000:
                    result["body"] = result["body"][:1997] + "..."

                return result
            else:
                logger.warning("Failed to parse LLM response as JSON")
                self._error_count += 1
                return None

        except requests.exceptions.Timeout:
            logger.warning("LLM API request timed out after %ds", self.timeout)
            self._error_count += 1
            return None
        except requests.exceptions.RequestException as e:
            logger.warning("LLM API request failed: %s", e)
            self._error_count += 1
            return None
        except Exception as e:
            logger.error("Unexpected error in LLM generation: %s", e)
            self._error_count += 1
            return None

    @property
    def stats(self) -> dict:
        """Generator usage statistics."""
        return {
            "requests": self._request_count,
            "errors": self._error_count,
            "success_rate": (
                (self._request_count - self._error_count) / self._request_count
                if self._request_count > 0
                else 0.0
            ),
        }
