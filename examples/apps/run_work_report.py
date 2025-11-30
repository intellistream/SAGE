#!/usr/bin/env python3
"""
Work Report Generator Example

This script demonstrates the Work Report Generator application from sage-apps.
It generates weekly/daily work reports by combining GitHub data with optional diary entries.

Requirements:
    pip install -e packages/sage-apps

Usage:
    python examples/apps/run_work_report.py
    python examples/apps/run_work_report.py --days 7
    python examples/apps/run_work_report.py --format json --output report.json
    python examples/apps/run_work_report.py --no-submodules --branch main

Test Configuration:
    @test_category: apps
    @test_speed: medium
    @test_requires: [network]  # Needs GitHub API access
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

try:
    from sage.apps.work_report_generator import run_work_report_pipeline
    from sage.apps.work_report_generator.operators import GitHubDataSource
    from sage.common.utils.logging.custom_logger import CustomLogger
except ImportError as e:
    print(f"Error importing sage.apps.work_report_generator: {e}")
    print("\nPlease install sage-apps:")
    print("  pip install -e packages/sage-apps")
    sys.exit(1)


def main():
    """Run the work report generator pipeline."""
    parser = argparse.ArgumentParser(
        description="SAGE Work Report Generator - Generate weekly/daily work reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default settings (all SAGE repos, main-dev branch, 7 days)
  python %(prog)s

  # Main repo only, without submodules
  python %(prog)s --no-submodules

  # Specify custom repositories
  python %(prog)s --repos intellistream/SAGE,intellistream/sageLLM

  # Use different branch (e.g., main instead of main-dev)
  python %(prog)s --branch main

  # Custom time range
  python %(prog)s --days 14

  # JSON output
  python %(prog)s --format json --output reports/weekly.json

  # English report with verbose output
  python %(prog)s --language en --verbose

  # Without LLM summarization (faster)
  python %(prog)s --no-llm

Environment Variables:
  GITHUB_TOKEN or GIT_TOKEN: GitHub personal access token

Features:
  - Fetches commits and PRs from GitHub repositories
  - Supports fetching from specific branches (default: main-dev)
  - Includes all SAGE submodules by default
  - Aggregates contributions by contributor
  - Generates AI-powered summaries (optional)
  - Supports markdown, JSON, and console output
        """,
    )

    parser.add_argument(
        "--repos",
        "-r",
        type=str,
        default=None,
        help="Comma-separated list of repositories. If not specified, fetches all SAGE repos.",
    )

    parser.add_argument(
        "--branch",
        "-b",
        type=str,
        default="main-dev",
        help="Branch name to fetch commits from (default: main-dev)",
    )

    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=7,
        help="Number of days to look back (default: 7)",
    )

    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["console", "markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (default: .sage/reports/weekly_report_<date>.<ext>)",
    )

    parser.add_argument(
        "--diary-path",
        type=str,
        help="Path to diary directory or file for personal notes",
    )

    parser.add_argument(
        "--language",
        "-l",
        type=str,
        choices=["zh", "en"],
        default="zh",
        help="Report language (default: zh for Chinese)",
    )

    parser.add_argument(
        "--token",
        "-t",
        type=str,
        help="GitHub personal access token (can also use GITHUB_TOKEN env var)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM summary generation for faster reports",
    )

    parser.add_argument(
        "--no-submodules",
        action="store_true",
        help="Only fetch from main SAGE repo, skip submodules",
    )

    args = parser.parse_args()

    # Setup logging
    logger = CustomLogger.get_logger(__name__)

    # Parse repositories
    repos = None
    if args.repos:
        repos = [r.strip() for r in args.repos.split(",")]

    # Get GitHub token
    github_token = (
        args.token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GIT_TOKEN")
    )

    if not github_token:
        logger.warning(
            "No GitHub token provided. Set GITHUB_TOKEN environment variable "
            "or use --token option for full functionality. Using mock data."
        )

    # Determine repos to display
    display_repos = (
        repos
        if repos
        else (
            GitHubDataSource.SAGE_REPOS
            if not args.no_submodules
            else ["intellistream/SAGE"]
        )
    )

    # Print configuration
    print()
    print("Configuration:")
    print(f"  Target Branch: {args.branch}")
    print(f"  Repositories ({len(display_repos)}):")
    for repo in display_repos:
        print(f"    - {repo}")
    print(f"  Time Range: {args.days} days")
    print(f"  Output Format: {args.format}")
    print(f"  Language: {'Chinese' if args.language == 'zh' else 'English'}")
    print(f"  LLM Summary: {'Disabled' if args.no_llm else 'Enabled'}")
    print(
        f"  GitHub Token: {'Provided' if github_token else 'Not provided (mock data)'}"
    )
    print()

    # Run pipeline
    try:
        result = run_work_report_pipeline(
            repos=repos,
            branch=args.branch,
            days=args.days,
            output_format=args.format,
            output_path=args.output,
            diary_path=args.diary_path,
            language=args.language,
            github_token=github_token,
            verbose=args.verbose,
            use_llm=not args.no_llm,
            include_submodules=not args.no_submodules,
        )

        if result:
            print(f"\n Report saved to: {result}")
            print("\nTo view the report:")
            print(f"  cat {result}")

    except KeyboardInterrupt:
        print("\n\n Pipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
