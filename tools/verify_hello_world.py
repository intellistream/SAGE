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
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))


def main() -> int:
    """Verify SAGE installation by testing core imports."""
    print("=" * 50)
    print("SAGE Installation Verification")
    print("=" * 50)

    errors = []

    transitional = []

    # Transitional compatibility surfaces may still be present in migrated environments.
    try:
        import sage.common

        print(f"ℹ️  sage.common {sage.common.__version__} (transitional)")
    except ImportError as e:
        print(f"⚠️  sage.common: {e} (transitional)")
        transitional.append("sage.common")

    # Transitional surface: sage.libs (now owned by consolidated isage)
    try:
        import sage.libs

        print(f"ℹ️  sage.libs {sage.libs.__version__} (transitional)")
    except ImportError as e:
        print(f"⚠️  sage.libs: {e} (transitional)")
        transitional.append("sage.libs")

    # Transitional surface: sage.platform (now owned by consolidated isage runtime/foundation)
    try:
        import sage.platform

        print(f"ℹ️  sage.platform {sage.platform.__version__} (transitional)")
    except ImportError as e:
        print(f"⚠️  sage.platform: {e} (transitional)")
        transitional.append("sage.platform")

    # Transitional kernel/middleware imports are optional and no longer part of the root contract.
    try:
        import sage.kernel

        print(f"ℹ️  sage.kernel {sage.kernel.__version__} (transitional)")
    except ImportError as e:
        print(f"⚠️  sage.kernel: {e} (transitional)")
        transitional.append("sage.kernel")

    # Test L2: sage.middleware (transitional)
    try:
        import sage.middleware

        print(f"ℹ️  sage.middleware {sage.middleware.__version__} (transitional)")
    except ImportError as e:
        print(f"⚠️  sage.middleware: {e} (transitional)")
        transitional.append("sage.middleware")

    # Test main-repo in-tree surfaces
    try:
        import sage.foundation

        print("✅ sage.foundation")
    except ImportError as e:
        print(f"❌ sage.foundation: {e}")
        errors.append("sage.foundation")

    try:
        import sage.stream

        print("✅ sage.stream")
    except ImportError as e:
        print(f"❌ sage.stream: {e}")
        errors.append("sage.stream")

    try:
        import sage.runtime

        print("✅ sage.runtime")
    except ImportError as e:
        print(f"❌ sage.runtime: {e}")
        errors.append("sage.runtime")

    try:
        import sage.serving

        print("✅ sage.serving")
    except ImportError as e:
        print(f"❌ sage.serving: {e}")
        errors.append("sage.serving")

    # Test L3: main-repo CLI (required)
    try:
        import sage.cli

        print(f"✅ sage.cli {sage.cli.__version__}")
    except ImportError as e:
        print(f"❌ sage.cli: {e}")
        errors.append("sage.cli")

    print("=" * 50)

    if errors:
        print(f"❌ Core packages failed: {', '.join(errors)}")
        print("Please reinstall: ./quickstart.sh --dev --yes")
        return 1

    # Get overall version from main repo
    try:
        from sage._version import __version__ as version
    except Exception:
        version = "unknown"

    print(f"✅ SAGE v{version} installed successfully!")
    print()
    print("Next steps:")
    print("  - Verify CLI surface: sage verify")
    print("  - Inspect runtime view: sage runtime nodes")
    print("  - Inspect gateway contract: sage serve gateway --json")
    print("  - Build a stream: from sage.stream import DataStream")
    print("  - Pick a runtime: from sage.runtime import LocalEnvironment, FluttyEnvironment")
    print("  - Attach serving when needed: from sage.serving import SageServeConfig")
    print('  - Chat with sagellm: sage chat --ask "Hello, SAGE!"')
    print(
        "  - Record lightweight index metadata: sage index ingest --source ./docs --index local-docs"
    )
    if transitional:
        print(
            f"  - Transitional packages still visible via kernel stack: {', '.join(transitional)}"
        )
    print("  - Read docs: https://intellistream.github.io/sage-docs/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
