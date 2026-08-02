"""
PhoneValidatorExpert - Egyptian Phone Number Validation
=======================================================
Domain expert for validating and normalizing Egyptian phone numbers.

Secrets & Expertise:
    - Egyptian phone format: +20 1X XXXX XXXX
    - Carrier detection: Vodafone (010), Orange (011), Etisalat (012), WE (015)
    - Number type detection: mobile, landline, fax
    - Format normalization: all formats → +20XXXXXXXXXX
    - Duplicate detection across formats
    - Quality scoring based on completeness
"""

import logging
import re

logger = logging.getLogger("automation.experts.phone")


# Egyptian mobile carriers by prefix
CARRIER_MAP = {
    "010": "Vodafone",
    "011": "Orange",
    "012": "Etisalat",
    "015": "WE (Telecom Egypt)",
}

# Valid Egyptian mobile prefixes
VALID_MOBILE_PREFIXES = ["010", "011", "012", "015"]

# Phone format patterns
PHONE_PATTERNS = [
    # International format
    (r"\+20\s*1[0125]\s*\d{4}\s*\d{4}", "+20XXXXXXXXXX"),
    (r"\+20\s*1[0125]\d{8}", "+20XXXXXXXXXX"),
    # Local format
    (r"01[0125]\s*\d{4}\s*\d{4}", "01XXXXXXXXX"),
    (r"01[0125]\d{8}", "01XXXXXXXXX"),
    # Without prefix
    (r"201[0125]\d{8}", "201XXXXXXXXX"),
    # With spaces/dashes
    (r"01[0125]\s*\d{3}\s*\d{3}\s*\d{2}", "01XXXXXXXXX"),
    (r"01[0125]-\d{4}-\d{4}", "01XXXXXXXXX"),
]


class PhoneValidatorExpert:
    """Egyptian phone number validation expert.

    This expert:
    - Validates phone number format
    - Normalizes to +20XXXXXXXXXX format
    - Detects carrier (Vodafone, Orange, Etisalat, WE)
    - Identifies number type (mobile, landline)
    - Scores phone quality (0-100)
    - Handles Arabic numeral input
    - Detects duplicates across formats
    """

    def __init__(self) -> None:
        self._validation_cache: dict[str, dict] = {}

    def normalize(self, phone: str) -> str | None:
        """Normalize phone number to +20XXXXXXXXXX format.

        Args:
            phone: Phone number in any format

        Returns:
            Normalized phone or None if invalid
        """
        if not phone:
            return None

        # Check cache
        if phone in self._validation_cache:
            return self._validation_cache[phone].get("normalized")

        # Clean input
        cleaned = phone.strip()

        # Convert Arabic numerals
        arabic_to_english = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        cleaned = cleaned.translate(arabic_to_english)

        # Remove non-digit characters except +
        cleaned = re.sub(r"[^\d+]", "", cleaned)

        # Try each pattern
        for pattern, _ in PHONE_PATTERNS:
            match = re.search(pattern, cleaned)
            if match:
                normalized = match.group(0)
                # Ensure +20 prefix
                if normalized.startswith("+20"):
                    pass
                elif normalized.startswith("20"):
                    normalized = "+" + normalized
                elif normalized.startswith("0"):
                    normalized = "+20" + normalized[1:]
                elif normalized.startswith("1"):
                    normalized = "+20" + normalized

                # Validate length
                if len(normalized) == 13:  # +20XXXXXXXXXX
                    self._validation_cache[phone] = {"normalized": normalized}
                    return normalized

        return None

    def validate(self, phone: str) -> dict:
        """Validate a phone number with detailed analysis.

        Args:
            phone: Phone number in any format

        Returns:
            Dict with validation results
        """
        result = {
            "original": phone,
            "normalized": None,
            "is_valid": False,
            "carrier": None,
            "number_type": None,
            "quality_score": 0,
            "issues": [],
        }

        if not phone:
            result["issues"].append("empty_input")
            return result

        # Normalize
        normalized = self.normalize(phone)
        if not normalized:
            result["issues"].append("invalid_format")
            return result

        result["normalized"] = normalized
        result["is_valid"] = True

        # Extract prefix
        prefix = normalized[3:6]  # After +20

        # Detect carrier
        if prefix in CARRIER_MAP:
            result["carrier"] = CARRIER_MAP[prefix]
        else:
            result["issues"].append("unknown_carrier")

        # Detect number type
        if prefix in VALID_MOBILE_PREFIXES:
            result["number_type"] = "mobile"
        elif prefix.startswith("02"):
            result["number_type"] = "landline"
        elif prefix.startswith("015"):
            result["number_type"] = "mobile"  # WE is mobile
        else:
            result["number_type"] = "unknown"

        # Calculate quality score
        score = 0

        # Format validity (40 points)
        if result["is_valid"]:
            score += 40

        # Carrier known (20 points)
        if result["carrier"]:
            score += 20

        # Number type known (20 points)
        if result["number_type"] == "mobile":
            score += 20
        elif result["number_type"]:
            score += 10

        # Length valid (20 points)
        if len(normalized) == 13:
            score += 20

        result["quality_score"] = score

        return result

    def validate_batch(self, phones: list[str]) -> list[dict]:
        """Validate multiple phone numbers.

        Returns:
            List of validation results
        """
        return [self.validate(phone) for phone in phones]

    def deduplicate(self, phones: list[str]) -> list[str]:
        """Remove duplicate phone numbers (different formats).

        Returns:
            List of unique normalized phones
        """
        seen = set()
        unique = []

        for phone in phones:
            normalized = self.normalize(phone)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(normalized)

        return unique

    def format_for_display(self, phone: str) -> str:
        """Format phone number for human-readable display.

        Returns:
            Formatted string like: +20 101 234 5678
        """
        normalized = self.normalize(phone)
        if not normalized:
            return phone

        # +20 1XX XXX XXXX
        return f"+20 {normalized[3:6]} {normalized[6:9]} {normalized[9:13]}"

    def format_for_whatsapp(self, phone: str) -> str:
        """Format phone number for WhatsApp API.

        Returns:
            String like: 201012345678
        """
        normalized = self.normalize(phone)
        if not normalized:
            return phone

        # Remove + prefix for WhatsApp
        return normalized.lstrip("+")

    def get_stats(self, phones: list[str]) -> dict:
        """Get validation statistics for a batch of phones."""
        results = self.validate_batch(phones)

        return {
            "total": len(phones),
            "valid": sum(1 for r in results if r["is_valid"]),
            "invalid": sum(1 for r in results if not r["is_valid"]),
            "with_carrier": sum(1 for r in results if r["carrier"]),
            "mobile_count": sum(1 for r in results if r["number_type"] == "mobile"),
            "carriers": {
                carrier: sum(1 for r in results if r["carrier"] == carrier)
                for carrier in CARRIER_MAP.values()
            },
            "avg_quality": sum(r["quality_score"] for r in results) / max(len(results), 1),
        }
