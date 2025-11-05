"""
Article Monitoring System

An intelligent article monitoring system that continuously fetches papers from arXiv,
performs multi-level filtering (keyword-based and semantic), and provides personalized
recommendations to users.

Built on SAGE framework using stream processing operators.

Features:
- Real-time article fetching from arXiv
- Keyword-based filtering using bag-of-words
- Semantic filtering using text similarity
- Personalized recommendations
- Stream processing with SAGE operators
"""

from .pipeline import run_article_monitoring_pipeline

__all__ = ["run_article_monitoring_pipeline"]
