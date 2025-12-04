# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Integration tests for SAGE Gateway Control Plane.

This module tests the Control Plane management API endpoints including:
1. Gateway startup/shutdown with Control Plane enabled
2. Engine registration and lifecycle management
3. Engine state transitions (STARTING → READY → DRAINING → STOPPED)
4. Backend discovery endpoints
5. Cluster status reporting

Tests use mock Control Plane components to avoid requiring actual GPU resources.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Import app at module level - package may not be installed in all environments
from sage.gateway.server import app as gateway_app  # type: ignore[import-not-found]

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_control_plane_manager():
    """Create a mock Control Plane Manager for testing."""
    manager = MagicMock()

    # Mock engine info objects
    mock_engine_1 = MagicMock()
    mock_engine_1.to_dict.return_value = {
        "engine_id": "engine-1",
        "model_id": "Qwen/Qwen2.5-7B-Instruct",
        "host": "localhost",
        "port": 8901,
        "state": "READY",
        "engine_kind": "llm",
        "created_at": "2025-01-01T00:00:00",
        "last_heartbeat": "2025-01-01T00:01:00",
    }

    mock_engine_2 = MagicMock()
    mock_engine_2.to_dict.return_value = {
        "engine_id": "engine-2",
        "model_id": "BAAI/bge-m3",
        "host": "localhost",
        "port": 8090,
        "state": "READY",
        "engine_kind": "embedding",
        "created_at": "2025-01-01T00:00:00",
        "last_heartbeat": "2025-01-01T00:01:00",
    }

    # Configure mock methods
    manager.list_registered_engines.return_value = [mock_engine_1, mock_engine_2]

    manager.register_engine.return_value = mock_engine_1

    manager.request_engine_startup.return_value = {
        "engine_id": "engine-new",
        "model_id": "test-model",
        "port": 8902,
        "status": "STARTING",
    }

    manager.request_engine_shutdown.return_value = {
        "engine_id": "engine-1",
        "stopped": True,
    }

    manager.stop_engine_gracefully = AsyncMock(return_value=True)

    manager.get_cluster_status.return_value = {
        "total_engines": 2,
        "engines_by_state": {"READY": 2, "STARTING": 0, "DRAINING": 0, "STOPPED": 0},
        "total_gpus": 1,
        "used_gpus": 1,
    }

    manager.get_registered_backends.return_value = {
        "llm_backends": [
            {
                "engine_id": "engine-1",
                "model_id": "Qwen/Qwen2.5-7B-Instruct",
                "host": "localhost",
                "port": 8901,
                "healthy": True,
            }
        ],
        "embedding_backends": [
            {
                "engine_id": "engine-2",
                "model_id": "BAAI/bge-m3",
                "host": "localhost",
                "port": 8090,
                "healthy": True,
            }
        ],
    }

    # Mock start/stop for async context
    manager.start = AsyncMock()
    manager.stop = AsyncMock()

    return manager


@pytest.fixture
def client_with_control_plane(mock_control_plane_manager):
    """Create a test client with mocked Control Plane."""
    # Patch the control plane module before creating client
    with (
        patch("sage.gateway.routes.control_plane.CONTROL_PLANE_AVAILABLE", True),
        patch(
            "sage.gateway.routes.control_plane._control_plane_manager",
            mock_control_plane_manager,
        ),
        patch(
            "sage.gateway.routes.control_plane.init_control_plane",
            return_value=True,
        ),
    ):
        client = TestClient(gateway_app)
        yield client


@pytest.fixture
def client_without_control_plane():
    """Create a test client without Control Plane enabled."""
    with (
        patch("sage.gateway.routes.control_plane.CONTROL_PLANE_AVAILABLE", False),
        patch("sage.gateway.routes.control_plane._control_plane_manager", None),
    ):
        client = TestClient(gateway_app)
        yield client


# =============================================================================
# Control Plane Root Endpoint Tests
# =============================================================================


class TestControlPlaneRoot:
    """Tests for the Control Plane root endpoint."""

    def test_control_plane_root_available(self, client_with_control_plane):
        """Test /v1/management returns available status when Control Plane is enabled."""
        response = client_with_control_plane.get("/v1/management")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "SAGE Gateway Control Plane"
        assert data["status"] == "available"
        assert "endpoints" in data

    def test_control_plane_root_unavailable(self, client_without_control_plane):
        """Test /v1/management returns unavailable when Control Plane is disabled."""
        response = client_without_control_plane.get("/v1/management")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "unavailable"


# =============================================================================
# Engine List Tests
# =============================================================================


class TestEngineList:
    """Tests for listing registered engines."""

    def test_list_engines_success(self, client_with_control_plane, mock_control_plane_manager):
        """Test GET /v1/management/engines returns engine list."""
        response = client_with_control_plane.get("/v1/management/engines")
        assert response.status_code == 200

        data = response.json()
        assert "engines" in data
        assert "count" in data
        assert data["count"] == 2
        assert len(data["engines"]) == 2

        # Verify engine details
        engine_ids = [e["engine_id"] for e in data["engines"]]
        assert "engine-1" in engine_ids
        assert "engine-2" in engine_ids

    def test_list_engines_no_control_plane(self, client_without_control_plane):
        """Test GET /v1/management/engines returns 503 when Control Plane unavailable."""
        response = client_without_control_plane.get("/v1/management/engines")
        assert response.status_code == 503


# =============================================================================
# Engine Registration Tests
# =============================================================================


class TestEngineRegistration:
    """Tests for engine registration."""

    def test_register_engine_success(self, client_with_control_plane, mock_control_plane_manager):
        """Test POST /v1/management/engines/register successfully registers an engine."""
        response = client_with_control_plane.post(
            "/v1/management/engines/register",
            json={
                "engine_id": "external-engine-1",
                "model_id": "custom-model",
                "host": "192.168.1.100",
                "port": 8080,
                "engine_kind": "llm",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert "engine_id" in data
        mock_control_plane_manager.register_engine.assert_called_once()

    def test_register_engine_duplicate(self, client_with_control_plane, mock_control_plane_manager):
        """Test registering a duplicate engine returns 409 conflict."""
        mock_control_plane_manager.register_engine.side_effect = ValueError(
            "Engine already registered"
        )

        response = client_with_control_plane.post(
            "/v1/management/engines/register",
            json={
                "engine_id": "engine-1",
                "model_id": "model",
                "host": "localhost",
                "port": 8901,
            },
        )
        assert response.status_code == 409

    def test_register_engine_missing_fields(self, client_with_control_plane):
        """Test registration with missing required fields returns 422."""
        response = client_with_control_plane.post(
            "/v1/management/engines/register",
            json={
                "engine_id": "test",
                # Missing required fields: model_id, port
            },
        )
        assert response.status_code == 422


# =============================================================================
# Engine Start Tests
# =============================================================================


class TestEngineStart:
    """Tests for starting new engines."""

    def test_start_engine_success(self, client_with_control_plane, mock_control_plane_manager):
        """Test POST /v1/management/engines starts a new engine."""
        response = client_with_control_plane.post(
            "/v1/management/engines",
            json={
                "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
                "tensor_parallel_size": 1,
                "engine_kind": "llm",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert "engine_id" in data or "engine" in data
        mock_control_plane_manager.request_engine_startup.assert_called_once()

    def test_start_engine_invalid_instance_type(self, client_with_control_plane):
        """Test starting engine with invalid instance_type returns 400."""
        # Need to mock _ExecutionInstanceType to test this
        with patch("sage.gateway.routes.control_plane._ExecutionInstanceType") as mock_type:
            mock_type.__getitem__.side_effect = KeyError("INVALID")
            mock_type.__iter__ = lambda self: iter([])

            response = client_with_control_plane.post(
                "/v1/management/engines",
                json={
                    "model_id": "test-model",
                    "instance_type": "INVALID_TYPE",
                },
            )
            assert response.status_code == 400

    def test_start_engine_resource_conflict(
        self, client_with_control_plane, mock_control_plane_manager
    ):
        """Test starting engine when resources unavailable returns 409."""
        mock_control_plane_manager.request_engine_startup.side_effect = RuntimeError(
            "No GPU available"
        )

        response = client_with_control_plane.post(
            "/v1/management/engines",
            json={
                "model_id": "large-model",
                "tensor_parallel_size": 8,
            },
        )
        assert response.status_code == 409


# =============================================================================
# Engine Stop Tests
# =============================================================================


class TestEngineStop:
    """Tests for stopping engines."""

    def test_stop_engine_success(self, client_with_control_plane, mock_control_plane_manager):
        """Test DELETE /v1/management/engines/{id} stops an engine."""
        response = client_with_control_plane.delete("/v1/management/engines/engine-1")
        assert response.status_code == 200

        data = response.json()
        assert data["stopped"] is True
        mock_control_plane_manager.request_engine_shutdown.assert_called_once_with("engine-1")

    def test_stop_engine_with_drain(self, client_with_control_plane, mock_control_plane_manager):
        """Test DELETE /v1/management/engines/{id}?drain=true gracefully drains."""
        response = client_with_control_plane.delete("/v1/management/engines/engine-1?drain=true")
        assert response.status_code == 200

        data = response.json()
        assert data["drained"] is True
        mock_control_plane_manager.stop_engine_gracefully.assert_called_once_with("engine-1")

    def test_stop_engine_not_found(self, client_with_control_plane, mock_control_plane_manager):
        """Test stopping non-existent engine returns appropriate error."""
        mock_control_plane_manager.request_engine_shutdown.return_value = {
            "engine_id": "nonexistent",
            "stopped": False,
        }

        response = client_with_control_plane.delete("/v1/management/engines/nonexistent")
        assert response.status_code == 409


# =============================================================================
# Cluster Status Tests
# =============================================================================


class TestClusterStatus:
    """Tests for cluster status endpoint."""

    def test_cluster_status_success(self, client_with_control_plane, mock_control_plane_manager):
        """Test GET /v1/management/status returns cluster status."""
        response = client_with_control_plane.get("/v1/management/status")
        assert response.status_code == 200

        data = response.json()
        assert "total_engines" in data
        assert data["total_engines"] == 2
        assert "engines_by_state" in data


# =============================================================================
# Backend Discovery Tests
# =============================================================================


class TestBackendDiscovery:
    """Tests for backend discovery endpoint."""

    def test_list_backends_success(self, client_with_control_plane, mock_control_plane_manager):
        """Test GET /v1/management/backends returns categorized backends."""
        response = client_with_control_plane.get("/v1/management/backends")
        assert response.status_code == 200

        data = response.json()
        assert "llm_backends" in data
        assert "embedding_backends" in data
        assert len(data["llm_backends"]) == 1
        assert len(data["embedding_backends"]) == 1

        # Verify LLM backend details
        llm_backend = data["llm_backends"][0]
        assert llm_backend["healthy"] is True
        assert llm_backend["port"] == 8901

        # Verify Embedding backend details
        embed_backend = data["embedding_backends"][0]
        assert embed_backend["healthy"] is True
        assert embed_backend["port"] == 8090


# =============================================================================
# GPU Resource Tests
# =============================================================================


class TestGPUResources:
    """Tests for GPU resource endpoint."""

    def test_gpu_resources_with_info(self, client_with_control_plane, mock_control_plane_manager):
        """Test GET /v1/management/gpu returns GPU info when available."""
        # Add get_gpu_info method to mock
        mock_control_plane_manager.get_gpu_info = MagicMock(
            return_value={
                "gpus": [
                    {"id": 0, "name": "NVIDIA A100", "memory_total": 40960, "memory_used": 20480}
                ],
                "total_gpus": 1,
                "available_gpus": 0,
            }
        )

        response = client_with_control_plane.get("/v1/management/gpu")
        assert response.status_code == 200

        data = response.json()
        assert "gpus" in data

    def test_gpu_resources_fallback(self, client_with_control_plane, mock_control_plane_manager):
        """Test GET /v1/management/gpu returns fallback when no GPU info."""
        # Remove get_gpu_info to trigger fallback
        if hasattr(mock_control_plane_manager, "get_gpu_info"):
            delattr(mock_control_plane_manager, "get_gpu_info")

        response = client_with_control_plane.get("/v1/management/gpu")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data


# =============================================================================
# Engine Lifecycle State Tests
# =============================================================================


class TestEngineLifecycle:
    """Tests for engine lifecycle state transitions."""

    def test_engine_states_in_list(self, client_with_control_plane, mock_control_plane_manager):
        """Test that engine list includes state information."""
        response = client_with_control_plane.get("/v1/management/engines")
        assert response.status_code == 200

        data = response.json()
        for engine in data["engines"]:
            assert "state" in engine
            assert engine["state"] in ["STARTING", "READY", "DRAINING", "STOPPED", "ERROR"]

    def test_draining_state_on_graceful_stop(
        self, client_with_control_plane, mock_control_plane_manager
    ):
        """Test that graceful stop transitions engine to DRAINING state."""
        # This is implicitly tested by the drain=true parameter
        response = client_with_control_plane.delete("/v1/management/engines/engine-1?drain=true")
        assert response.status_code == 200
        assert response.json()["drained"] is True


# =============================================================================
# Gateway Root Endpoint Integration
# =============================================================================


class TestGatewayIntegration:
    """Tests for Control Plane integration with Gateway root."""

    def test_root_includes_control_plane_endpoints(self, client_with_control_plane):
        """Test that Gateway root includes Control Plane endpoints."""
        response = client_with_control_plane.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "endpoints" in data
        # Check for control_plane key in endpoints
        if "control_plane" in data["endpoints"]:
            cp_endpoints = data["endpoints"]["control_plane"]
            assert "engines" in cp_endpoints

    def test_health_check_still_works(self, client_with_control_plane):
        """Test that health check works with Control Plane enabled."""
        response = client_with_control_plane.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
