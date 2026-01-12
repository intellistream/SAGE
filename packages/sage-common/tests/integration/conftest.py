# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Pytest fixtures for integration tests.

This module provides shared fixtures for integration testing.

NOTE: LLM/Control Plane specific fixtures have been moved to isagellm.
See: pip install isagellm
"""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock

import pytest

# Add source path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))


@pytest.fixture
def mock_async_client():
    """Create a mock async HTTP client."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    return client


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
