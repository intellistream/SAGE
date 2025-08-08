#!/usr/bin/env python3
"""
Test the failed test cache functionality with some simple test scenarios.
"""

import sys
import json
import tempfile
from pathlib import Path

# Add the sage-dev-toolkit to the path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sage_dev_toolkit.tools.test_failure_cache import TestFailureCache


def test_basic_cache_functionality():
    """Test basic cache operations."""
    print("🧪 Testing basic cache functionality...")
    
    # Create a temporary project directory
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        
        # Create cache
        cache = TestFailureCache(str(project_root))
        
        # Test cache info
        info = cache.get_cache_info()
        print(f"✅ Cache created: {info['cache_file']}")
        assert info['failed_tests_count'] == 0
        assert not info['has_failed_tests']
        
        # Create mock test results
        mock_results = {
            'mode': 'all',
            'execution_time': 15.5,
            'summary': {
                'total': 5,
                'passed': 3,
                'failed': 2
            },
            'results': [
                {
                    'test_file': 'packages/sage-kernel/tests/test_job.py',
                    'passed': True,
                    'duration': 2.5,
                    'log_file': '/path/to/test_job.py.log'
                },
                {
                    'test_file': 'packages/sage-kernel/tests/test_cli.py',
                    'passed': False,
                    'duration': 5.0,
                    'error': 'AssertionError: Expected True but got False',
                    'log_file': '/path/to/test_cli.py.log'
                },
                {
                    'test_file': 'packages/sage-tools/tests/test_manager.py',
                    'passed': True,
                    'duration': 3.2,
                    'log_file': '/path/to/test_manager.py.log'
                },
                {
                    'test_file': 'packages/sage-apps/tests/test_config.py',
                    'passed': False,
                    'duration': 4.8,
                    'error': 'ImportError: No module named something',
                    'log_file': '/path/to/test_config.py.log'
                },
                {
                    'test_file': 'packages/sage-middleware/tests/test_core.py',
                    'passed': True,
                    'duration': 1.0,
                    'log_file': '/path/to/test_core.py.log'
                }
            ]
        }
        
        # Update cache with results
        cache.update_from_test_results(mock_results)
        
        # Check updated cache
        info = cache.get_cache_info()
        assert info['failed_tests_count'] == 2
        assert info['has_failed_tests']
        
        # Get failed test paths
        failed_paths = cache.get_failed_test_paths()
        assert len(failed_paths) == 2
        assert 'packages/sage-kernel/tests/test_cli.py' in failed_paths
        assert 'packages/sage-apps/tests/test_config.py' in failed_paths
        
        # Get failed test details
        failed_details = cache.get_failed_test_details()
        assert len(failed_details) == 2
        assert any(d['test_file'] == 'packages/sage-kernel/tests/test_cli.py' for d in failed_details)
        
        # Test history
        history = cache.get_history()
        assert len(history) == 1
        assert history[0]['failed_count'] == 2
        
        print("✅ All basic cache tests passed!")


def test_cache_persistence():
    """Test that cache persists across instances."""
    print("🧪 Testing cache persistence...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        
        # Create first cache instance and add data
        cache1 = TestFailureCache(str(project_root))
        mock_results = {
            'mode': 'diff',
            'execution_time': 8.0,
            'summary': {'total': 2, 'passed': 1, 'failed': 1},
            'results': [
                {
                    'test_file': 'packages/test/test_persistence.py',
                    'passed': False,
                    'duration': 3.0,
                    'error': 'Some error',
                    'log_file': '/path/to/log'
                }
            ]
        }
        cache1.update_from_test_results(mock_results)
        
        # Create second cache instance (should load existing data)
        cache2 = TestFailureCache(str(project_root))
        
        # Check that data persisted
        failed_paths = cache2.get_failed_test_paths()
        assert len(failed_paths) == 1
        assert 'packages/test/test_persistence.py' in failed_paths
        
        info = cache2.get_cache_info()
        assert info['has_failed_tests']
        
        print("✅ Cache persistence test passed!")


def test_cache_clearing():
    """Test cache clearing functionality."""
    print("🧪 Testing cache clearing...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        
        cache = TestFailureCache(str(project_root))
        
        # Add some failed tests
        mock_results = {
            'summary': {'total': 1, 'passed': 0, 'failed': 1},
            'results': [
                {
                    'test_file': 'test_clear.py',
                    'passed': False,
                    'error': 'Error'
                }
            ]
        }
        cache.update_from_test_results(mock_results)
        
        # Verify cache has data
        assert cache.has_failed_tests()
        
        # Clear cache
        cache.clear_cache()
        
        # Verify cache is empty
        assert not cache.has_failed_tests()
        assert len(cache.get_failed_test_paths()) == 0
        
        print("✅ Cache clearing test passed!")


def main():
    """Run all tests."""
    print("🚀 Starting TestFailureCache tests...")
    
    try:
        test_basic_cache_functionality()
        test_cache_persistence()
        test_cache_clearing()
        
        print("\n🎉 All tests passed! The TestFailureCache is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
