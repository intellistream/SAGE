"""
Article Monitoring Pipeline

Main pipeline implementation using SAGE operators for article monitoring.
"""

from __future__ import annotations

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment

from .operators import (
    ArticleLogSink,
    ArticleRankingSink,
    ArticleScorer,
    ArxivSource,
    KeywordFilter,
    SemanticFilter,
)


def run_article_monitoring_pipeline(
    keywords: list[str] | None = None,
    interest_topics: list[str] | None = None,
    category: str = "cs.AI",
    max_articles: int = 10,
    verbose: bool = False,
) -> None:
    """
    Run the article monitoring pipeline using SAGE framework.

    Args:
        keywords: List of keywords for initial filtering
        interest_topics: List of topics for semantic filtering
        category: arXiv category to monitor
        max_articles: Maximum number of articles to fetch
        verbose: Enable verbose logging

    Example:
        >>> run_article_monitoring_pipeline(
        ...     keywords=["machine learning", "deep learning"],
        ...     interest_topics=["artificial intelligence applications"],
        ...     category="cs.AI",
        ...     max_articles=20
        ... )
    """
    # Default parameters
    if keywords is None:
        keywords = [
            "machine learning",
            "deep learning",
            "neural network",
            "stream processing",
        ]

    if interest_topics is None:
        interest_topics = [
            "artificial intelligence and machine learning applications",
            "data stream processing and real-time systems",
            "distributed computing and scalability",
        ]

    print("=" * 70)
    print("🔍 SAGE Article Monitoring System")
    print("=" * 70)
    print(f"Category: {category}")
    print(f"Max Articles: {max_articles}")
    print(f"Keywords: {keywords}")
    print(
        f"Interest Topics: {', '.join(t[:40] + '...' if len(t) > 40 else t for t in interest_topics)}"
    )
    print("=" * 70)
    print()

    # Create SAGE environment
    env = LocalEnvironment("article_monitoring")

    # Build pipeline:
    # 1. ArxivSource: Fetch articles from arXiv
    # 2. KeywordFilter: Filter by keywords
    # 3. SemanticFilter: Filter by semantic similarity
    # 4. ArticleScorer: Calculate final scores
    # 5. ArticleRankingSink: Collect and display results
    pipeline = (
        env.from_batch(
            ArxivSource,
            category=category,
            max_results=max_articles,
        )
        .map(KeywordFilter, keywords=keywords, min_score=1.0)
        .map(SemanticFilter, interest_topics=interest_topics, min_similarity=0.05)
        .map(ArticleScorer)
        .sink(ArticleRankingSink)
    )

    # Optionally add logging sink
    if verbose:
        pipeline.sink(ArticleLogSink)

    # Execute pipeline
    print("📡 Starting pipeline...")
    print()
    env.submit(autostop=True)


def main():
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SAGE Article Monitoring System - Monitor and filter arXiv papers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default settings
  python -m sage.apps.article_monitoring.pipeline

  # Custom keywords and topics
  python -m sage.apps.article_monitoring.pipeline \\
      --keywords "transformer,attention,bert" \\
      --topics "natural language processing and transformers" \\
      --category cs.CL \\
      --max-articles 30

  # Verbose mode
  python -m sage.apps.article_monitoring.pipeline --verbose
        """,
    )

    parser.add_argument(
        "--keywords",
        "-k",
        type=str,
        help="Comma-separated list of keywords (default: machine learning,deep learning,neural network)",
    )

    parser.add_argument(
        "--topics",
        "-t",
        type=str,
        help="Comma-separated list of interest topics",
    )

    parser.add_argument(
        "--category",
        "-c",
        type=str,
        default="cs.AI",
        help="arXiv category to monitor (default: cs.AI)",
    )

    parser.add_argument(
        "--max-articles",
        "-m",
        type=int,
        default=10,
        help="Maximum number of articles to fetch (default: 10)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Parse keywords
    keywords = None
    if args.keywords:
        keywords = [kw.strip() for kw in args.keywords.split(",")]

    # Parse topics
    topics = None
    if args.topics:
        topics = [t.strip() for t in args.topics.split(",")]

    # Disable global console debug unless verbose
    if not args.verbose:
        CustomLogger.disable_global_console_debug()

    # Run pipeline
    run_article_monitoring_pipeline(
        keywords=keywords,
        interest_topics=topics,
        category=args.category,
        max_articles=args.max_articles,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
