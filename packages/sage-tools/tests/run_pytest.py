#!/usr/bin/env python3
"""
SAGE CLI Test Runner (pytest-based)

A comprehensive pytest-based test runner for SAGE CLI tools.
Provides organized test execution with multiple test categories and detailed reporting.
"""

import argparse
import subprocess
import sys


def run_pytest(
    test_pattern: str = ".",
    markers: list[str] | None = None,
    verbose: bool = True,
    capture: str = "no",
    coverage: bool = False,
    output_file: str | None = None,
    exitfirst: bool = False,
) -> int:
    """
    Run pytest with specified parameters.

    Args:
        test_pattern: Test pattern or directory to run
        markers: pytest markers to filter tests
        verbose: Enable verbose output
        capture: Capture mode ("no", "sys", "fd")
        coverage: Enable coverage reporting
        output_file: Output file for results
        exitfirst: Exit on first failure

    Returns:
        Exit code from pytest
    """
    cmd = ["python", "-m", "pytest"]

    # Add test pattern
    cmd.append(test_pattern)

    # Add verbosity
    if verbose:
        cmd.append("-v")

    # Add capture mode
    cmd.extend(["-s" if capture == "no" else f"--capture={capture}"])

    # Add markers
    if markers:
        for marker in markers:
            cmd.extend(["-m", marker])

    # Add coverage
    if coverage:
        cmd.extend(["--cov=sage.tools", "--cov-report=term-missing"])

    # Add output file
    if output_file:
        cmd.extend(["--junitxml", output_file])

    # Exit on first failure
    if exitfirst:
        cmd.append("-x")

    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="SAGE CLI Test Runner (pytest-based)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Categories:
  unit         - Unit tests (fast, isolated)
  integration  - Integration tests (slower, with real services)
  cli          - CLI command tests
  slow         - Long-running tests
  quick        - Quick smoke tests

Examples:
  python run_pytest.py                    # Run all tests
  python run_pytest.py --unit             # Run only unit tests
  python run_pytest.py --cli --verbose    # Run CLI tests with verbose output
  python run_pytest.py --pattern test_dev # Run tests in test_dev directory
  python run_pytest.py --coverage         # Run with coverage reporting
        """,
    )

    # Test selection
    parser.add_argument(
        "--pattern",
        "-p",
        default=".",
        help="Test pattern or directory to run (default: all tests)",
    )

    # Test categories
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests"
    )
    parser.add_argument("--cli", action="store_true", help="Run CLI tests")
    parser.add_argument("--slow", action="store_true", help="Run slow tests")
    parser.add_argument("--quick", action="store_true", help="Run quick tests")

    # Output options
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet output")
    parser.add_argument(
        "--capture",
        choices=["no", "sys", "fd"],
        default="no",
        help="Capture mode for output",
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Enable coverage reporting"
    )
    parser.add_argument("--output", "-o", help="Output file for results (JUnit XML)")

    # Special test runs
    parser.add_argument(
        "--failed", action="store_true", help="Run only failed tests from last run"
    )
    parser.add_argument(
        "--exitfirst", "-x", action="store_true", help="Exit on first failure"
    )

    args = parser.parse_args()

    # Build markers list
    markers = []
    if args.unit:
        markers.append("unit")
    if args.integration:
        markers.append("integration")
    if args.cli:
        markers.append("cli")
    if args.slow:
        markers.append("slow")
    if args.quick:
        markers.append("quick")

    # Special handling for failed tests
    if args.failed:
        cmd = ["python", "-m", "pytest", "--lf"]
        if args.verbose:
            cmd.append("-v")
        print(f"Running: {' '.join(cmd)}")
        return subprocess.run(cmd).returncode

    # Run pytest
    exit_code = run_pytest(
        test_pattern=args.pattern,
        markers=markers if markers else None,
        verbose=args.verbose and not args.quiet,
        capture=args.capture,
        coverage=args.coverage,
        output_file=args.output,
        exitfirst=args.exitfirst,
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
