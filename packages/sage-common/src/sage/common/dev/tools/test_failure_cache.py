"""
Test Failure Cache Manager

This module provides functionality to cache failed test paths and enable
running only previously failed tests with the --failed option.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime
from ..utils.sage_home import get_logs_dir


class TestFailureCache:
    """Manages caching of failed test paths for quick re-execution."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        
        # Use .sage/test_logs directory for cache storage
        sage_dir = self.project_root / '.sage'
        self.cache_dir = sage_dir / 'test_logs'
        self.cache_file = self.cache_dir / 'failed_tests.json'
        
        # Ensure directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize cache data structure
        self._cache_data = {
            'last_updated': None,
            'failed_tests': [],
            'last_run_summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'execution_time': 0,
                'timestamp': None
            },
            'history': []  # Keep last 10 test run results
        }
        
        # Load existing cache
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from file if it exists."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Merge with default structure to handle schema changes
                    self._cache_data.update(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load test failure cache: {e}")
            # Keep default cache data
    
    def _save_cache(self) -> None:
        """Save cache to file."""
        try:
            # Update timestamp
            self._cache_data['last_updated'] = datetime.now().isoformat()
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Could not save test failure cache: {e}")
    
    def update_from_test_results(self, test_results: Dict) -> None:
        """Update cache with results from a test run."""
        try:
            # Extract failed test paths
            failed_tests = []
            
            if 'results' in test_results:
                for result in test_results['results']:
                    if not result.get('passed', True):
                        test_file = result.get('test_file')
                        if test_file:
                            # Store full path and simplified path
                            failed_tests.append({
                                'test_file': test_file,
                                'error': result.get('error', 'Unknown error'),
                                'duration': result.get('duration', 0),
                                'log_file': result.get('log_file'),
                                'failed_at': datetime.now().isoformat()
                            })
            
            # Update cache data
            self._cache_data['failed_tests'] = failed_tests
            
            # Update summary
            summary = test_results.get('summary', {})
            self._cache_data['last_run_summary'] = {
                'total': summary.get('total', 0),
                'passed': summary.get('passed', 0),
                'failed': summary.get('failed', 0),
                'execution_time': test_results.get('execution_time', 0),
                'timestamp': datetime.now().isoformat(),
                'mode': test_results.get('mode', 'unknown')
            }
            
            # Add to history (keep last 10)
            history_entry = {
                'timestamp': datetime.now().isoformat(),
                'summary': self._cache_data['last_run_summary'].copy(),
                'failed_count': len(failed_tests),
                'failed_tests': [f['test_file'] for f in failed_tests]
            }
            
            self._cache_data['history'].insert(0, history_entry)
            self._cache_data['history'] = self._cache_data['history'][:10]
            
            # Save to file
            self._save_cache()
            
            print(f"✅ Updated test failure cache: {len(failed_tests)} failed tests recorded")
            
        except Exception as e:
            print(f"Warning: Failed to update test failure cache: {e}")
    
    def get_failed_test_paths(self) -> List[str]:
        """Get list of test files that failed in the last run."""
        return [f['test_file'] for f in self._cache_data['failed_tests']]
    
    def get_failed_test_details(self) -> List[Dict]:
        """Get detailed information about failed tests."""
        return self._cache_data['failed_tests'].copy()
    
    def has_failed_tests(self) -> bool:
        """Check if there are any cached failed tests."""
        return len(self._cache_data['failed_tests']) > 0
    
    def clear_cache(self) -> None:
        """Clear the failed tests cache."""
        self._cache_data['failed_tests'] = []
        self._save_cache()
        print("✅ Cleared test failure cache")
    
    def get_cache_info(self) -> Dict:
        """Get information about the current cache state."""
        failed_count = len(self._cache_data['failed_tests'])
        last_updated = self._cache_data.get('last_updated')
        last_summary = self._cache_data.get('last_run_summary', {})
        
        return {
            'cache_file': str(self.cache_file),
            'failed_tests_count': failed_count,
            'last_updated': last_updated,
            'last_run_summary': last_summary,
            'has_failed_tests': failed_count > 0,
            'cache_exists': self.cache_file.exists()
        }
    
    def get_history(self, limit: int = 5) -> List[Dict]:
        """Get test run history."""
        return self._cache_data['history'][:limit]
    
    def resolve_test_paths(self, packages_dir: Path) -> List[Path]:
        """
        Resolve cached failed test paths to actual file paths.
        
        This handles cases where the cached paths might be simplified
        or the project structure changed.
        """
        failed_paths = self.get_failed_test_paths()
        resolved_paths = []
        
        for test_path in failed_paths:
            # Try to resolve the path
            resolved_path = self._resolve_single_test_path(test_path, packages_dir)
            if resolved_path:
                resolved_paths.append(resolved_path)
            else:
                print(f"Warning: Could not resolve cached test path: {test_path}")
        
        return resolved_paths
    
    def _resolve_single_test_path(self, test_path: str, packages_dir: Path) -> Optional[Path]:
        """Resolve a single test path to an actual file."""
        # If it's already an absolute path and exists
        if Path(test_path).is_absolute() and Path(test_path).exists():
            return Path(test_path)
        
        # Try as relative to project root
        project_relative = self.project_root / test_path
        if project_relative.exists():
            return project_relative
        
        # Try to find in packages directory structure
        # Handle simplified paths like "sage-kernel/tests/kernel/cli/test_job_new.py"
        if '/' in test_path:
            parts = test_path.split('/')
            
            # Look for package name in the path
            for i, part in enumerate(parts):
                # Try each part as a potential package name
                potential_package = packages_dir / part
                if potential_package.exists() and potential_package.is_dir():
                    # Reconstruct path from this package
                    remaining_path = '/'.join(parts[i+1:]) if i+1 < len(parts) else test_path
                    full_path = potential_package / remaining_path
                    if full_path.exists():
                        return full_path
        
        # Last resort: search for the file name in all packages
        file_name = Path(test_path).name
        if file_name.startswith('test_') and file_name.endswith('.py'):
            for package_dir in packages_dir.iterdir():
                if package_dir.is_dir() and not package_dir.name.startswith('.'):
                    found_files = list(package_dir.rglob(file_name))
                    if found_files:
                        # Return the first match (there might be multiple)
                        return found_files[0]
        
        return None
    
    def print_cache_status(self) -> None:
        """Print current cache status in a user-friendly format."""
        info = self.get_cache_info()
        
        print(f"📊 Test Failure Cache Status")
        print(f"   Cache file: {info['cache_file']}")
        print(f"   Failed tests: {info['failed_tests_count']}")
        
        if info['last_updated']:
            print(f"   Last updated: {info['last_updated']}")
        
        last_summary = info.get('last_run_summary', {})
        if last_summary.get('timestamp'):
            print(f"   Last run: {last_summary['total']} tests, "
                  f"{last_summary['passed']} passed, {last_summary['failed']} failed")
            print(f"   Execution time: {last_summary.get('execution_time', 0):.2f}s")
        
        if info['has_failed_tests']:
            print(f"\n   Use 'sage-dev test --failed' to re-run failed tests")
        else:
            print(f"\n   No failed tests cached")
