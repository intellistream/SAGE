"""Document Processing Utilities for RAG

Provides reusable utilities for processing documents into chunks suitable for
RAG indexing. These are pure utility functions with no SAGE-specific dependencies.

Layer: L1 (sage-common)
Dependencies: Standard library only
"""

import re
from collections.abc import Iterable
from pathlib import Path
from typing import TypedDict

# Supported file extensions for Markdown documents
SUPPORTED_MARKDOWN_SUFFIXES = {".md", ".markdown"}


class Section(TypedDict):
    """A section extracted from a document."""

    heading: str
    content: str


def iter_markdown_files(source: Path) -> Iterable[Path]:
    """Iterate over all Markdown files in a directory tree.

    Args:
        source: Root directory to scan

    Yields:
        Path objects for each Markdown file (sorted by path)

    Example:
        >>> for file in iter_markdown_files(Path("docs")):
        ...     print(file)
        docs/intro.md
        docs/guide/tutorial.md
    """
    for path in sorted(source.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_MARKDOWN_SUFFIXES:
            yield path


_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(?P<title>.+?)\s*$")


def parse_markdown_sections(content: str) -> list[Section]:
    """Parse Markdown content into sections based on headings.

    Splits content at heading boundaries (# through ######), grouping
    text under each heading into a section. The first section before
    any heading is labeled "Introduction".

    Args:
        content: Markdown document as string

    Returns:
        List of sections, each with 'heading' and 'content' keys
        Empty sections (no content) are filtered out

    Example:
        >>> text = '''
        ... # Overview
        ... This is the intro.
        ...
        ... ## Details
        ... More content here.
        ... '''
        >>> sections = parse_markdown_sections(text)
        >>> len(sections)
        2
        >>> sections[0]['heading']
        'Overview'
    """
    sections: list[Section] = []
    current_title = "Introduction"
    current_lines: list[str] = []

    for raw_line in content.splitlines():
        match = _HEADING_PATTERN.match(raw_line.strip())
        if match:
            # Save previous section
            if current_lines:
                sections.append(
                    {
                        "heading": current_title,
                        "content": "\n".join(current_lines).strip(),
                    }
                )
                current_lines = []
            # Start new section
            current_title = match.group("title").strip()
        else:
            current_lines.append(raw_line)

    # Save final section
    if current_lines:
        sections.append({"heading": current_title, "content": "\n".join(current_lines).strip()})

    # Filter out empty sections
    return [section for section in sections if section["content"]]


def chunk_text(content: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Chunk text into overlapping segments with smart boundary detection.

    Splits text into chunks of approximately chunk_size characters, with
    overlap between consecutive chunks. Attempts to break at natural
    boundaries (newlines, sentence endings) rather than mid-word.

    Algorithm:
    1. Normalize whitespace (collapse 3+ newlines to 2)
    2. Use sliding window with step = chunk_size - chunk_overlap
    3. For chunks not at document end, try to break at:
       - Newline (preferred)
       - Chinese period (。)
       - English period (.)
    4. Only break at boundary if it's in the latter 60% of the chunk

    Args:
        content: Text to chunk
        chunk_size: Target size for each chunk (characters)
        chunk_overlap: Overlap between consecutive chunks (characters)

    Returns:
        List of text chunks, with empty chunks filtered out

    Example:
        >>> text = "First sentence. Second sentence. Third sentence."
        >>> chunks = chunk_text(text, chunk_size=20, chunk_overlap=5)
        >>> len(chunks) >= 2
        True
    """
    # Normalize excessive newlines
    normalized = re.sub(r"\n{3,}", "\n\n", content).strip()
    if not normalized:
        return []

    start = 0
    length = len(normalized)
    step = max(1, chunk_size - chunk_overlap)
    chunks: list[str] = []

    while start < length:
        end = min(length, start + chunk_size)
        chunk = normalized[start:end]

        # For non-final chunks, try to break at natural boundary
        if end < length:
            # Find rightmost boundary (newline or period)
            boundary = max(chunk.rfind("\n"), chunk.rfind("。"), chunk.rfind("."))

            # Only break if boundary is in latter 60% of chunk
            # (prevents very small chunks)
            if boundary >= 0 and boundary > len(chunk) * 0.4:
                end = start + boundary
                chunk = normalized[start:end]

        chunks.append(chunk.strip())
        start += step

    # Filter out empty chunks
    return [c for c in chunks if c]


def slugify(text: str) -> str:
    """Convert text to URL-safe slug format.

    Converts text to lowercase, replaces non-alphanumeric characters
    with hyphens, and removes consecutive hyphens.

    Args:
        text: Text to slugify

    Returns:
        URL-safe slug (or "section" if result is empty)

    Example:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("C++ Programming")
        'c-programming'
    """
    slug = re.sub(r"[^\w\-]+", "-", text.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug or "section"


def truncate_text(text: str, limit: int = 480) -> str:
    """Truncate text to specified character limit, adding ellipsis if needed.

    Args:
        text: Text to truncate
        limit: Maximum length (default: 480)

    Returns:
        Truncated text with "..." suffix if truncated, otherwise original text

    Example:
        >>> truncate_text("Short text", limit=100)
        'Short text'
        >>> truncate_text("Very long text" * 50, limit=20)
        'Very long textVer...'
    """
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def sanitize_metadata_value(value: str) -> str:
    """Sanitize text for use as vector database metadata.

    Performs the following transformations:
    - Remove backslashes (avoid JSON escape issues in C++ parser)
    - Replace carriage returns and newlines with spaces
    - Replace double quotes with single quotes
    - Replace patterns that look like JSON keys (avoid C++ parser confusion)
    - Collapse multiple spaces into one
    - Trim leading/trailing whitespace

    This ensures metadata values are safe for JSON serialization and
    don't contain problematic characters that confuse the C++ parser.

    Args:
        value: Raw metadata value

    Returns:
        Sanitized string

    Example:
        >>> sanitize_metadata_value('Line 1\\nLine 2')
        'Line 1 Line 2'
        >>> sanitize_metadata_value('He said "hello"')
        "He said 'hello'"
        >>> sanitize_metadata_value('dict["key"]: {value}')
        "dict['key']: (value)"
    """
    # Remove backslashes to avoid JSON/C++ parser issues
    cleaned = value.replace("\\", "")
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")
    # Replace double quotes with single quotes
    cleaned = cleaned.replace('"', "'")
    # Replace { and } with ( and ) to avoid JSON-like patterns
    cleaned = cleaned.replace("{", "(").replace("}", ")")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()
