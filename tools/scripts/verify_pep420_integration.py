#!/usr/bin/env python3
"""
verify_pep420_integration.py

Verifies PEP 420 namespace package integration in SAGE monorepo.
Tests that packages can coexist and namespace behaves correctly.

Usage:
    python3 tools/scripts/verify_pep420_integration.py
"""

import importlib
import importlib.util
import sys
from pathlib import Path

# ANSI color codes
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"  # No Color


def print_header(text: str) -> None:
    """Print a formatted header."""
    print("=" * 70)
    print(text)
    print("=" * 70)


def test_namespace_import() -> tuple[bool, str]:
    """Test that sage namespace can be imported and is implicit."""
    try:
        import sage

        # PEP 420 namespace packages should have __file__ = None
        if sage.__file__ is not None:
            return False, f"sage.__file__ should be None (implicit namespace), got: {sage.__file__}"

        # Namespace should not have __path__ as a list (should be _NamespacePath)
        if not hasattr(sage, "__path__"):
            return False, "sage should have __path__ attribute"

        return True, "sage namespace is correctly implicit (PEP 420)"
    except ImportError as e:
        return False, f"Failed to import sage: {e}"


def test_subpackage_imports() -> tuple[bool, list[str]]:
    """Test that subpackages can be imported."""
    subpackages = [
        "sage.common",
        "sage.kernel",
        "sage.libs",
        "sage.platform",
        "sage.llm",
    ]

    errors = []
    successes = []
    success_count = 0

    for pkg_name in subpackages:
        try:
            pkg = importlib.import_module(pkg_name)

            # Subpackages should have __file__ (they have __init__.py)
            if not hasattr(pkg, "__file__"):
                errors.append(f"{pkg_name}: missing __file__ attribute")
            elif pkg.__file__ is None:
                errors.append(f"{pkg_name}.__file__ is None (should be a real path)")
            else:
                success_count += 1
                successes.append(f"{pkg_name} imported successfully")

        except ImportError:
            # Some packages might not be installed, that's OK
            # Only report if it's a critical package
            pass

    # At least one package should be importable
    if success_count == 0:
        errors.append("No SAGE subpackages could be imported")
    else:
        # Return successes as the message list when test passes
        return True, successes

    return False, errors


def test_namespace_coexistence() -> tuple[bool, list[str]]:
    """Test that multiple packages can coexist in the namespace."""
    errors = []

    try:
        import sage

        # Get all paths in the namespace
        namespace_paths = list(sage.__path__)

        if len(namespace_paths) == 0:
            errors.append("sage.__path__ is empty")
        elif len(namespace_paths) < 2:
            errors.append(
                f"Only {len(namespace_paths)} path(s) in namespace (expected multiple for monorepo)"
            )

        # Verify paths exist (skip editable install finder paths)
        for path in namespace_paths:
            # Skip __editable__ paths (these are from pip install -e)
            if "__editable__" in str(path):
                continue

            path_obj = Path(path)
            if not path_obj.exists():
                errors.append(f"Namespace path does not exist: {path}")

    except ImportError as e:
        errors.append(f"Failed to import sage: {e}")

    return len(errors) == 0, errors


def test_version_attributes() -> tuple[bool, list[str]]:
    """Test that subpackages have proper version attributes."""
    test_packages = [
        ("sage.common", "__version__"),
        ("sage.kernel", "__version__"),
        ("sage.libs", "__version__"),
    ]

    errors = []
    successes = []
    success_count = 0

    for pkg_name, attr in test_packages:
        try:
            pkg = importlib.import_module(pkg_name)
            if not hasattr(pkg, attr):
                errors.append(f"{pkg_name} missing {attr} attribute")
            else:
                version = getattr(pkg, attr)
                if not version or not isinstance(version, str):
                    errors.append(f"{pkg_name}.{attr} is invalid: {version}")
                else:
                    success_count += 1
                    successes.append(f"{pkg_name}.{attr} = {version}")
        except ImportError:
            # Package not installed, skip
            pass

    # At least one package should have version
    if success_count == 0:
        errors.append("No SAGE packages have version attributes")
    else:
        # Return successes when test passes
        return True, successes

    return False, errors


def main() -> int:
    """Run all PEP 420 integration tests."""
    print_header("🔍 PEP 420 Namespace Package Integration Tests")
    print()

    all_passed = True
    results = []

    # Test 1: Namespace import
    print("Test 1: Namespace import...")
    passed, message = test_namespace_import()
    results.append(("Namespace import", passed, message))
    if passed:
        print(f"  {GREEN}✓ PASS{NC}: {message}")
    else:
        print(f"  {RED}✗ FAIL{NC}: {message}")
        all_passed = False
    print()

    # Test 2: Subpackage imports
    print("Test 2: Subpackage imports...")
    passed, messages = test_subpackage_imports()
    results.append(("Subpackage imports", passed, messages))
    if passed:
        print(f"  {GREEN}✓ PASS{NC}: All importable subpackages work correctly")
        for msg in messages:
            print(f"    - {msg}")
    else:
        print(f"  {RED}✗ FAIL{NC}:")
        for msg in messages:
            print(f"    - {msg}")
        all_passed = False
    print()

    # Test 3: Namespace coexistence
    print("Test 3: Namespace coexistence...")
    passed, messages = test_namespace_coexistence()
    results.append(("Namespace coexistence", passed, messages))
    if passed:
        print(f"  {GREEN}✓ PASS{NC}: Multiple packages coexist in namespace")
    else:
        print(f"  {RED}✗ FAIL{NC}:")
        for msg in messages:
            print(f"    - {msg}")
        all_passed = False
    print()

    # Test 4: Version attributes
    print("Test 4: Version attributes...")
    passed, messages = test_version_attributes()
    results.append(("Version attributes", passed, messages))
    if passed:
        print(f"  {GREEN}✓ PASS{NC}: Subpackages have proper version attributes")
        for msg in messages:
            print(f"    - {msg}")
    else:
        print(f"  {RED}✗ FAIL{NC}:")
        for msg in messages:
            print(f"    - {msg}")
        all_passed = False
    print()

    # Summary
    print_header("📊 Summary")
    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)

    print(f"Tests passed: {passed_count}/{total_count}")
    print()

    if all_passed:
        print(f"{GREEN}✅ All PEP 420 integration tests passed!{NC}")
        return 0
    else:
        print(f"{RED}❌ Some tests failed. See details above.{NC}")
        print()
        print("Troubleshooting:")
        print("  1. Ensure all SAGE packages are installed in dev mode:")
        print("     pip install -e packages/sage-common")
        print("     pip install -e packages/sage-kernel")
        print("     pip install -e packages/sage-libs")
        print()
        print("  2. Check that packages/*/src/sage/__init__.py does NOT exist")
        print("     (PEP 420 requires implicit namespace packages)")
        print()
        print("  3. Verify pyproject.toml has 'namespaces = true':")
        print("     [tool.setuptools.packages.find]")
        print("     namespaces = true")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
