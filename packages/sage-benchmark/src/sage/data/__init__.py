"""
Shared Data Directory
=====================

This directory contains shared datasets organized by data type/characteristic,
enabling data sharing across different benchmarks.

Structure:
- **qa/**: Question-Answering datasets and knowledge bases (used by RAG, QA systems, etc.)
- **locomo/**: Long-Context Memory datasets with loader and downloader (use `python -m sage.data.locomo.download`)

Design: Data is organized by what it represents, not which benchmark uses it.
This enables multiple benchmarks to share the same datasets efficiently.
"""

__all__: list[str] = []
