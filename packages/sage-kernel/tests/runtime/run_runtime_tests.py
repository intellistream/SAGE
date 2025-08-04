#!/usr/bin/env python3
"""
SAGE Runtime Test Runner

Comprehensive test runner for sage.runtime module with various test categories
and reporting options.

Usage:
    python run_runtime_tests.py [options]

Examples:
    # Run all tests
    python run_runtime_tests.py
    
    # Run only unit tests  
    python run_runtime_tests.py --unit
    
    # Run tests excluding slow ones
    python run_runtime_tests.py --fast
    
    # Run specific component tests
    python run_runtime_tests.py --component dispatcher
    python run_runtime_tests.py --component distributed
    
    # Run with coverage report
    python run_runtime_tests.py --coverage
    
    # Run in verbose mode
    python run_runtime_tests.py --verbose
"""

import argparse
import sys
import subprocess
import os
from pathlib import Path


def run_pytest(args_list):
    """Run pytest with given arguments"""
    cmd = [sys.executable, "-m", "pytest"] + args_list
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=Path(__file__).parent)


def main():
    parser = argparse.ArgumentParser(
        description="SAGE Runtime Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Test selection options
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument(
        "--unit", action="store_true",
        help="Run only unit tests (fast, isolated)"
    )
    test_group.add_argument(
        "--integration", action="store_true", 
        help="Run only integration tests"
    )
    test_group.add_argument(
        "--slow", action="store_true",
        help="Run only slow/performance tests"
    )
    test_group.add_argument(
        "--fast", action="store_true",
        help="Run tests excluding slow ones"
    )
    
    # Component-specific options
    parser.add_argument(
        "--component", choices=[
            "dispatcher", "context", "distributed", "factory", 
            "serialization", "communication", "service", "task", "state"
        ],
        help="Run tests for specific component only"
    )
    
    # Coverage options
    parser.add_argument(
        "--coverage", action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--no-cov", action="store_true",
        help="Disable coverage reporting"
    )
    
    # Output options
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", 
        help="Quiet output"
    )
    parser.add_argument(
        "--tb", choices=["short", "long", "line", "native"],
        default="short", help="Traceback format"
    )
    
    # Pytest pass-through options
    parser.add_argument(
        "--maxfail", type=int, default=None,
        help="Stop after N test failures"
    )
    parser.add_argument(
        "--pdb", action="store_true",
        help="Drop into PDB on test failures"
    )
    parser.add_argument(
        "--lf", action="store_true",
        help="Run last failed tests only"
    )
    parser.add_argument(
        "--ff", action="store_true", 
        help="Run failed tests first"
    )
    
    args = parser.parse_args()
    
    # Build pytest arguments
    pytest_args = []
    
    # Test path selection
    if args.component:
        if args.component in ["dispatcher", "context", "state"]:
            pytest_args.append(f"test_{args.component}.py")
        else:
            pytest_args.append(f"{args.component}/")
    else:
        pytest_args.append(".")
    
    # Test filtering
    if args.unit:
        pytest_args.extend(["-m", "unit"])
    elif args.integration:
        pytest_args.extend(["-m", "integration"])
    elif args.slow:
        pytest_args.extend(["-m", "slow"])
    elif args.fast:
        pytest_args.extend(["-m", "not slow"])
    
    # Coverage options
    if args.coverage and not args.no_cov:
        pytest_args.extend([
            "--cov=sage.runtime",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/runtime",
            "--cov-report=xml:coverage-runtime.xml",
            "--cov-branch"
        ])
    elif args.no_cov:
        pytest_args.append("--no-cov")
    
    # Output options
    if args.verbose:
        pytest_args.append("-v")
    elif args.quiet:
        pytest_args.append("-q")
    
    pytest_args.extend(["--tb", args.tb])
    
    # Additional options
    if args.maxfail:
        pytest_args.extend(["--maxfail", str(args.maxfail)])
    if args.pdb:
        pytest_args.append("--pdb")
    if args.lf:
        pytest_args.append("--lf")
    if args.ff:
        pytest_args.append("--ff")
    
    # Always include strict markers and config
    pytest_args.extend(["--strict-markers", "--strict-config"])
    
    # Run tests
    result = run_pytest(pytest_args)
    
    # Print summary
    if result.returncode == 0:
        print("\n✅ All tests passed!")
        if args.coverage and not args.no_cov:
            print("📊 Coverage report available in htmlcov/runtime/index.html")
    else:
        print(f"\n❌ Tests failed with return code {result.returncode}")
    
    return result.returncode


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
