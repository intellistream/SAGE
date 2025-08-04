#!/usr/bin/env python3
"""
Comprehensive test runner for SAGE CLI modules.
Runs all CLI tests and provides detailed reporting.
"""

import unittest
import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

def discover_and_run_tests():
    """Discover and run all CLI tests."""
    
    # Get the directory containing this script
    test_dir = Path(__file__).parent
    
    # Test files to run
    test_files = [
        'test_setup_simple.py',
        'test_config_manager_simple.py', 
        'test_head_manager_simple.py',
        'test_worker_manager_simple.py',
        'test_job_simple.py',
        'test_deploy_simple.py',
        'test_cluster_manager_simple.py',
        'test_extensions_simple.py',
        'test_main_simple.py'
    ]
    
    print("=" * 80)
    print("SAGE CLI Test Suite")
    print("=" * 80)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Load tests from each file
    for test_file in test_files:
        test_path = test_dir / test_file
        if test_path.exists():
            try:
                # Import the test module
                module_name = test_file[:-3]  # Remove .py extension
                spec = unittest.util.spec_from_file_location(module_name, test_path)
                module = unittest.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Add tests from the module
                test_suite = loader.loadTestsFromModule(module)
                suite.addTests(test_suite)
                print(f"✓ Loaded tests from {test_file}")
                
            except Exception as e:
                print(f"✗ Failed to load tests from {test_file}: {e}")
        else:
            print(f"✗ Test file not found: {test_file}")
    
    print("-" * 80)
    
    # Run the tests
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=True
    )
    
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.splitlines()[-1] if traceback else 'Unknown failure'}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.splitlines()[-1] if traceback else 'Unknown error'}")
    
    if result.skipped:
        print(f"\nSKIPPED ({len(result.skipped)}):")
        for test, reason in result.skipped:
            print(f"- {test}: {reason}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / max(result.testsRun, 1) * 100
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = discover_and_run_tests()
    sys.exit(0 if success else 1)
