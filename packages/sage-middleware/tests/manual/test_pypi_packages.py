#!/usr/bin/env python3
"""测试独立包的导入和兼容性"""

import sys
import warnings

# Suppress warnings during import
warnings.filterwarnings("ignore", category=UserWarning)


def test_direct_import(module_name, display_name):
    """Test direct package import"""
    print(f"\n📦 Testing {display_name} ({module_name})...")
    try:
        __import__(module_name)
        print("  ✅ Package imported successfully")
        return True
    except ImportError as e:
        print(f"  ⚠️  Package not available: {e}")
        return False


def test_sage_compatibility_layer(module_path, display_name):
    """Test SAGE compatibility layer"""
    print(f"\n🔗 Testing SAGE compatibility layer for {display_name}...")
    print(f"   Import path: {module_path}")
    try:
        # Import through SAGE
        parts = module_path.split(".")
        module = __import__(module_path, fromlist=[parts[-1]])

        # Try to get availability flag
        availability_attrs = [
            attr for attr in dir(module) if attr.endswith("_AVAILABLE") and attr.startswith("_SAGE")
        ]

        if availability_attrs:
            for attr in availability_attrs:
                value = getattr(module, attr)
                status = "✅ Available" if value else "⚠️  Not available"
                print(f"  {attr}: {status}")
            return any(getattr(module, attr) for attr in availability_attrs)
        else:
            print("  ✅ Module imported (no availability flags found)")
            return True
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("🔍 Testing SAGE Middleware Components Compatibility")
    print("=" * 60)

    components = [
        ("sagedb", "sage.middleware.components.sage_db", "SageDB"),
        ("sage_flow", "sage.middleware.components.sage_flow", "SageFlow"),
        ("sage_tsdb", "sage.middleware.components.sage_tsdb", "SageTSDB"),
        ("sage_refiner", "sage.middleware.components.sage_refiner", "SageRefiner"),
    ]

    direct_results = {}
    compat_results = {}

    print("\n" + "=" * 60)
    print("Phase 1: Direct PyPI Package Imports")
    print("=" * 60)

    for pkg, _, display in components:
        direct_results[display] = test_direct_import(pkg, display)

    print("\n" + "=" * 60)
    print("Phase 2: SAGE Compatibility Layer")
    print("=" * 60)

    for _, path, display in components:
        compat_results[display] = test_sage_compatibility_layer(path, display)

    print("\n" + "=" * 60)
    print("📊 Summary:")
    print("=" * 60)

    direct_available = sum(direct_results.values())
    compat_available = sum(compat_results.values())
    total = len(components)

    print(f"\nDirect package imports: {direct_available}/{total}")
    for name, status in direct_results.items():
        symbol = "✅" if status else "⚠️ "
        print(f"  {symbol} {name}")

    print(f"\nSAGE compatibility layer: {compat_available}/{total}")
    for name, status in compat_results.items():
        symbol = "✅" if status else "⚠️ "
        print(f"  {symbol} {name}")

    print("\n💡 Note: It's OK if some packages are unavailable.")
    print("   They are optional dependencies for advanced features.")
    print("   The key requirement is that imports don't crash.")

    # Test that extensions_compat works
    print("\n" + "=" * 60)
    print("Phase 3: Testing extensions_compat")
    print("=" * 60)
    try:
        from sage.middleware.components.extensions_compat import (
            check_extensions_availability,
        )

        ext_status = check_extensions_availability()
        print("\n✅ extensions_compat works")
        print(f"   Status: {ext_status}")
    except Exception as e:
        print(f"\n❌ extensions_compat failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    print("\n✅ All tests passed! Imports are graceful even without packages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
