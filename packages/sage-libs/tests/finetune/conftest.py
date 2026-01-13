"""Pytest configuration for finetune tests."""

import sys
from pathlib import Path

import pytest

# Add sage-libs src to path
sage_libs_src = Path(__file__).parent.parent.parent / "src"
if sage_libs_src.exists():
    sys.path.insert(0, str(sage_libs_src))


# Skip all tests in this module if isage-finetune is not installed
def pytest_collection_modifyitems(config, items):
    """Skip finetune tests if isage-finetune is not installed."""
    try:
        import isage_finetune  # noqa: F401
    except ImportError:
        skip_marker = pytest.mark.skip(
            reason="isage-finetune not installed. Install with: pip install isage-finetune"
        )
        for item in items:
            if "finetune" in str(item.fspath):
                item.add_marker(skip_marker)
