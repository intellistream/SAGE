"""Content filtering utilities."""

from __future__ import annotations

import re
from typing import Pattern


class ContentFilter:
    """Pattern-based content filter."""

    def __init__(self, patterns: list[str | Pattern] | None = None):
        """Initialize filter with patterns.

        Args:
            patterns: List of regex patterns or compiled patterns
        """
        self.patterns = []
        if patterns:
            for p in patterns:
                if isinstance(p, str):
                    self.patterns.append(re.compile(p, re.IGNORECASE))
                else:
                    self.patterns.append(p)

    def add_pattern(self, pattern: str | Pattern) -> None:
        """Add a filter pattern.

        Args:
            pattern: Regex pattern or compiled pattern
        """
        if isinstance(pattern, str):
            self.patterns.append(re.compile(pattern, re.IGNORECASE))
        else:
            self.patterns.append(pattern)

    def contains_violation(self, text: str) -> tuple[bool, list[str]]:
        """Check if text contains any violations.

        Args:
            text: Text to check

        Returns:
            Tuple of (has_violation, matched_patterns)
        """
        matches = []
        for pattern in self.patterns:
            if pattern.search(text):
                matches.append(pattern.pattern)

        return len(matches) > 0, matches

    def filter_text(self, text: str, replacement: str = "[FILTERED]") -> str:
        """Filter text by replacing violations.

        Args:
            text: Input text
            replacement: Replacement string

        Returns:
            Filtered text
        """
        result = text
        for pattern in self.patterns:
            result = pattern.sub(replacement, result)
        return result


# Predefined filter patterns
PROFANITY_PATTERNS = [
    r"\b(fuck|shit|damn|hell|bastard)\b",
    # Add more patterns as needed
]

PERSONAL_ATTACK_PATTERNS = [
    r"you are (stupid|dumb|idiot)",
    r"(stupid|dumb|idiot) (person|user)",
]


def create_profanity_filter() -> ContentFilter:
    """Create a filter for profanity."""
    return ContentFilter(PROFANITY_PATTERNS)


def create_personal_attack_filter() -> ContentFilter:
    """Create a filter for personal attacks."""
    return ContentFilter(PERSONAL_ATTACK_PATTERNS)


__all__ = [
    "ContentFilter",
    "PROFANITY_PATTERNS",
    "PERSONAL_ATTACK_PATTERNS",
    "create_profanity_filter",
    "create_personal_attack_filter",
]
