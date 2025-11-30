"""Pytest configuration for finetune tests."""

import sys
from pathlib import Path

# Add sage-libs src to path
sage_libs_src = Path(__file__).parent.parent.parent / "src"
if sage_libs_src.exists():
    sys.path.insert(0, str(sage_libs_src))
