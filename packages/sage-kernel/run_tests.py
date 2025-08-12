#!/usr/bin/env python3
"""
SAGE Kernel Test Runner

Comprehensive test runner for the sage-kernel package with support for different
test categories, parallel execution, coverage reporting, and selective test execution.

Usage:
    python run_tests.py [options]

Examples:
    # Run all tests
    python run_tests.py
    
    # Run only unit tests  
    python run_tests.py --unit
    
    # Run tests excluding slow ones
    python run_tests.py --fast
    
    # Run specific component tests
    python run_tests.py --component core
    python run_tests.py --component runtime
    python run_tests.py --component jobmanager
    
    # Run with coverage report
    python run_tests.py --coverage
    
    # Run in parallel
    python run_tests.py --parallel
    
    # Run with verbose output
    python run_tests.py --verbose
    
    # Stop on first failure
    python run_tests.py --fail-fast
    
    # Run last failed tests only
    python run_tests.py --lf
"""

import argparse
import sys
import subprocess
import os
import time
from pathlib import Path
from typing import List, Optional


class SAGEKernelTestRunner:
    """Test runner for SAGE Kernel package"""
    
    def __init__(self, kernel_root: Path):
        self.kernel_root = kernel_root
        self.tests_dir = kernel_root / "tests"
        
        # Find project root (should contain .sage directory)
        self.project_root = kernel_root
        while self.project_root.parent != self.project_root:
            if (self.project_root / '.sage').exists() or (self.project_root / 'packages').exists():
                break
            self.project_root = self.project_root.parent
        
        # Use unified logging directory
        self.logs_dir = self.project_root / '.sage' / 'logs' / 'kernel'
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
    def run_pytest(self, args_list: List[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """Run pytest with given arguments"""
        cmd = [sys.executable, "-m", "pytest"] + args_list
        print(f"Running: {' '.join(cmd)}")
        print(f"Working directory: {self.kernel_root}")
        print("-" * 80)
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd, 
                cwd=self.kernel_root,
                timeout=timeout
            )
            execution_time = time.time() - start_time
            print(f"\nExecution time: {execution_time:.2f}s")
            return result
        except subprocess.TimeoutExpired:
            print(f"\nTests timed out after {timeout}s")
            return subprocess.CompletedProcess(cmd, returncode=124)
    
    def get_component_paths(self, component: str) -> List[str]:
        """Get test paths for specific component"""
        component_paths = {
            "core": ["tests/unit/core/"],
            "runtime": ["tests/unit/kernel/runtime/"],
            "jobmanager": ["tests/unit/kernel/jobmanager/"],
            "utils": ["tests/unit/kernel/utils/"],
            "enterprise": ["tests/unit/kernel/enterprise/"] if (self.tests_dir / "unit/kernel/enterprise").exists() else [],
            "integration": ["tests/integration/"] if (self.tests_dir / "integration").exists() else [],
            "all": ["tests/"]
        }
        
        # Filter out non-existent paths
        valid_paths = []
        for path in component_paths.get(component, []):
            full_path = self.kernel_root / path
            if full_path.exists():
                valid_paths.append(path)
        
        return valid_paths
    
    def check_test_structure(self) -> bool:
        """Check if test structure is complete"""
        print("Checking SAGE Kernel test structure...")
        print("=" * 60)
        
        required_components = [
            ("tests/unit/core/", "Core module tests"),
            ("tests/unit/kernel/runtime/", "Runtime module tests"),
            ("tests/unit/kernel/jobmanager/", "Job manager tests"),
            ("tests/unit/kernel/utils/", "Utils module tests"),
            ("tests/conftest.py", "Test configuration"),
            ("pytest.ini", "Pytest configuration")
        ]
        
        missing_components = []
        existing_components = []
        
        for component_path, description in required_components:
            full_path = self.kernel_root / component_path
            if full_path.exists():
                existing_components.append((component_path, description))
                print(f"✓ {component_path} - {description}")
            else:
                missing_components.append((component_path, description))
                print(f"✗ {component_path} - {description} (MISSING)")
        
        print("\n" + "=" * 60)
        print(f"Structure Summary:")
        print(f"Existing: {len(existing_components)}")
        print(f"Missing: {len(missing_components)}")
        
        if missing_components:
            print("\nMissing components:")
            for component_path, description in missing_components:
                print(f"  - {component_path}")
            return False
        else:
            print("\n✓ All required components are present!")
            return True
    
    def list_available_tests(self):
        """List all available test files"""
        print("Available test files in SAGE Kernel:")
        print("=" * 60)
        
        if not self.tests_dir.exists():
            print("No tests directory found!")
            return
        
        test_files = list(self.tests_dir.rglob("test_*.py"))
        
        # Group by component
        components = {}
        for test_file in test_files:
            try:
                relative_path = test_file.relative_to(self.tests_dir)
                parts = relative_path.parts
                
                if len(parts) >= 2:
                    component = parts[1]  # unit/core, unit/kernel, etc.
                    if component not in components:
                        components[component] = []
                    components[component].append(str(relative_path))
            except ValueError:
                continue
        
        for component, files in sorted(components.items()):
            print(f"\n{component.upper()}:")
            for file_path in sorted(files):
                print(f"  - {file_path}")
        
        print(f"\nTotal test files: {len(test_files)}")
    
    def run_component_tests(self, component: str, **kwargs) -> int:
        """Run tests for a specific component"""
        paths = self.get_component_paths(component)
        
        if not paths:
            print(f"No test paths found for component: {component}")
            print("Available components: core, runtime, jobmanager, utils, enterprise, integration, all")
            return 1
        
        # Build pytest arguments
        pytest_args = []
        
        # Add test paths
        pytest_args.extend(paths)
        
        return self._run_with_options(pytest_args, **kwargs)
    
    def _run_with_options(self, base_args: List[str], **kwargs) -> int:
        """Run pytest with various options"""
        pytest_args = base_args.copy()
        
        # Test filtering
        if kwargs.get('unit'):
            pytest_args.extend(["-m", "unit"])
        elif kwargs.get('integration'):
            pytest_args.extend(["-m", "integration"])
        elif kwargs.get('slow'):
            pytest_args.extend(["-m", "slow"])
        elif kwargs.get('fast'):
            pytest_args.extend(["-m", "not slow"])
        elif kwargs.get('ray'):
            pytest_args.extend(["-m", "ray"])
        elif kwargs.get('distributed'):
            pytest_args.extend(["-m", "distributed"])
        elif kwargs.get('performance'):
            pytest_args.extend(["-m", "performance"])
        
        # Coverage options
        if kwargs.get('coverage') and not kwargs.get('no_cov'):
            pytest_args.extend([
                "--cov=src/sage/kernel",
                "--cov=src/sage/core", 
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov/kernel",
                "--cov-report=xml:coverage-kernel.xml",
                "--cov-branch"
            ])
        elif kwargs.get('no_cov'):
            pytest_args.extend(["--cov=", "--no-cov"])
        
        # Output options
        if kwargs.get('verbose'):
            pytest_args.append("-v")
        elif kwargs.get('quiet'):
            pytest_args.append("-q")
        
        # Execution options
        if kwargs.get('fail_fast'):
            pytest_args.append("-x")
        
        if kwargs.get('parallel'):
            # Check if pytest-xdist is available
            try:
                import xdist
                pytest_args.extend(["-n", "auto"])
            except ImportError:
                print("Warning: pytest-xdist not available, running sequentially")
        
        # Pytest built-in options
        if kwargs.get('lf'):
            pytest_args.append("--lf")
        if kwargs.get('ff'):
            pytest_args.append("--ff")
        if kwargs.get('pdb'):
            pytest_args.append("--pdb")
        
        if kwargs.get('maxfail'):
            pytest_args.extend(["--maxfail", str(kwargs['maxfail'])])
        
        # Traceback format
        tb_format = kwargs.get('tb', 'short')
        pytest_args.extend(["--tb", tb_format])
        
        # Always include strict options
        pytest_args.extend(["--strict-markers", "--strict-config"])
        
        # Add result summary
        pytest_args.append("-ra")
        
        # Run tests
        timeout = kwargs.get('timeout')
        result = self.run_pytest(pytest_args, timeout=timeout)
        return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="SAGE Kernel Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Find kernel root
    kernel_root = Path(__file__).parent
    runner = SAGEKernelTestRunner(kernel_root)
    
    # Test selection options
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument(
        "--unit", action="store_true",
        help="Run only unit tests"
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
    test_group.add_argument(
        "--ray", action="store_true",
        help="Run only Ray-related tests"
    )
    test_group.add_argument(
        "--distributed", action="store_true",
        help="Run only distributed tests"
    )
    test_group.add_argument(
        "--performance", action="store_true",
        help="Run only performance benchmark tests"
    )
    
    # Component selection
    parser.add_argument(
        "--component", choices=[
            "core", "runtime", "jobmanager", "utils", "enterprise", "integration", "all"
        ],
        help="Run tests for specific component only"
    )
    
    # Coverage options
    coverage_group = parser.add_mutually_exclusive_group()
    coverage_group.add_argument(
        "--coverage", action="store_true",
        help="Generate coverage report"
    )
    coverage_group.add_argument(
        "--no-cov", action="store_true",
        help="Disable coverage reporting"
    )
    
    # Output options
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )
    output_group.add_argument(
        "--quiet", "-q", action="store_true", 
        help="Quiet output"
    )
    
    parser.add_argument(
        "--tb", choices=["short", "long", "line", "native"],
        default="short", help="Traceback format"
    )
    
    # Execution options
    parser.add_argument(
        "--parallel", action="store_true",
        help="Run tests in parallel (requires pytest-xdist)"
    )
    parser.add_argument(
        "--fail-fast", "-x", action="store_true",
        help="Stop on first failure"
    )
    parser.add_argument(
        "--timeout", type=int,
        help="Timeout for entire test run in seconds"
    )
    
    # Pytest pass-through options
    parser.add_argument(
        "--maxfail", type=int,
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
    
    # Utility options
    parser.add_argument(
        "--check-structure", action="store_true",
        help="Check test structure completeness"
    )
    parser.add_argument(
        "--list-tests", action="store_true",
        help="List all available test files"
    )
    
    args = parser.parse_args()
    
    # Handle utility commands
    if args.check_structure:
        success = runner.check_test_structure()
        return 0 if success else 1
    
    if args.list_tests:
        runner.list_available_tests()
        return 0
    
    # Convert args to kwargs
    kwargs = {
        'unit': args.unit,
        'integration': args.integration,
        'slow': args.slow,
        'fast': args.fast,
        'ray': args.ray,
        'distributed': args.distributed,
        'performance': args.performance,
        'coverage': args.coverage,
        'no_cov': args.no_cov,
        'verbose': args.verbose,
        'quiet': args.quiet,
        'tb': args.tb,
        'parallel': args.parallel,
        'fail_fast': args.fail_fast,
        'timeout': args.timeout,
        'maxfail': args.maxfail,
        'pdb': args.pdb,
        'lf': args.lf,
        'ff': args.ff
    }
    
    # Run tests
    if args.component:
        exit_code = runner.run_component_tests(args.component, **kwargs)
    else:
        # Run all tests
        exit_code = runner.run_component_tests("all", **kwargs)
    
    # Print summary
    if exit_code == 0:
        print("\n✅ All tests passed!")
        if args.coverage and not args.no_cov:
            print("📊 Coverage report available in htmlcov/kernel/index.html")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
