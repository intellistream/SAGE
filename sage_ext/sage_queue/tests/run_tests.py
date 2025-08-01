#!/usr/bin/env python3
"""
Modern test runner for SAGE Queue tests using pytest
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Optional

# Add parent directory to path
current_dir = Path(__file__).parent
sage_queue_dir = current_dir.parent
sys.path.insert(0, str(sage_queue_dir))


class SageQueueTestRunner:
    """Modern test runner for SAGE Queue"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent.parent.parent.parent
        
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        try:
            import pytest
            print(f"✓ pytest {pytest.__version__} available")
        except ImportError:
            print("✗ pytest not available. Install with: pip install pytest")
            return False
        
        # Check for optional dependencies
        optional_deps = {
            'psutil': 'Performance monitoring',
            'ray': 'Ray integration tests', 
            'pytest-cov': 'Coverage reporting',
            'pytest-html': 'HTML reports',
            'pytest-xdist': 'Parallel execution'
        }
        
        for dep, description in optional_deps.items():
            try:
                __import__(dep.replace('-', '_'))
                print(f"✓ {dep} available ({description})")
            except ImportError:
                print(f"○ {dep} not available ({description}) - install with: pip install {dep}")
        
        return True
    
    def check_sage_queue(self) -> bool:
        """Check if SAGE Queue is available"""
        try:
            from sage_queue import SageQueue, SageQueueManager
            print("✓ SAGE Queue modules available")
            return True
        except ImportError as e:
            print(f"✗ SAGE Queue not available: {e}")
            print("Make sure the C library is compiled and Python modules are accessible")
            return False
    
    def run_quick_validation(self) -> bool:
        """Run quick validation tests"""
        print("\n" + "="*60)
        print("QUICK VALIDATION")
        print("="*60)
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir / "unit" / "test_basic_operations.py::TestSageQueueBasics::test_queue_creation"),
            "-v", "--tb=short"
        ]
        
        result = subprocess.run(cmd, cwd=self.test_dir)
        return result.returncode == 0
    
    def run_unit_tests(self, verbose: bool = True) -> bool:
        """Run unit tests"""
        print("\n" + "="*60)
        print("UNIT TESTS")
        print("="*60)
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir / "unit"),
            "-m", "unit"
        ]
        
        if verbose:
            cmd.extend(["-v", "--tb=short"])
        
        result = subprocess.run(cmd, cwd=self.test_dir)
        return result.returncode == 0
    
    def run_integration_tests(self, verbose: bool = True) -> bool:
        """Run integration tests"""
        print("\n" + "="*60)
        print("INTEGRATION TESTS")
        print("="*60)
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir / "integration"),
            "-m", "integration"
        ]
        
        if verbose:
            cmd.extend(["-v", "--tb=short"])
        
        result = subprocess.run(cmd, cwd=self.test_dir)
        return result.returncode == 0
    
    def run_performance_tests(self) -> bool:
        """运行性能测试"""
        print(f"\n⚡ Running SAGE Queue Performance Tests...")
        cmd = ["python", "-m", "pytest", "-m", "performance", "-v", "--tb=short"]
        return self._run_test_command(cmd, "Performance Tests")

    def run_stress_tests(self, subset: str = "all") -> bool:
        """
        运行压力测试
        
        Args:
            subset: 测试子集 ('all', 'multiprocess', 'lifecycle', 'memory')
        """
        print(f"\n🔥 Running SAGE Queue Stress Tests ({subset})...")
        
        # 压力测试命令映射
        stress_commands = {
            "all": ["-m", "stress", "-v", "--tb=short"],
            "multiprocess": ["-m", "stress", "-k", "multiprocess", "-v", "--tb=short"],
            "lifecycle": ["-m", "stress", "-k", "lifecycle", "-v", "--tb=short"],
            "memory": ["-m", "stress", "-k", "memory", "-v", "--tb=short"]
        }
        
        if subset not in stress_commands:
            print(f"❌ Unknown stress test subset: {subset}")
            return False
        
        cmd = ["python", "-m", "pytest"] + stress_commands[subset]
        return self._run_test_command(cmd, f"Stress Tests ({subset})")

    def run_lifecycle_tests(self) -> bool:
        """运行生命周期测试"""
        print(f"\n♻️  Running SAGE Queue Lifecycle Tests...")
        cmd = ["python", "-m", "pytest", "-m", "lifecycle", "-v", "--tb=short"]
        return self._run_test_command(cmd, "Lifecycle Tests")
    
    def run_all_tests(self, include_slow: bool = False, parallel: bool = False) -> bool:
        """Run all tests"""
        print("\n" + "="*60)
        print("ALL TESTS")
        print("="*60)
        
        cmd = [sys.executable, "-m", "pytest", str(self.test_dir)]
        
        if not include_slow:
            cmd.extend(["-m", "not slow"])
        
        if parallel:
            try:
                import xdist
                cmd.extend(["-n", "auto"])
                print("Running tests in parallel...")
            except ImportError:
                print("pytest-xdist not available, running sequentially")
        
        cmd.extend(["-v", "--tb=short"])
        
        result = subprocess.run(cmd, cwd=self.test_dir)
        return result.returncode == 0
    
    def run_with_coverage(self) -> bool:
        """Run tests with coverage reporting"""
        print("\n" + "="*60)
        print("TESTS WITH COVERAGE")
        print("="*60)
        
        try:
            import pytest_cov
        except ImportError:
            print("pytest-cov not available. Install with: pip install pytest-cov")
            return False
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "--cov=sage_queue",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "-v"
        ]
        
        result = subprocess.run(cmd, cwd=self.test_dir)
        
        if result.returncode == 0:
            print(f"\nCoverage HTML report generated: {self.test_dir}/htmlcov/index.html")
        
        return result.returncode == 0
    
    def run_custom_command(self, pytest_args: List[str]) -> bool:
        """Run custom pytest command"""
        print(f"\n" + "="*60)
        print(f"CUSTOM COMMAND: pytest {' '.join(pytest_args)}")
        print("="*60)
        
        cmd = [sys.executable, "-m", "pytest"] + pytest_args
        result = subprocess.run(cmd, cwd=self.test_dir)
        return result.returncode == 0
    
    def generate_html_report(self) -> bool:
        """Generate HTML test report"""
        try:
            import pytest_html
        except ImportError:
            print("pytest-html not available. Install with: pip install pytest-html")
            return False
        
        timestamp = int(time.time())
        report_file = self.test_dir / f"test_report_{timestamp}.html"
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            f"--html={report_file}",
            "--self-contained-html",
            "-v"
        ]
        
        result = subprocess.run(cmd, cwd=self.test_dir)
        
        if result.returncode == 0:
            print(f"\nHTML report generated: {report_file}")
        
        return result.returncode == 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="SAGE Queue Test Runner")
    parser.add_argument("--quick", action="store_true", help="Run quick validation only")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--stress", action="store_true", help="Run stress tests only")
    parser.add_argument("--lifecycle", action="store_true", help="Run lifecycle tests only")
    parser.add_argument("--stress-type", choices=['all', 'multiprocess', 'lifecycle', 'memory'], 
                       default='all', help="Type of stress tests to run")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage reporting")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--include-slow", action="store_true", help="Include slow tests")
    parser.add_argument("--check-deps", action="store_true", help="Check dependencies only")
    parser.add_argument("pytest_args", nargs="*", help="Additional pytest arguments")
    
    args = parser.parse_args()
    
    runner = SageQueueTestRunner()
    
    print("SAGE Queue Test Runner")
    print("="*60)
    
    # Check dependencies
    if not runner.check_dependencies():
        sys.exit(1)
    
    if args.check_deps:
        sys.exit(0)
    
    # Check SAGE Queue availability
    if not runner.check_sage_queue():
        print("\nSuggestions:")
        print("1. Compile the C library: cd .. && ./build.sh")
        print("2. Check PYTHONPATH includes the sage_queue directory")
        print("3. Verify all dependencies are installed")
        sys.exit(1)
    
    success = True
    
    # Run tests based on arguments
    if args.pytest_args:
        success = runner.run_custom_command(args.pytest_args)
    elif args.quick:
        success = runner.run_quick_validation()
    elif args.unit:
        success = runner.run_unit_tests()
    elif args.integration:
        success = runner.run_integration_tests()
    elif args.performance:
        success = runner.run_performance_tests()
    elif args.stress:
        success = runner.run_stress_tests(args.stress_type)
    elif args.lifecycle:
        success = runner.run_lifecycle_tests()
    elif args.coverage:
        success = runner.run_with_coverage()
    elif args.html:
        success = runner.generate_html_report()
    elif args.all:
        success = runner.run_all_tests(include_slow=args.include_slow, parallel=args.parallel)
    else:
        # Default: run unit and integration tests
        print("\nRunning default test suite (unit + integration)...")
        success = (
            runner.run_unit_tests() and 
            runner.run_integration_tests()
        )
    
    if success:
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("❌ SOME TESTS FAILED")
        print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()
