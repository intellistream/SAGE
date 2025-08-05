#!/usr/bin/env python3
"""
Test configuration and utilities for sage.core.api tests

This module provides shared test configurations, fixtures, and utilities
for all API tests following the testing organization structure.
"""

import pytest
import sys
from pathlib import Path

# Add the src directory to the Python path for imports
src_path = Path(__file__).parent.parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Test configuration
# pytest_plugins moved to top-level conftest.py

# Shared fixtures
@pytest.fixture(scope="session")
def test_config():
    """Shared test configuration"""
    return {
        "test_timeout": 30,
        "mock_data_size": 100,
        "log_level": "DEBUG"
    }

@pytest.fixture
def sample_data():
    """Sample data for testing"""
    return [
        {"id": 1, "name": "Alice", "value": 10},
        {"id": 2, "name": "Bob", "value": 20},
        {"id": 3, "name": "Charlie", "value": 30},
        {"id": 4, "name": "David", "value": 40},
        {"id": 5, "name": "Eve", "value": 50}
    ]

@pytest.fixture
def large_sample_data():
    """Large sample data for performance testing"""
    return [{"id": i, "value": i * 10} for i in range(1000)]

# Test markers
pytestmark = [
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
    pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
]
