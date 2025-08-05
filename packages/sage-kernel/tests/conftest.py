#!/usr/bin/env python3
"""
Top-level test configuration for sage-kernel package
"""

import pytest
import sys
from pathlib import Path

# Add src to path if needed
src_path = Path(__file__).parent.parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Ensure .sage/logs directory exists for coverage reports
logs_dir = Path(__file__).parent.parent.parent.parent / '.sage' / 'logs'
logs_dir.mkdir(parents=True, exist_ok=True)

# Test configuration
pytest_plugins = []
