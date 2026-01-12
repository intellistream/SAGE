"""Text processing and manipulation utilities."""

from __future__ import annotations

import re
from typing import Callable


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace (collapse multiple spaces, trim)."""
    return " ".join(text.split())


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length, adding suffix if truncated."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def extract_keywords(
    text: str, stopwords: set[str] | None = None, min_length: int = 3
) -> list[str]:
    """Extract keywords from text (simple word extraction).

    Args:
        text: Input text
        stopwords: Set of stopwords to filter out
        min_length: Minimum word length

    Returns:
        List of keywords
    """
    if stopwords is None:
        stopwords = set()

    # Extract words
    words = re.findall(r"\b\w+\b", text.lower())

    # Filter by length and stopwords
    keywords = [w for w in words if len(w) >= min_length and w not in stopwords]

    return keywords


def split_sentences(text: str) -> list[str]:
    """Split text into sentences (simple regex-based)."""
    # Simple sentence splitter
    sentences = re.split(r"[.!?]+", text)
    return [s.strip() for s in sentences if s.strip()]


def deduplicate_lines(text: str, keep_order: bool = True) -> str:
    """Remove duplicate lines from text.

    Args:
        text: Input text
        keep_order: If True, preserve original line order

    Returns:
        Text with duplicate lines removed
    """
    lines = text.split("\n")
    if keep_order:
        seen = set()
        unique_lines = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        return "\n".join(unique_lines)
    else:
        return "\n".join(list(set(lines)))


def apply_template(template: str, **kwargs) -> str:
    """Apply template with variables.

    Args:
        template: Template string with {var} placeholders
        **kwargs: Variable values

    Returns:
        Formatted string
    """
    return template.format(**kwargs)


def batch_transform(texts: list[str], transform_fn: Callable[[str], str]) -> list[str]:
    """Apply transformation function to list of texts.

    Args:
        texts: List of input texts
        transform_fn: Function to apply to each text

    Returns:
        List of transformed texts
    """
    return [transform_fn(text) for text in texts]


__all__ = [
    "normalize_whitespace",
    "truncate_text",
    "extract_keywords",
    "split_sentences",
    "deduplicate_lines",
    "apply_template",
    "batch_transform",
]
