#!/usr/bin/env python3
"""
Article Monitoring System Example

This script demonstrates the Article Monitoring application from sage-apps.
It monitors arXiv for relevant research papers using keyword and semantic filtering.

Requirements:
    pip install -e packages/sage-apps

Usage:
    python examples/apps/run_article_monitoring.py
    python examples/apps/run_article_monitoring.py --keywords "transformer,attention"
    python examples/apps/run_article_monitoring.py --category cs.CL --max-articles 20

Test Configuration:
    @test_category: apps
    @test_speed: medium
    @test_requires: [network]  # May need network for arXiv API
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

try:
    from sage.apps.article_monitoring import run_article_monitoring_pipeline
    from sage.common.utils.logging.custom_logger import CustomLogger
except ImportError as e:
    print(f"Error importing sage.apps.article_monitoring: {e}")
    print("\nPlease install sage-apps:")
    print("  pip install -e packages/sage-apps")
    sys.exit(1)


def main():
    """Run the article monitoring pipeline."""
    parser = argparse.ArgumentParser(
        description="SAGE Article Monitoring System - Monitor and filter arXiv papers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default settings
  python %(prog)s

  # Custom keywords
  python %(prog)s --keywords "transformer,attention,bert,nlp"

  # Different category
  python %(prog)s --category cs.CL --max-articles 20

  # Verbose mode
  python %(prog)s --verbose

Features:
  - Real-time arXiv paper fetching
  - Keyword-based filtering
  - Semantic similarity filtering
  - Ranked recommendations
        """,
    )

    parser.add_argument(
        "--keywords",
        "-k",
        type=str,
        help="Comma-separated list of keywords",
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

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

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

    print("=" * 70)
    print("SAGE Article Monitoring System - Example")
    print("=" * 70)
    print()

    # Run pipeline
    try:
        run_article_monitoring_pipeline(
            keywords=keywords,
            interest_topics=topics,
            category=args.category,
            max_articles=args.max_articles,
            verbose=args.verbose,
        )
    except Exception as e:
        print(f"\nError running article monitoring pipeline: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
