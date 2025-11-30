"""
Work Report Generator - Weekly/Daily report generator based on SAGE framework.

This application generates work reports by combining:
- GitHub commit and PR data from specified repositories
- Optional diary entries for personal notes
- LLM-powered summarization and formatting

Example:
    >>> from sage.apps.work_report_generator import run_work_report_pipeline
    >>> run_work_report_pipeline(
    ...     repos=["intellistream/SAGE"],
    ...     days=7,
    ...     output_format="markdown"
    ... )
"""

from .pipeline import run_work_report_pipeline

__all__ = ["run_work_report_pipeline"]
