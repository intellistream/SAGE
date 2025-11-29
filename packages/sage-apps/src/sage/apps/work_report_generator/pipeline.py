"""
Work Report Generator Pipeline

Main pipeline implementation using SAGE operators for weekly/daily report generation.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from sage.kernel.api.local_environment import LocalEnvironment

from .operators import (
    ConsoleSink,
    ContributorAggregator,
    DiaryEntrySource,
    GitHubDataSource,
    LLMReportGenerator,
    ReportSink,
)


def run_work_report_pipeline(
    repos: list[str] | None = None,
    days: int = 7,
    branch: str = "main-dev",
    output_format: str = "markdown",
    output_path: str | Path | None = None,
    diary_path: str | Path | None = None,
    language: str = "zh",
    github_token: str | None = None,
    verbose: bool = False,
    use_llm: bool = True,
    include_submodules: bool = True,
) -> str | None:
    """
    Run the work report generation pipeline using SAGE framework.

    This pipeline:
    1. Fetches commits and PRs from GitHub repositories (main + submodules)
    2. Optionally loads diary entries from local files
    3. Aggregates data by contributor
    4. Generates LLM-powered summaries (optional)
    5. Outputs the final report

    Args:
        repos: List of GitHub repositories in "owner/repo" format.
               If None, defaults to SAGE main repo + all submodules.
        days: Number of days to look back for contributions. Default 7.
        branch: Branch name to fetch commits from. Default "main-dev".
        output_format: Output format ("console", "markdown", "json").
        output_path: Path to save the report file. If None, outputs to console.
        diary_path: Path to diary directory or file for personal notes.
        language: Report language ("zh" for Chinese, "en" for English).
        github_token: GitHub personal access token. Uses env var if not provided.
        verbose: Enable verbose logging.
        use_llm: Whether to use LLM for generating summaries.
        include_submodules: If True and repos is None, include all SAGE submodules.

    Returns:
        Path to the generated report file, or None if outputting to console.

    Example:
        >>> run_work_report_pipeline(
        ...     days=7,
        ...     branch="main-dev",
        ...     output_format="markdown",
        ...     output_path="reports/weekly_report.md"
        ... )
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Get repo list for display
    display_repos = (
        repos
        if repos
        else GitHubDataSource.SAGE_REPOS
        if include_submodules
        else ["intellistream/SAGE"]
    )

    # Print header
    print("=" * 70)
    print(" SAGE Work Report Generator")
    print("=" * 70)
    print(f"Period: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"Target Branch: {branch}")
    print(f"Repositories ({len(display_repos)}):")
    for repo in display_repos:
        print(f"  - {repo}")
    print(f"Output Format: {output_format}")
    print(f"Language: {'Chinese' if language == 'zh' else 'English'}")
    print(f"LLM Summary: {'Enabled' if use_llm else 'Disabled'}")
    print("=" * 70)
    print()

    # Reset aggregator state (important for multiple pipeline runs)
    ContributorAggregator.reset()

    # Create SAGE environment
    env = LocalEnvironment("work_report_generator")

    # Determine output path
    if output_path is None and output_format != "console":
        output_dir = Path(".sage/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = "json" if output_format == "json" else "md"
        output_path = output_dir / f"weekly_report_{end_date.strftime('%Y%m%d')}.{ext}"

    # Build pipeline:
    # 1. GitHubDataSource: Fetch commits and PRs from main-dev branch
    # 2. ContributorAggregator: Group by contributor
    # 3. LLMReportGenerator: Generate AI summaries (optional)
    # 4. ReportSink: Output final report

    pipeline = env.from_batch(
        GitHubDataSource,
        repos=repos,
        days=days,
        branch=branch,
        github_token=github_token,
        include_submodules=include_submodules,
    ).map(ContributorAggregator)

    # Optionally add LLM summary generation
    if use_llm:
        pipeline = pipeline.map(LLMReportGenerator, language=language)

    # Add report sink
    pipeline = pipeline.sink(
        ReportSink,
        output_format=output_format,
        output_path=output_path,
        repos=repos,
        days=days,
    )

    # Optionally add verbose logging
    if verbose:
        pipeline.sink(ConsoleSink)

    # Handle diary entries if provided
    if diary_path:
        diary_pipeline = env.from_batch(
            DiaryEntrySource,
            diary_path=diary_path,
            days=days,
        ).map(ContributorAggregator)

        if use_llm:
            diary_pipeline = diary_pipeline.map(LLMReportGenerator, language=language)

        diary_pipeline.sink(
            ReportSink,
            output_format=output_format,
            output_path=output_path,
            repos=repos,
            days=days,
        )

    # Execute pipeline
    print(" Starting pipeline...")
    print()
    env.submit(autostop=True)

    return str(output_path) if output_path else None


def main():
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SAGE Work Report Generator - Generate weekly/daily work reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate report for all SAGE repositories (main + submodules)
  python -m sage.apps.work_report_generator.pipeline

  # Specify custom repositories
  python -m sage.apps.work_report_generator.pipeline \\
      --repos intellistream/SAGE,intellistream/sageLLM

  # Use different branch
  python -m sage.apps.work_report_generator.pipeline --branch main

  # Main repo only (without submodules)
  python -m sage.apps.work_report_generator.pipeline --no-submodules

  # Custom time range and output
  python -m sage.apps.work_report_generator.pipeline \\
      --days 14 \\
      --output reports/biweekly.md \\
      --format markdown

  # With diary entries
  python -m sage.apps.work_report_generator.pipeline \\
      --diary-path ./diaries \\
      --language zh

  # Skip LLM for faster generation
  python -m sage.apps.work_report_generator.pipeline --no-llm
        """,
    )

    parser.add_argument(
        "--repos",
        "-r",
        type=str,
        help="Comma-separated list of repositories (owner/repo format). "
        "If not specified, fetches from all SAGE repos including submodules.",
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
        help="Output file path",
    )

    parser.add_argument(
        "--diary-path",
        type=str,
        help="Path to diary directory or file",
    )

    parser.add_argument(
        "--language",
        "-l",
        type=str,
        choices=["zh", "en"],
        default="zh",
        help="Report language (default: zh)",
    )

    parser.add_argument(
        "--token",
        "-t",
        type=str,
        help="GitHub personal access token",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM summary generation",
    )

    parser.add_argument(
        "--no-submodules",
        action="store_true",
        help="Only fetch from main SAGE repo, skip submodules",
    )

    args = parser.parse_args()

    # Parse repositories
    repos = None
    if args.repos:
        repos = [r.strip() for r in args.repos.split(",")]

    # Run pipeline
    result = run_work_report_pipeline(
        repos=repos,
        days=args.days,
        branch=args.branch,
        output_format=args.format,
        output_path=args.output,
        diary_path=args.diary_path,
        language=args.language,
        github_token=args.token,
        verbose=args.verbose,
        use_llm=not args.no_llm,
        include_submodules=not args.no_submodules,
    )

    if result:
        print(f"\n Report generated: {result}")


if __name__ == "__main__":
    main()
