#!/usr/bin/env python3
"""
PEP 420 Namespace Package Integration Test

Tests that multiple sage.* packages can coexist without namespace hijacking.
This is a critical test for multi-repo compatibility.

Usage:
    python3 tools/scripts/test_pep420_integration.py

Exit codes:
    0 - All tests passed
    1 - Test failures detected
"""

import sys
import importlib
from typing import List, Tuple


def test_namespace_is_implicit() -> bool:
    """Test that sage namespace is implicit (no __file__)."""
    print("\n1. Testing sage namespace is implicit...")
    try:
        import sage
        file = getattr(sage, '__file__', None)
        if file is None:
            print("   ✅ sage.__file__ is None (implicit namespace)")
            return True
        else:
            print(f"   ❌ sage.__file__ = {file} (should be None)")
            return False
    except ImportError as e:
        print(f"   ✅ ImportError (also valid for PEP 420): {e}")
        return True


def test_subpackages_import() -> Tuple[bool, List[str]]:
    """Test that all sage sub-packages can be imported."""
    print("\n2. Testing sub-package imports...")
    
    # Core packages (must exist)
    core_packages = [
        'sage.common',
        'sage.llm',
        'sage.platform',
        'sage.kernel',
        'sage.libs',
        'sage.middleware',
    ]
    
    # Optional packages (L5-L6)
    optional_packages = [
        'sage.apps',
        'sage.benchmark',
        'sage.cli',
        'sage.studio',
        'sage.llm.gateway',
        'sage.edge',
        'sage.tools',
    ]
    
    all_packages = core_packages + optional_packages
    success = True
    failed = []
    
    for pkg in all_packages:
        try:
            mod = importlib.import_module(pkg)
            version = getattr(mod, '__version__', 'no version')
            print(f"   ✅ {pkg:20s} v{version}")
        except ImportError as e:
            if pkg in core_packages:
                print(f"   ❌ {pkg:20s} FAILED (core package): {e}")
                success = False
                failed.append(pkg)
            else:
                print(f"   ⚠️  {pkg:20s} Not installed (optional)")
    
    return success, failed


def test_no_namespace_hijacking() -> bool:
    """Test that no __init__.py hijacks the sage namespace."""
    print("\n3. Testing for namespace hijacking...")
    
    import os
    import sys
    
    hijacked = False
    for path in sys.path:
        sage_init = os.path.join(path, 'sage', '__init__.py')
        if os.path.exists(sage_init):
            # Read file to check if it's empty or docstring-only
            with open(sage_init, 'r') as f:
                content = f.read().strip()
                # Check if it contains actual code (not just docstring/comments)
                lines = [l.strip() for l in content.split('\n') 
                        if l.strip() and not l.strip().startswith('#')]
                
                # Filter out docstrings (triple quotes)
                code_lines = []
                in_docstring = False
                for line in lines:
                    if '"""' in line or "'''" in line:
                        in_docstring = not in_docstring
                    elif not in_docstring:
                        code_lines.append(line)
                
                if code_lines:
                    print(f"   ⚠️  Found __init__.py with code: {sage_init}")
                    print(f"      Code lines: {code_lines[:3]}")
                    hijacked = True
    
    if not hijacked:
        print("   ✅ No namespace hijacking detected")
        return True
    else:
        print("   ❌ Namespace hijacking detected")
        return False


def test_cross_package_compatibility() -> bool:
    """Test that packages from different sources coexist."""
    print("\n4. Testing cross-package compatibility...")
    
    try:
        # Import from different packages (use actual exports)
        import sage.common
        import sage.kernel
        
        # Test actual functionality exists
        assert hasattr(sage.common, '__version__')
        assert hasattr(sage.kernel, '__version__')
        
        # If sage.benchmark is installed, test it too
        try:
            import sage.benchmark
            assert hasattr(sage.benchmark, '__version__')
            print("   ✅ sage.common + sage.kernel + sage.benchmark coexist")
        except ImportError:
            print("   ✅ sage.common + sage.kernel coexist")
        
        return True
        
    except (ImportError, AssertionError) as e:
        print(f"   ❌ Cross-package compatibility failed: {e}")
        return False


def main() -> int:
    """Run all PEP 420 integration tests."""
    print("=" * 70)
    print("🧪 PEP 420 Namespace Package Integration Test")
    print("=" * 70)
    
    results = {
        'namespace_implicit': test_namespace_is_implicit(),
        'subpackages_import': test_subpackages_import()[0],
        'no_hijacking': test_no_namespace_hijacking(),
        'cross_package': test_cross_package_compatibility(),
    }
    
    print("\n" + "=" * 70)
    print("📊 Test Results:")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {test_name}")
    
    all_passed = all(results.values())
    
    print()
    if all_passed:
        print("✅ All PEP 420 integration tests passed!")
        return 0
    else:
        print("❌ Some PEP 420 integration tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
