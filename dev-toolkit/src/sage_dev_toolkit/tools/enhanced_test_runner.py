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
from pathlib import Path
from typing import Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from ..core.exceptions import SAGEDevToolkitError


class EnhancedTestRunner:
    """Enhanced test runner with intelligent change detection."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.packages_dir = self.project_root / 'packages'
        self.test_logs_dir = self.project_root / 'test_logs'
        self.reports_dir = self.project_root / 'dev_reports'
        
        # Ensure directories exist
        self.test_logs_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
    
    def run_tests(self, mode: str = 'diff', **kwargs) -> Dict:
        """Run tests based on specified mode."""
        try:
            if mode == 'all':
                return self._run_all_tests(**kwargs)
            elif mode == 'diff':
                return self._run_diff_tests(**kwargs)
            elif mode == 'package':
                package = kwargs.get('package')
                if not package:
                    raise SAGEDevToolkitError("Package name required for package mode")
                return self._run_package_tests(package, **kwargs)
            else:
                raise SAGEDevToolkitError(f"Unknown test mode: {mode}")
                
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
            'test_files': [str(f) for f in test_files],
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
            'test_files': [str(f) for f in test_files],
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
            'test_files': [str(f) for f in test_files],
            'results': results,
            'summary': self._calculate_summary(results),
            'execution_time': execution_time,
            'status': 'success' if all(r['passed'] for r in results) else 'failed'
        }
    
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
        
        for test_file in test_files:
            result = self._run_single_test_file(test_file, timeout, quick)
            results.append(result)
        
        return results
    
    def _execute_parallel(self, test_files: List[Path], workers: int, timeout: int, quick: bool) -> List[Dict]:
        """Execute test files in parallel."""
        results = []
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all test files
            future_to_file = {
                executor.submit(self._run_single_test_file, test_file, timeout, quick): test_file
                for test_file in test_files
            }
            
            # Collect results
            for future in as_completed(future_to_file):
                test_file = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        'test_file': str(test_file),
                        'passed': False,
                        'duration': 0,
                        'output': '',
                        'error': str(e)
                    })
        
        return results
    
    def _run_single_test_file(self, test_file: Path, timeout: int, quick: bool) -> Dict:
        """Run a single test file."""
        try:
            # Prepare command
            cmd = [sys.executable, '-m', 'pytest', str(test_file), '-v']
            
            if quick:
                cmd.extend(['-x'])  # Stop on first failure
            
            # Create log file path
            relative_path = test_file.relative_to(self.project_root)
            log_file = self.test_logs_dir / f"{str(relative_path).replace('/', '_')}.log"
            
            # Run test
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.project_root)
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
                'test_file': str(test_file),
                'passed': result.returncode == 0,
                'duration': duration,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None,
                'log_file': str(log_file)
            }
            
        except subprocess.TimeoutExpired:
            return {
                'test_file': str(test_file),
                'passed': False,
                'duration': timeout,
                'output': '',
                'error': f'Test timed out after {timeout} seconds'
            }
        except Exception as e:
            return {
                'test_file': str(test_file),
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
                            str(f.relative_to(self.project_root)) for f in test_files
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
