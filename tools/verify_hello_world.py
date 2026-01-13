#!/usr/bin/env python3
"""SAGE Installation Verification Script.

This is a minimal hello world script to verify SAGE installation.
It tests core imports without requiring external services or API keys.

Usage:
    python tools/verify_hello_world.py

Expected output:
    ✅ SAGE v0.x.x installed successfully!
"""

import sys


def main() -> int:
    """Verify SAGE installation by testing core imports."""
    print("=" * 50)
    print("SAGE Installation Verification")
    print("=" * 50)

    errors = []

    # Test L1: sage-common
    try:
        import sage.common

        print(f"✅ sage.common {sage.common.__version__}")
    except ImportError as e:
        print(f"❌ sage.common: {e}")
        errors.append("sage.common")

    # Test L2: sage-platform
    try:
        import sage.platform

        print(f"✅ sage.platform {sage.platform.__version__}")
    except ImportError as e:
        print(f"❌ sage.platform: {e}")
        errors.append("sage.platform")

    # Test L3: sage-kernel
    try:
        import sage.kernel

        print(f"✅ sage.kernel {sage.kernel.__version__}")
    except ImportError as e:
        print(f"❌ sage.kernel: {e}")
        errors.append("sage.kernel")

    # Test L3: sage-libs (interface layer only)
    try:
        import sage.libs

        print(f"✅ sage.libs {sage.libs.__version__}")
    except ImportError as e:
        print(f"❌ sage.libs: {e}")
        errors.append("sage.libs")

    # Test L4: sage-middleware (optional, may have heavy deps)
    try:
        import sage.middleware

        print(f"✅ sage.middleware {sage.middleware.__version__}")
    except ImportError as e:
        print(f"⚠️  sage.middleware: {e} (optional)")

    # Test L5: sage-cli (optional)
    try:
        import sage.cli

        print(f"✅ sage.cli {sage.cli.__version__}")
    except ImportError as e:
        print(f"⚠️  sage.cli: {e} (optional)")

    # Test L5: sage-tools (optional)
    try:
        import sage.tools

        print(f"✅ sage.tools {sage.tools.__version__}")
    except ImportError as e:
        print(f"⚠️  sage.tools: {e} (optional)")

    print("=" * 50)

    if errors:
        print(f"❌ Core packages failed: {', '.join(errors)}")
        print("Please reinstall: ./quickstart.sh --dev --yes")
        return 1

    # Get overall version from sage.common
    try:
        version = sage.common.__version__
    except Exception:
        version = "unknown"

    print(f"✅ SAGE v{version} installed successfully!")
    print()
    print("Next steps:")
    print("  - Clone examples: git clone https://github.com/intellistream/sage-examples.git")
    print("  - Run tutorial: python sage-examples/tutorials/hello_world.py")
    print("  - Read docs: https://intellistream.github.io/SAGE-Pub/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
