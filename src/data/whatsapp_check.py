"""
WhatsApp Checker — فاحص واتساب
===============================
Verifies if phone numbers are registered on WhatsApp.
Used for lead qualification and contact verification.

El Sadat City premium real estate focus.
"""

import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger("data.whatsapp_check")


# ---------------------------------------------------------------------------
# Egyptian Phone Number Patterns
# ---------------------------------------------------------------------------
EGYPT_PHONE_PATTERNS = [
    r"^(\+20\s*1[0-9]{9})$",       # +20 1XXXXXXXXX
    r"^(20\s*1[0-9]{9})$",          # 20 1XXXXXXXXX
    r"^(01[0-9]{9})$",              # 01XXXXXXXXX
    r"^(\+201[0-9]{9})$",           # +201XXXXXXXXX (no space)
]


# ---------------------------------------------------------------------------
# WhatsAppChecker
# ---------------------------------------------------------------------------
class WhatsAppChecker:
    """
    Checks if phone numbers are registered on WhatsApp.

    Features:
    - Egyptian phone number normalization
    - WhatsApp registration check (via browser automation)
    - Batch verification
    - Rate limiting

    Note: Actual WhatsApp check requires browser automation (Playwright).
    This module provides the interface and data model.
    """

    def __init__(self):
        self._check_count = 0
        self._results_cache: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Phone Normalization
    # ------------------------------------------------------------------
    def normalize_phone(self, phone: str) -> str | None:
        """
        Normalize Egyptian phone number to international format.

        Args:
            phone: Raw phone number string.

        Returns:
            Normalized phone number (+201XXXXXXXXX) or None.
        """
        if not phone:
            return None

        # Remove spaces, dashes, parentheses
        cleaned = re.sub(r"[\s\-\(\)\.]", "", phone.strip())

        # Try patterns
        for pattern in EGYPT_PHONE_PATTERNS:
            match = re.match(pattern, cleaned)
            if match:
                number = match.group(1)
                # Normalize to +201XXXXXXXXX
                if number.startswith("+20"):
                    return number.replace(" ", "")
                elif number.startswith("20"):
                    return "+" + number
                elif number.startswith("01"):
                    return "+20" + number
                elif number.startswith("+201"):
                    return number

        # If it looks like a valid Egyptian mobile (11 digits starting with 01)
        if re.match(r"^01[0-9]{9}$", cleaned):
            return "+20" + cleaned

        logger.warning("Could not normalize phone: %s", phone)
        return None

    # ------------------------------------------------------------------
    # WhatsApp Registration Check
    # ------------------------------------------------------------------
    def check_whatsapp(self, phone: str) -> dict:
        """
        Check if a phone number is registered on WhatsApp.

        Args:
            phone: Phone number to check.

        Returns:
            dict with:
                - phone: Normalized phone number
                - has_whatsapp: bool
                - is_business: bool (if detectable)
                - checked_at: ISO timestamp
                - status: "success" | "error" | "not_checked"
        """
        normalized = self.normalize_phone(phone)
        if not normalized:
            return {
                "phone": phone,
                "has_whatsapp": False,
                "is_business": False,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "status": "invalid_number",
            }

        # Check cache
        if normalized in self._results_cache:
            logger.debug("Cache hit for %s", normalized)
            return self._results_cache[normalized]

        # In production, this would use Playwright to check WhatsApp Web
        # For now, return a placeholder
        result = {
            "phone": normalized,
            "has_whatsapp": None,  # Unknown until checked
            "is_business": None,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": "not_checked",
            "message": "Requires browser automation to check",
        }

        self._check_count += 1
        self._results_cache[normalized] = result
        return result

    def check_batch(self, phones: list[str]) -> list[dict]:
        """
        Check multiple phone numbers for WhatsApp registration.

        Args:
            phones: List of phone numbers.

        Returns:
            List of check result dicts.
        """
        results = []
        for phone in phones:
            result = self.check_whatsapp(phone)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Lead Qualification
    # ------------------------------------------------------------------
    def qualify_lead(self, phone: str, name: str | None = None,
                      property_type: str | None = None, budget: float | None = None) -> dict:
        """
        Qualify a lead based on WhatsApp availability and data quality.

        Args:
            phone: Contact phone number.
            name: Contact name.
            property_type: Property type interest.
            budget: Budget amount.

        Returns:
            dict with qualification score and recommendation.
        """
        score = 0
        reasons = []

        # Phone normalization
        normalized = self.normalize_phone(phone)
        if normalized:
            score += 30
            reasons.append("valid_phone")
        else:
            reasons.append("invalid_phone")

        # Name available
        if name and len(name.strip()) > 2:
            score += 15
            reasons.append("name_available")

        # Property type specified
        if property_type:
            score += 20
            reasons.append("property_type_specified")

        # Budget specified and above minimum
        if budget and budget >= 1_500_000:
            score += 25
            reasons.append("budget_above_minimum")
        elif budget:
            reasons.append("budget_below_minimum")

        # Premium indicator
        if budget and budget >= 3_000_000:
            score += 10
            reasons.append("premium_budget")

        # Determine recommendation
        if score >= 70:
            recommendation = "high_priority"
        elif score >= 40:
            recommendation = "medium_priority"
        else:
            recommendation = "low_priority"

        return {
            "phone": normalized or phone,
            "qualification_score": score,
            "recommendation": recommendation,
            "reasons": reasons,
            "qualified_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def is_egyptian_number(self, phone: str) -> bool:
        """Check if a phone number is Egyptian."""
        normalized = self.normalize_phone(phone)
        return normalized is not None and normalized.startswith("+20")

    def extract_phones_from_text(self, text: str) -> list[str]:
        """Extract all phone numbers from a text."""
        phones = []
        # Common phone patterns in Arabic/English text
        patterns = [
            r"\+20\s*\d{10}",
            r"01[0-9]\d{8}",
            r"\d{11}",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                normalized = self.normalize_phone(match)
                if normalized and normalized not in phones:
                    phones.append(normalized)
        return phones

    @property
    def stats(self) -> dict:
        """Return check statistics."""
        return {
            "total_checks": self._check_count,
            "cached_results": len(self._results_cache),
        }

    def clear_cache(self):
        """Clear the results cache."""
        self._results_cache.clear()
