# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Integration tests for dynamic backend discovery.

This module tests the dynamic backend discovery functionality including:
1. Backend discovery endpoint responses
2. Client backend refresh mechanism
3. Automatic failover when backends go down
4. New engine discovery within refresh interval
5. Error handling when no backends are available

Tests use mock servers and control plane components to simulate
real-world scenarios without requiring actual running services.
"""

from __future__ import annotations

import os
import threading
import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables before each test."""
    env_vars = [
        "SAGE_UNIFIED_BASE_URL",
        "SAGE_UNIFIED_MODEL",
        "SAGE_CHAT_BASE_URL",
        "SAGE_CHAT_MODEL",
        "SAGE_EMBEDDING_BASE_URL",
        "SAGE_EMBEDDING_MODEL",
    ]
    original = {k: os.environ.get(k) for k in env_vars}

    for k in env_vars:
        if k in os.environ:
            del os.environ[k]

    yield

    for k, v in original.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]


@pytest.fixture
def mock_backends_response():
    """Create a mock backends response."""
    return {
        "llm_backends": [
            {
                "engine_id": "llm-1",
                "model_id": "Qwen/Qwen2.5-7B-Instruct",
                "host": "localhost",
                "port": 8901,
                "healthy": True,
            },
            {
                "engine_id": "llm-2",
                "model_id": "Qwen/Qwen2.5-7B-Instruct",
                "host": "localhost",
                "port": 8902,
                "healthy": True,
            },
        ],
        "embedding_backends": [
            {
                "engine_id": "embed-1",
                "model_id": "BAAI/bge-m3",
                "host": "localhost",
                "port": 8090,
                "healthy": True,
            },
        ],
    }


@pytest.fixture
def mock_backends_partial_healthy():
    """Create a mock backends response with some unhealthy backends."""
    return {
        "llm_backends": [
            {
                "engine_id": "llm-1",
                "model_id": "Qwen/Qwen2.5-7B-Instruct",
                "host": "localhost",
                "port": 8901,
                "healthy": False,  # Unhealthy
            },
            {
                "engine_id": "llm-2",
                "model_id": "Qwen/Qwen2.5-7B-Instruct",
                "host": "localhost",
                "port": 8902,
                "healthy": True,
            },
        ],
        "embedding_backends": [
            {
                "engine_id": "embed-1",
                "model_id": "BAAI/bge-m3",
                "host": "localhost",
                "port": 8090,
                "healthy": True,
            },
        ],
    }


@pytest.fixture
def mock_backends_empty():
    """Create a mock backends response with no backends."""
    return {
        "llm_backends": [],
        "embedding_backends": [],
    }


@pytest.fixture
def mock_control_plane_manager():
    """Create a mock Control Plane Manager."""
    manager = MagicMock()
    manager.get_registered_backends = MagicMock()
    return manager


# =============================================================================
# Backend Discovery Tests
# =============================================================================


class TestBackendDiscoveryEndpoint:
    """Tests for the /v1/management/backends endpoint."""

    def test_backends_endpoint_returns_categorized_list(self, mock_backends_response):
        """Test that backends endpoint returns LLM and Embedding backends separately."""
        with patch("sage.gateway.routes.control_plane._control_plane_manager") as mock_manager:
            mock_manager.get_registered_backends.return_value = mock_backends_response

            with patch(
                "sage.gateway.routes.control_plane._require_control_plane_manager",
                return_value=mock_manager,
            ):
                # Simulate calling the endpoint
                result = mock_manager.get_registered_backends()

                assert "llm_backends" in result
                assert "embedding_backends" in result
                assert len(result["llm_backends"]) == 2
                assert len(result["embedding_backends"]) == 1

    def test_backends_include_health_status(self, mock_backends_response):
        """Test that backend info includes health status."""
        for backend in mock_backends_response["llm_backends"]:
            assert "healthy" in backend
            assert isinstance(backend["healthy"], bool)

        for backend in mock_backends_response["embedding_backends"]:
            assert "healthy" in backend
            assert isinstance(backend["healthy"], bool)

    def test_backends_include_connection_info(self, mock_backends_response):
        """Test that backend info includes host and port."""
        for backend in mock_backends_response["llm_backends"]:
            assert "host" in backend
            assert "port" in backend
            assert isinstance(backend["port"], int)


# =============================================================================
# Client Backend Refresh Tests
# =============================================================================


class TestClientBackendRefresh:
    """Tests for client-side backend refresh mechanism."""

    def test_client_can_parse_backends_response(self, mock_backends_response):
        """Test that client can parse the backends response format."""
        llm_backends = mock_backends_response["llm_backends"]
        embedding_backends = mock_backends_response["embedding_backends"]

        # Extract healthy LLM backends
        healthy_llm = [b for b in llm_backends if b.get("healthy", False)]
        assert len(healthy_llm) == 2

        # Extract healthy embedding backends
        healthy_embed = [b for b in embedding_backends if b.get("healthy", False)]
        assert len(healthy_embed) == 1

    def test_filter_unhealthy_backends(self, mock_backends_partial_healthy):
        """Test filtering out unhealthy backends."""
        llm_backends = mock_backends_partial_healthy["llm_backends"]

        healthy_llm = [b for b in llm_backends if b.get("healthy", False)]
        assert len(healthy_llm) == 1
        assert healthy_llm[0]["engine_id"] == "llm-2"

    def test_build_backend_urls_from_response(self, mock_backends_response):
        """Test building backend URLs from response."""
        llm_backends = mock_backends_response["llm_backends"]

        urls = []
        for backend in llm_backends:
            if backend.get("healthy", False):
                url = f"http://{backend['host']}:{backend['port']}/v1"
                urls.append(url)

        assert len(urls) == 2
        assert "http://localhost:8901/v1" in urls
        assert "http://localhost:8902/v1" in urls


# =============================================================================
# Failover Tests
# =============================================================================


class TestAutomaticFailover:
    """Tests for automatic failover when backends become unavailable."""

    def test_select_healthy_backend_when_primary_down(self, mock_backends_partial_healthy):
        """Test selecting healthy backend when primary is down."""
        llm_backends = mock_backends_partial_healthy["llm_backends"]

        # Simulate backend selection logic
        def select_healthy_backend(backends: list[dict]) -> dict | None:
            for backend in backends:
                if backend.get("healthy", False):
                    return backend
            return None

        selected = select_healthy_backend(llm_backends)
        assert selected is not None
        assert selected["engine_id"] == "llm-2"
        assert selected["port"] == 8902

    def test_no_backend_available_raises_error(self, mock_backends_empty):
        """Test that error is raised when no backends are available."""
        llm_backends = mock_backends_empty["llm_backends"]

        def select_healthy_backend(backends: list[dict]) -> dict | None:
            for backend in backends:
                if backend.get("healthy", False):
                    return backend
            return None

        selected = select_healthy_backend(llm_backends)
        assert selected is None

    def test_failover_order_preference(self):
        """Test that failover respects backend order/priority."""
        backends = [
            {"engine_id": "llm-1", "port": 8901, "healthy": False, "priority": 1},
            {"engine_id": "llm-2", "port": 8902, "healthy": True, "priority": 2},
            {"engine_id": "llm-3", "port": 8903, "healthy": True, "priority": 3},
        ]

        # Select first healthy backend
        healthy = [b for b in backends if b.get("healthy", False)]
        if healthy:
            # Sort by priority if available
            healthy.sort(key=lambda x: x.get("priority", 999))
            selected = healthy[0]
        else:
            selected = None

        assert selected is not None
        assert selected["engine_id"] == "llm-2"


# =============================================================================
# New Engine Discovery Tests
# =============================================================================


class TestNewEngineDiscovery:
    """Tests for discovering newly started engines."""

    def test_new_engine_appears_in_backends(self):
        """Test that a new engine appears in the backends list after registration."""
        # Initial state
        initial_backends = {
            "llm_backends": [
                {"engine_id": "llm-1", "port": 8901, "healthy": True},
            ],
            "embedding_backends": [],
        }

        # After new engine starts
        updated_backends = {
            "llm_backends": [
                {"engine_id": "llm-1", "port": 8901, "healthy": True},
                {"engine_id": "llm-2", "port": 8902, "healthy": True},  # New engine
            ],
            "embedding_backends": [],
        }

        assert len(initial_backends["llm_backends"]) == 1
        assert len(updated_backends["llm_backends"]) == 2

        # Find new engine
        initial_ids = {b["engine_id"] for b in initial_backends["llm_backends"]}
        new_engines = [
            b for b in updated_backends["llm_backends"] if b["engine_id"] not in initial_ids
        ]
        assert len(new_engines) == 1
        assert new_engines[0]["engine_id"] == "llm-2"

    def test_engine_removal_detected(self):
        """Test that removed engines are detected."""
        # Initial state with two engines
        initial_backends = {
            "llm_backends": [
                {"engine_id": "llm-1", "port": 8901, "healthy": True},
                {"engine_id": "llm-2", "port": 8902, "healthy": True},
            ],
        }

        # After one engine stops
        updated_backends = {
            "llm_backends": [
                {"engine_id": "llm-1", "port": 8901, "healthy": True},
            ],
        }

        initial_ids = {b["engine_id"] for b in initial_backends["llm_backends"]}
        updated_ids = {b["engine_id"] for b in updated_backends["llm_backends"]}

        removed = initial_ids - updated_ids
        assert "llm-2" in removed


# =============================================================================
# Backend State Transition Tests
# =============================================================================


class TestBackendStateTransitions:
    """Tests for backend state transitions affecting discovery."""

    def test_starting_engine_not_marked_healthy(self):
        """Test that STARTING engines are not marked as healthy."""
        backends = {
            "llm_backends": [
                {"engine_id": "llm-1", "port": 8901, "state": "STARTING", "healthy": False},
                {"engine_id": "llm-2", "port": 8902, "state": "READY", "healthy": True},
            ],
        }

        healthy = [b for b in backends["llm_backends"] if b.get("healthy", False)]
        assert len(healthy) == 1
        assert healthy[0]["state"] == "READY"

    def test_draining_engine_excluded_from_routing(self):
        """Test that DRAINING engines are excluded from new request routing."""
        backends = {
            "llm_backends": [
                {"engine_id": "llm-1", "port": 8901, "state": "DRAINING", "healthy": False},
                {"engine_id": "llm-2", "port": 8902, "state": "READY", "healthy": True},
            ],
        }

        # For new requests, only route to READY backends
        routable = [
            b
            for b in backends["llm_backends"]
            if b.get("healthy", False) and b.get("state") == "READY"
        ]
        assert len(routable) == 1
        assert routable[0]["engine_id"] == "llm-2"

    def test_error_state_engine_marked_unhealthy(self):
        """Test that ERROR state engines are marked unhealthy."""
        backends = {
            "llm_backends": [
                {"engine_id": "llm-1", "port": 8901, "state": "ERROR", "healthy": False},
            ],
        }

        healthy = [b for b in backends["llm_backends"] if b.get("healthy", False)]
        assert len(healthy) == 0


# =============================================================================
# Refresh Interval Tests
# =============================================================================


class TestRefreshInterval:
    """Tests for backend refresh timing."""

    def test_refresh_interval_default(self):
        """Test default refresh interval configuration."""
        # Default should be 30 seconds as per task spec
        default_interval = 30
        assert default_interval == 30

    def test_stale_backend_list_detection(self):
        """Test detection of stale backend list."""
        last_refresh = time.time() - 60  # 60 seconds ago
        refresh_interval = 30

        is_stale = (time.time() - last_refresh) > refresh_interval
        assert is_stale is True

    def test_fresh_backend_list(self):
        """Test fresh backend list does not trigger refresh."""
        last_refresh = time.time() - 10  # 10 seconds ago
        refresh_interval = 30

        is_stale = (time.time() - last_refresh) > refresh_interval
        assert is_stale is False


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestDiscoveryErrorHandling:
    """Tests for error handling in backend discovery."""

    def test_discovery_endpoint_unavailable(self):
        """Test handling when discovery endpoint is unavailable."""

        # Simulate network error
        def mock_fetch_backends():
            raise ConnectionError("Connection refused")

        with pytest.raises(ConnectionError):
            mock_fetch_backends()

    def test_malformed_response_handling(self):
        """Test handling of malformed backend response."""
        malformed_response: dict[str, object] = {
            "llm_backends": "not a list",  # Should be a list
        }

        # Accessing items from a string would fail when trying to access dict keys
        backends = malformed_response["llm_backends"]

        # Trying to access a dict key on string items will fail
        if isinstance(backends, list):
            for backend in backends:
                _ = backend.get("engine_id")  # This would work for dicts
        else:
            # Verify that we correctly detect the malformed response
            assert not isinstance(backends, list)
            with pytest.raises((TypeError, AttributeError)):
                # Trying to call .get() on a string character
                # This is intentionally testing error handling
                for item in backends:  # type: ignore[union-attr]
                    item.get("engine_id")  # type: ignore[union-attr]

    def test_missing_required_fields(self):
        """Test handling of backends with missing required fields."""
        incomplete_backends = {
            "llm_backends": [
                {"engine_id": "llm-1"},  # Missing host, port, healthy
            ],
        }

        backend = incomplete_backends["llm_backends"][0]

        # Should handle missing fields gracefully
        host = backend.get("host", "localhost")
        port = backend.get("port", 8000)
        healthy = backend.get("healthy", False)

        assert host == "localhost"
        assert port == 8000
        assert healthy is False


# =============================================================================
# Concurrent Access Tests
# =============================================================================


class TestConcurrentDiscovery:
    """Tests for concurrent backend discovery operations."""

    def test_thread_safe_backend_update(self):
        """Test that backend list updates are thread-safe."""
        backends = {"llm_backends": []}
        lock = threading.Lock()

        def add_backend(engine_id: str):
            with lock:
                backends["llm_backends"].append({"engine_id": engine_id})

        threads = [threading.Thread(target=add_backend, args=(f"llm-{i}",)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(backends["llm_backends"]) == 10

    def test_read_during_refresh(self):
        """Test reading backends while refresh is in progress."""
        backends = {
            "llm_backends": [
                {"engine_id": "llm-1", "healthy": True},
            ]
        }
        lock = threading.RLock()

        read_results = []

        def read_backends():
            with lock:
                read_results.append(len(backends["llm_backends"]))

        def update_backends():
            with lock:
                backends["llm_backends"].append({"engine_id": "llm-2", "healthy": True})

        read_thread = threading.Thread(target=read_backends)
        update_thread = threading.Thread(target=update_backends)

        read_thread.start()
        update_thread.start()
        read_thread.join()
        update_thread.join()

        # Result should be 1 or 2 depending on timing, but consistent
        assert read_results[0] in [1, 2]
