#!/usr/bin/env python3
"""
Test runner for SAGE Core API tests

This script provides convenient ways to run the comprehensive test suite
for sage.core.api module with different configurations.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and handle the result"""
    print(f"\n{'='*60}")
    if description:
        print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, check=False, capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run SAGE Core API tests with various options"
    )
    
    # Test selection options
    parser.add_argument(
        '--file', '-f',
        help="Run specific test file (e.g., test_base_environment.py)"
    )
    parser.add_argument(
        '--class', '-c', dest='test_class',
        help="Run specific test class (e.g., TestBaseEnvironmentInit)"
    )
    parser.add_argument(
        '--method', '-m', dest='method',
        help="Run specific test method"
    )
    
    # Test type filters
    parser.add_argument(
        '--unit', action='store_true',
        help="Run only unit tests"
    )
    parser.add_argument(
        '--integration', action='store_true',
        help="Run only integration tests"
    )
    parser.add_argument(
        '--slow', action='store_true',
        help="Include slow tests"
    )
    
    # Output options
    parser.add_argument(
        '--coverage', action='store_true',
        help="Run with coverage analysis"
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help="Verbose output"
    )
    parser.add_argument(
        '--quiet', '-q', action='store_true',
        help="Quiet output"
    )
    
    # Additional options
    parser.add_argument(
        '--parallel', '-n', type=int,
        help="Run tests in parallel (specify number of processes)"
    )
    parser.add_argument(
        '--failfast', '-x', action='store_true',
        help="Stop on first failure"
    )
    
    args = parser.parse_args()
    
    # Base directory for tests
    test_dir = Path(__file__).parent
    
    # Build pytest command
    cmd = ['pytest']
    
    # Test selection
    if args.file:
        if args.test_class:
            if args.method:
                cmd.append(f"{test_dir}/{args.file}::{args.test_class}::{args.method}")
            else:
                cmd.append(f"{test_dir}/{args.file}::{args.test_class}")
        else:
            cmd.append(f"{test_dir}/{args.file}")
    elif args.test_class:
        cmd.extend(['-k', args.test_class])
    elif args.method:
        cmd.extend(['-k', args.method])
    else:
        cmd.append(str(test_dir))
    
    # Test type filters
    markers = []
    if args.unit:
        markers.append('unit')
    if args.integration:
        markers.append('integration')
    if args.slow:
        markers.append('slow')
    elif not args.unit and not args.integration:
        # Exclude slow tests by default unless specifically requested
        markers.append('not slow')
    
    if markers:
        cmd.extend(['-m', ' and '.join(markers)])
    
    # Output options
    if args.verbose:
        cmd.append('-v')
    elif args.quiet:
        cmd.append('-q')
    else:
        cmd.append('-v')  # Default to verbose
    
    # Coverage
    if args.coverage:
        cmd.extend([
            '--cov=sage.core.api',
            '--cov-report=html',
            '--cov-report=term-missing'
        ])
    
    # Additional options
    if args.parallel:
        cmd.extend(['-n', str(args.parallel)])
    
    if args.failfast:
        cmd.append('-x')
    
    # Always show local variables on failure for better debugging
    cmd.append('-l')
    
    # Run the tests
    success = run_command(cmd, "SAGE Core API Tests")
    
    if success:
        print("\n✅ All tests passed!")
        if args.coverage:
            print("📊 Coverage report generated in htmlcov/")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
