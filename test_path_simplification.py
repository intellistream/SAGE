#!/usr/bin/env python3
"""
Test script to verify path simplification functionality.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "packages/sage-tools/sage-dev-toolkit/src"))

from sage_dev_toolkit.tools.enhanced_test_runner import EnhancedTestRunner

def test_path_simplification():
    """Test the path simplification functionality."""
    
    # Create test runner with project root (coverage disabled by default)
    project_root = Path(__file__).parent
    runner = EnhancedTestRunner(str(project_root), enable_coverage=False)
    
    # Test cases
    test_cases = [
        # (input_path, expected_output)
        (project_root / "packages/sage-kernel/tests/cli/test_main.py", "sage-kernel/tests/cli/test_main.py"),
        (project_root / "packages/sage-middleware/tests/service/memory/test_memory_service.py", "sage-middleware/tests/service/memory/test_memory_service.py"),
        (project_root / "packages/sage-tools/sage-dev-toolkit/tests/test_basic.py", "sage-tools/sage-dev-toolkit/tests/test_basic.py"),
        (project_root / "other_location/test_something.py", "other_location/test_something.py")
    ]
    
    print("Testing path simplification:")
    print("=" * 60)
    
    all_passed = True
    for input_path, expected in test_cases:
        result = runner._simplify_test_path(input_path)
        passed = result == expected
        status = "✅ PASS" if passed else "❌ FAIL"
        
        print(f"{status} Input:    {input_path}")
        print(f"       Expected: {expected}")
        print(f"       Got:      {result}")
        print()
        
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    success = test_path_simplification()
    sys.exit(0 if success else 1)
