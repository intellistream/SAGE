"""
Pytest configuration for sage-libs tests.

This file ensures that the examples directory is available in the Python path
for tests that import from examples.agents and examples.tutorials.
"""

import sys

from sage.common.config import find_sage_project_root

# Add SAGE root directory to Python path
# This allows importing from examples/ directory
sage_root = find_sage_project_root()
if str(sage_root) not in sys.path:
    sys.path.insert(0, str(sage_root))
