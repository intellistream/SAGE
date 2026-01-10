"""PII (Personally Identifiable Information) scrubbing utilities."""

from __future__ import annotations

import re
from typing import Pattern


class PIIScrubber:
    """Simple PII detection and scrubbing."""

    # Common PII patterns
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    PHONE_PATTERN = re.compile(r"\b(\+?\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b")
    SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    CREDIT_CARD_PATTERN = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")
    IP_ADDRESS_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

    def __init__(self, custom_patterns: dict[str, Pattern] | None = None):
        """Initialize scrubber with optional custom patterns.

        Args:
            custom_patterns: Dictionary mapping PII type to regex pattern
        """
        self.patterns: dict[str, Pattern] = {
            "email": self.EMAIL_PATTERN,
            "phone": self.PHONE_PATTERN,
            "ssn": self.SSN_PATTERN,
            "credit_card": self.CREDIT_CARD_PATTERN,
            "ip_address": self.IP_ADDRESS_PATTERN,
        }

        if custom_patterns:
            self.patterns.update(custom_patterns)

    def detect_pii(self, text: str) -> dict[str, list[str]]:
        """Detect PII in text.

        Args:
            text: Input text

        Returns:
            Dictionary mapping PII type to list of matches
        """
        results = {}

        for pii_type, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                results[pii_type] = matches

        return results

    def scrub(self, text: str, replacement: str = "[REDACTED]") -> str:
        """Scrub PII from text.

        Args:
            text: Input text
            replacement: Replacement string

        Returns:
            Scrubbed text
        """
        result = text

        for pattern in self.patterns.values():
            result = pattern.sub(replacement, result)

        return result

    def scrub_by_type(self, text: str, replacements: dict[str, str] | None = None) -> str:
        """Scrub PII with type-specific replacements.

        Args:
            text: Input text
            replacements: Dictionary mapping PII type to replacement string

        Returns:
            Scrubbed text
        """
        if replacements is None:
            replacements = {}

        result = text

        for pii_type, pattern in self.patterns.items():
            replacement = replacements.get(pii_type, f"[REDACTED_{pii_type.upper()}]")
            result = pattern.sub(replacement, result)

        return result


def scrub_emails(text: str, replacement: str = "[EMAIL]") -> str:
    """Quick helper to scrub email addresses.

    Args:
        text: Input text
        replacement: Replacement string

    Returns:
        Text with emails scrubbed
    """
    return PIIScrubber.EMAIL_PATTERN.sub(replacement, text)


def scrub_phone_numbers(text: str, replacement: str = "[PHONE]") -> str:
    """Quick helper to scrub phone numbers.

    Args:
        text: Input text
        replacement: Replacement string

    Returns:
        Text with phone numbers scrubbed
    """
    return PIIScrubber.PHONE_PATTERN.sub(replacement, text)


__all__ = [
    "PIIScrubber",
    "scrub_emails",
    "scrub_phone_numbers",
]
