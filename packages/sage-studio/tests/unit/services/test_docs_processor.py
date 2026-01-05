"""Tests for the SAGE documentation processor used in Studio fine-tuning."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from sage.studio.services.docs_processor import SAGEDocsProcessor


@pytest.fixture()
def processor(tmp_path: Path) -> SAGEDocsProcessor:
    """Provide a processor that writes into a temp directory."""
    return SAGEDocsProcessor(output_dir=tmp_path)


def test_clean_markdown_removes_noise(processor: SAGEDocsProcessor):
    dirty_md = dedent(
        """
        ## Heading

        Some text with a [link](https://example.com) and image ![img](path).

        ```python
        print("code")
        ```
        """
    )

    cleaned = processor._clean_markdown(dirty_md)

    assert "link" in cleaned and "https://" not in cleaned
    assert "print" in cleaned and "```" not in cleaned
    assert "img" not in cleaned


def test_split_by_headers_handles_sections(processor: SAGEDocsProcessor):
    content = dedent(
        """
        # Title
        Intro
        ## Section A
        Content A
        ### SubSection A1
        Content A1
        ## Section B
        Content B
        """
    )

    sections = [section for section in processor._split_by_headers(content) if section[0]]

    assert sections[0][0] == "Title"
    assert "Content A" in sections[1][1]
    assert sections[-1][0] == "Section B"
    assert "Content B" in sections[-1][1]


def test_convert_markdown_to_qa_generates_pairs(processor: SAGEDocsProcessor):
    md = dedent(
        """
        # Overview
        This is a detailed section about SAGE with enough characters to surpass the
        trimming threshold. It explains the system modules and gives additional context
        so the total length is significant.

        ## Usage
        Another paragraph that is long enough to be kept, describing how engineers use
        the toolkit every day with numerous steps and details so it exceeds fifty chars.
        """
    )

    qa_pairs = processor.convert_markdown_to_qa(md, "guide.md")

    assert len(qa_pairs) == 2
    assert qa_pairs[0]["instruction"].startswith("请介绍 SAGE 框架中")
    assert "Overview" in qa_pairs[0]["instruction"]
    assert qa_pairs[1]["instruction"].startswith("请介绍 SAGE 框架中")
    assert qa_pairs[1]["output"].strip().startswith("Another")


def test_prepare_training_data_roundtrip(processor: SAGEDocsProcessor, monkeypatch):
    source_dir = processor.output_dir / "raw_docs" / "docs_src"
    source_dir.mkdir(parents=True)
    sample_file = source_dir / "intro.md"
    sample_file.write_text("## Hello\n" + "lorem ipsum " * 20, encoding="utf-8")

    def fake_download(force_refresh: bool = False) -> Path:  # pragma: no cover - simple helper
        return source_dir

    monkeypatch.setattr(processor, "download_docs", fake_download)

    output = processor.prepare_training_data(force_refresh=False)
    assert output.exists()

    stats = processor.get_stats(output)
    assert stats["total_samples"] >= 1
    assert stats["estimated_tokens"] > 0
