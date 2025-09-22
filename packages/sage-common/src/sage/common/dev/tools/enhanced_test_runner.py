"""
Enhanced Test Runner - Integrated from scripts/test_runner.py

This tool provides intelligent test execution with support for diff-based testing,
parallel execution, and comprehensive reporting.
"""

import os
import sys
import subprocess
import json
import time
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from ..core.exceptions import SAGEDevToolkitError
from ..utils.sage_home import get_logs_dir, get_reports_dir, setup_project_symlinks
from .test_failure_cache import TestFailureCache


class EnhancedTestRunner:
    """Enhanced test runner with intelligent change detection."""
    
    def __init__(self, project_root: str, enable_coverage: bool = False):
        self.project_root = Path(project_root)
        self.packages_dir = self.project_root / 'packages'
        self.enable_coverage = enable_coverage
        
        # Initialize test failure cache
        self.failure_cache = TestFailureCache(str(self.project_root))
        
        # Get project name from path
        project_name = self.project_root.name
        
        # Set up symlink to SAGE home
        setup_project_symlinks(self.project_root, project_name)
        
        # Use .sage subdirectories for all output
        sage_link = self.project_root / '.sage'
        self.test_logs_dir = sage_link / 'logs'
        self.reports_dir = sage_link / 'reports'
        
        # Check if pytest-benchmark is available
        self.has_benchmark = self._check_pytest_benchmark_available()
        
        # Ensure directories exist
        self.test_logs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _check_pytest_benchmark_available(self) -> bool:
        """Check if pytest-benchmark plugin is available."""
        try:
            import pytest_benchmark
            return True
        except ImportError:
            return False
    
    def run_tests(self, mode: str = 'diff', **kwargs) -> Dict:
        """Run tests based on specified mode."""
        try:
            print(f"\n🚀 Starting test run (mode: {mode})")
            
            if mode == 'all':
                result = self._run_all_tests(**kwargs)
            elif mode == 'diff':
                result = self._run_diff_tests(**kwargs)
            elif mode == 'package':
                package = kwargs.get('package')
                if not package:
                    raise SAGEDevToolkitError("Package name required for package mode")
                print(f"📦 Testing package: {package}")
                result = self._run_package_tests(package, **kwargs)
            elif mode == 'failed':
                result = self._run_failed_tests(**kwargs)
            else:
                raise SAGEDevToolkitError(f"Unknown test mode: {mode}")
            
            # Show final summary
            summary = result.get('summary', {})
            total = summary.get('total', 0)
            passed = summary.get('passed', 0)
            failed = summary.get('failed', 0)
            execution_time = result.get('execution_time', 0)
            
            print(f"\n📊 Test Summary:")
            print(f"   Total: {total}")
            print(f"   Passed: {passed} ✅")
            print(f"   Failed: {failed} ❌")
            print(f"   Duration: {execution_time:.2f}s")
            print(f"   Status: {'SUCCESS' if result.get('status') == 'success' else 'FAILED'}")
            
            # Update failure cache with results (except for failed mode to avoid recursion)
            if mode != 'failed':
                self.failure_cache.update_from_test_results(result)
            
            return result
                
        except Exception as e:
            raise SAGEDevToolkitError(f"Test execution failed: {e}")
    
    def _run_all_tests(self, **kwargs) -> Dict:
        """Run all tests in the project."""
        start_time = time.time()
        
        # Discover all test files
        test_files = self._discover_all_test_files()
        
        if not test_files:
            return {
                'mode': 'all',
                'test_files': [],
                'results': [],
                'summary': {'total': 0, 'passed': 0, 'failed': 0},
                'execution_time': 0,
                'status': 'success'
            }
        
        # Run tests
        results = self._execute_test_files(test_files, **kwargs)
        
        execution_time = time.time() - start_time
        
        return {
            'mode': 'all',
            'test_files': [self._simplify_test_path(f) for f in test_files],
            'results': results,
            'summary': self._calculate_summary(results),
            'execution_time': execution_time,
            'status': 'success' if all(r['passed'] for r in results) else 'failed'
        }
    
    def _run_diff_tests(self, base_branch: str = 'main', **kwargs) -> Dict:
        """Run tests for files affected by git diff."""
        start_time = time.time()
        
        # Get changed files
        changed_files = self._get_changed_files(base_branch)
        
        if not changed_files:
            return {
                'mode': 'diff',
                'base_branch': base_branch,
                'changed_files': [],
                'test_files': [],
                'results': [],
                'summary': {'total': 0, 'passed': 0, 'failed': 0},
                'execution_time': 0,
                'status': 'success'
            }
        
        # Find affected test files
        test_files = self._find_affected_test_files(changed_files)
        
        if not test_files:
            return {
                'mode': 'diff',
                'base_branch': base_branch,
                'changed_files': [str(f) for f in changed_files],
                'test_files': [],
                'results': [],
                'summary': {'total': 0, 'passed': 0, 'failed': 0},
                'execution_time': 0,
                'status': 'success'
            }
        
        # Run tests
        results = self._execute_test_files(test_files, **kwargs)
        
        execution_time = time.time() - start_time
        
        return {
            'mode': 'diff',
            'base_branch': base_branch,
            'changed_files': [str(f) for f in changed_files],
            'test_files': [self._simplify_test_path(f) for f in test_files],
            'results': results,
            'summary': self._calculate_summary(results),
            'execution_time': execution_time,
            'status': 'success' if all(r['passed'] for r in results) else 'failed'
        }
    
    def _run_package_tests(self, package_name: str, **kwargs) -> Dict:
        """Run tests for a specific package."""
        start_time = time.time()
        
        package_dir = self.packages_dir / package_name
        if not package_dir.exists():
            raise SAGEDevToolkitError(f"Package not found: {package_name}")
        
        # Find test files in package
        test_files = self._discover_package_test_files(package_dir)
        
        if not test_files:
            return {
                'mode': 'package',
                'package': package_name,
                'test_files': [],
                'results': [],
                'summary': {'total': 0, 'passed': 0, 'failed': 0},
                'execution_time': 0,
                'status': 'success'
            }
        
        # Run tests
        results = self._execute_test_files(test_files, **kwargs)
        
        execution_time = time.time() - start_time
        
        return {
            'mode': 'package',
            'package': package_name,
            'test_files': [self._simplify_test_path(f) for f in test_files],
            'results': results,
            'summary': self._calculate_summary(results),
            'execution_time': execution_time,
            'status': 'success' if all(r['passed'] for r in results) else 'failed'
        }
    
    def _run_failed_tests(self, **kwargs) -> Dict:
        """Run previously failed tests from cache."""
        start_time = time.time()
        
        # Check if there are cached failed tests
        if not self.failure_cache.has_failed_tests():
            return {
                'mode': 'failed',
                'test_files': [],
                'results': [],
                'summary': {'total': 0, 'passed': 0, 'failed': 0},
                'execution_time': 0,
                'status': 'success',
                'message': 'No failed tests found in cache'
            }
        
        # Get failed test paths and resolve them
        test_files = self.failure_cache.resolve_test_paths(self.packages_dir)
        
        if not test_files:
            return {
                'mode': 'failed',
                'cached_failed_count': len(self.failure_cache.get_failed_test_paths()),
                'test_files': [],
                'results': [],
                'summary': {'total': 0, 'passed': 0, 'failed': 0},
                'execution_time': 0,
                'status': 'success',
                'message': 'Cached failed tests could not be resolved to existing files'
            }
        
        # Run the resolved test files
        results = self._execute_test_files(test_files, **kwargs)
        
        execution_time = time.time() - start_time
        
        # Check if any previously failed tests now pass
        now_passing = [r for r in results if r['passed']]
        still_failing = [r for r in results if not r['passed']]
        
        return {
            'mode': 'failed',
            'cached_failed_count': len(self.failure_cache.get_failed_test_paths()),
            'resolved_test_count': len(test_files),
            'test_files': [self._simplify_test_path(f) for f in test_files],
            'results': results,
            'summary': self._calculate_summary(results),
            'execution_time': execution_time,
            'status': 'success' if all(r['passed'] for r in results) else 'failed',
            'now_passing_count': len(now_passing),
            'still_failing_count': len(still_failing)
        }
    
    def _simplify_test_path(self, test_file: Path) -> str:
        """Simplify test file path for display."""
        try:
            relative_path = test_file.relative_to(self.project_root)
            path_parts = relative_path.parts
            
            if 'packages' in path_parts and 'tests' in path_parts:
                # Find package name and tests part
                packages_idx = path_parts.index('packages')
                tests_idx = path_parts.index('tests')
                if packages_idx < tests_idx:
                    # Get the actual package name (could be multiple levels deep)
                    package_parts = path_parts[packages_idx + 1:tests_idx]
                    package_name = '/'.join(package_parts)
                    test_path_parts = path_parts[tests_idx:]
                    return f"{package_name}/{'/'.join(test_path_parts)}"
            
            return str(relative_path)
        except ValueError:
            return str(test_file)

    def _discover_all_test_files(self) -> List[Path]:
        """Discover all test files in the project."""
        test_files = []
        
        for package_dir in self.packages_dir.iterdir():
            if package_dir.is_dir() and not package_dir.name.startswith('.'):
                test_files.extend(self._discover_package_test_files(package_dir))
        
        return test_files
    
    def _discover_package_test_files(self, package_dir: Path) -> List[Path]:
        """Discover test files in a specific package."""
        test_files = []
        
        # Look for test directories
        for test_pattern in ['test', 'tests']:
            test_dir = package_dir / test_pattern
            if test_dir.exists():
                # Find all test_*.py files
                test_files.extend(test_dir.rglob('test_*.py'))
        
        # Also look for test files in the root of the package
        test_files.extend(package_dir.glob('test_*.py'))
        
        return test_files
    
    def _get_changed_files(self, base_branch: str) -> List[Path]:
        """Get files changed compared to base branch."""
        try:
            # Get changed files using git diff
            result = subprocess.run([
                'git', 'diff', '--name-only', f'{base_branch}...HEAD'
            ], capture_output=True, text=True, cwd=str(self.project_root))
            
            if result.returncode != 0:
                # Fallback to working directory changes
                result = subprocess.run([
                    'git', 'diff', '--name-only'
                ], capture_output=True, text=True, cwd=str(self.project_root))
            
            changed_files = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    file_path = self.project_root / line.strip()
                    if file_path.exists():
                        changed_files.append(file_path)
            
            return changed_files
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Failed to get changed files: {e}")
    
    def _find_affected_test_files(self, changed_files: List[Path]) -> List[Path]:
        """Find test files affected by changed files."""
        affected_packages = set()
        
        # Determine which packages are affected
        for changed_file in changed_files:
            try:
                relative_path = changed_file.relative_to(self.project_root)
                path_parts = relative_path.parts
                
                if len(path_parts) >= 2 and path_parts[0] == 'packages':
                    package_name = path_parts[1]
                    affected_packages.add(package_name)
            except ValueError:
                # File is not in packages directory
                continue
        
        # If no packages affected, run all tests
        if not affected_packages:
            return self._discover_all_test_files()
        
        # Find test files in affected packages
        test_files = []
        for package_name in affected_packages:
            package_dir = self.packages_dir / package_name
            if package_dir.exists():
                test_files.extend(self._discover_package_test_files(package_dir))
        
        return test_files
    
    def _execute_test_files(self, test_files: List[Path], **kwargs) -> List[Dict]:
        """Execute test files with optional parallel execution."""
        workers = kwargs.get('workers', 1)
        timeout = kwargs.get('timeout', 300)  # 5 minutes default
        quick = kwargs.get('quick', False)
        
        if workers and workers > 1:
            return self._execute_parallel(test_files, workers, timeout, quick)
        else:
            return self._execute_sequential(test_files, timeout, quick)
    
    def _execute_sequential(self, test_files: List[Path], timeout: int, quick: bool) -> List[Dict]:
        """Execute test files sequentially."""
        results = []
        total_tests = len(test_files)
        
        print(f"\n🧪 Running {total_tests} test files sequentially...")
        
        for i, test_file in enumerate(test_files, 1):
            print(f"[{i}/{total_tests}] Running: {self._simplify_test_path(test_file)}")
            result = self._run_single_test_file(test_file, timeout, quick)
            
            # Show immediate result
            status = "✅ PASSED" if result['passed'] else "❌ FAILED"
            duration = result.get('duration', 0)
            print(f"  {status} ({duration:.2f}s)")
            
            results.append(result)
            
            # Exit early on failure if quick mode
            if quick and not result['passed']:
                print(f"\n❌ Stopping on first failure (quick mode)")
                break
        
        return results
    
    def _execute_parallel(self, test_files: List[Path], workers: int, timeout: int, quick: bool) -> List[Dict]:
        """Execute test files in parallel."""
        results = []
        total_tests = len(test_files)
        completed = 0
        
        print(f"\n🧪 Running {total_tests} test files in parallel (workers: {workers})...")
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all test files
            future_to_file = {
                executor.submit(self._run_single_test_file, test_file, timeout, quick): test_file
                for test_file in test_files
            }
            
            # Collect results
            for future in as_completed(future_to_file):
                test_file = future_to_file[future]
                completed += 1
                
                try:
                    result = future.result()
                    status = "✅ PASSED" if result['passed'] else "❌ FAILED"
                    duration = result.get('duration', 0)
                    print(f"[{completed}/{total_tests}] {self._simplify_test_path(test_file)}: {status} ({duration:.2f}s)")
                    results.append(result)
                except Exception as e:
                    print(f"[{completed}/{total_tests}] {self._simplify_test_path(test_file)}: ❌ ERROR ({e})")
                    results.append({
                        'test_file': self._simplify_test_path(test_file),
                        'passed': False,
                        'duration': 0,
                        'output': '',
                        'error': str(e)
                    })
        
        return results
    
    def _get_package_from_test_file(self, test_file: Path) -> str:
        """Determine which package a test file belongs to."""
        try:
            relative_path = test_file.relative_to(self.packages_dir)
            path_parts = relative_path.parts
            
            if len(path_parts) >= 1:
                package_part = path_parts[0]
                # Map package directory names to standard log directory names
                package_mapping = {
                    'sage-kernel': 'kernel',
                    'sage-middleware': 'middleware', 
                    'sage-common': 'common',
                    'sage-libs': 'libs'
                }
                return package_mapping.get(package_part, 'common')  # Default to common
        except ValueError:
            # File is not in packages directory
            pass
        
        return 'common'  # Default fallback
    
    def _run_single_test_file(self, test_file: Path, timeout: int, quick: bool) -> Dict:
        """Run a single test file."""
        try:
            # Prepare command
            cmd = [sys.executable, '-m', 'pytest', str(test_file), '-v']
            
            if quick:
                cmd.extend(['-x'])  # Stop on first failure
            
            # If coverage is disabled, override any pyproject.toml coverage settings
            if not self.enable_coverage:
                cmd.extend(['--cov=', '--no-cov'])  # Explicitly disable coverage
            
            # Determine package and create appropriate log file path
            package_name = self._get_package_from_test_file(test_file)
            package_log_dir = self.test_logs_dir / package_name
            package_log_dir.mkdir(parents=True, exist_ok=True)
            log_file = package_log_dir / f"{test_file.name}.log"
            
            # Set up environment for test execution
            env = os.environ.copy()
            
            # Only add coverage if enabled
            if self.enable_coverage:
                # Set coverage data file to .sage directory
                coverage_dir = self.project_root / '.sage' / 'coverage'
                coverage_dir.mkdir(parents=True, exist_ok=True)
                coverage_file = coverage_dir / '.coverage'
                
                # Set up environment for coverage outputs
                env['COVERAGE_FILE'] = str(coverage_file)
                
                # Set coverage HTML output to .sage directory
                coverage_html_dir = coverage_dir / 'htmlcov'
                cmd.extend(['--cov-report=html:' + str(coverage_html_dir)])
                
                # Add explicit coverage source if needed
                # Note: pyproject.toml should have the coverage source settings
            
            # Run test
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.project_root),
                env=env
            )
            duration = time.time() - start_time
            
            # Write log file
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Command: {' '.join(cmd)}\n")
                f.write(f"Exit code: {result.returncode}\n")
                f.write(f"Duration: {duration:.2f}s\n")
                f.write(f"=== STDOUT ===\n{result.stdout}\n")
                f.write(f"=== STDERR ===\n{result.stderr}\n")
            
            return {
                'test_file': self._simplify_test_path(test_file),
                'passed': result.returncode == 0,
                'duration': duration,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None,
                'log_file': str(log_file)
            }
            
        except subprocess.TimeoutExpired:
            return {
                'test_file': self._simplify_test_path(test_file),
                'passed': False,
                'duration': timeout,
                'output': '',
                'error': f'Test timed out after {timeout} seconds'
            }
        except Exception as e:
            return {
                'test_file': self._simplify_test_path(test_file),
                'passed': False,
                'duration': 0,
                'output': '',
                'error': str(e)
            }
    
    def _calculate_summary(self, results: List[Dict]) -> Dict:
        """Calculate test summary statistics."""
        total = len(results)
        passed = sum(1 for r in results if r['passed'])
        failed = total - passed
        total_duration = sum(r['duration'] for r in results)
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'total_duration': total_duration,
            'average_duration': total_duration / total if total > 0 else 0
        }
    
    def list_tests(self) -> Dict:
        """List all available tests."""
        try:
            test_structure = {}
            
            for package_dir in self.packages_dir.iterdir():
                if package_dir.is_dir() and not package_dir.name.startswith('.'):
                    package_name = package_dir.name
                    test_files = self._discover_package_test_files(package_dir)
                    
                    if test_files:
                        test_structure[package_name] = [
                            self._simplify_test_path(f) for f in test_files
                        ]
            
            total_tests = sum(len(files) for files in test_structure.values())
            
            return {
                'test_structure': test_structure,
                'total_packages': len(test_structure),
                'total_test_files': total_tests,
                'status': 'success'
            }
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Test listing failed: {e}")
    
    def get_failure_cache_info(self) -> Dict:
        """Get information about the test failure cache."""
        return self.failure_cache.get_cache_info()
    
    def clear_failure_cache(self) -> None:
        """Clear the test failure cache."""
        self.failure_cache.clear_cache()
    
    def print_cache_status(self) -> None:
        """Print test failure cache status."""
        self.failure_cache.print_cache_status()
    
    def get_cache_history(self, limit: int = 5) -> List[Dict]:
        """Get test run history from cache."""
        return self.failure_cache.get_history(limit)
