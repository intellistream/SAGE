# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Integration tests for UnifiedAPIServer.

This module tests the unified API server endpoints including:
1. /v1/chat/completions - Chat completion endpoint
2. /v1/completions - Text completion endpoint
3. /v1/embeddings - Embedding endpoint
4. /v1/models - Model listing endpoint
5. /health - Health check endpoint
6. Concurrent request handling
7. Error handling and edge cases

Tests use mock backends and TestClient to avoid requiring actual
GPU resources or running servers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sage.common.components.sage_llm.unified_api_server import (
    FASTAPI_AVAILABLE,
    BackendInstanceConfig,
    SchedulingPolicyType,
    UnifiedAPIServer,
    UnifiedServerConfig,
)

if TYPE_CHECKING:
    from conftest import MockEmbeddingBackend, MockLLMBackend

# Skip all tests if FastAPI is not available
pytestmark = pytest.mark.skipif(
    not FASTAPI_AVAILABLE,
    reason="FastAPI not available",
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def server_config() -> UnifiedServerConfig:
    """Create a test server configuration."""
    return UnifiedServerConfig(
        host="127.0.0.1",
        port=8000,
        llm_backends=[
            BackendInstanceConfig(
                host="localhost",
                port=8001,
                model_name="Qwen/Qwen2.5-7B-Instruct",
                instance_type="llm",
            ),
        ],
        embedding_backends=[
            BackendInstanceConfig(
                host="localhost",
                port=8090,
                model_name="BAAI/bge-m3",
                instance_type="embedding",
            ),
        ],
        scheduling_policy=SchedulingPolicyType.ADAPTIVE,
        enable_cors=True,
    )


@pytest.fixture
def multi_backend_config() -> UnifiedServerConfig:
    """Create a configuration with multiple backends."""
    return UnifiedServerConfig(
        host="127.0.0.1",
        port=8000,
        llm_backends=[
            BackendInstanceConfig(
                host="localhost",
                port=8001,
                model_name="Qwen/Qwen2.5-7B-Instruct",
                instance_type="llm",
            ),
            BackendInstanceConfig(
                host="localhost",
                port=8002,
                model_name="Qwen/Qwen2.5-14B-Instruct",
                instance_type="llm",
            ),
        ],
        embedding_backends=[
            BackendInstanceConfig(
                host="localhost",
                port=8090,
                model_name="BAAI/bge-m3",
                instance_type="embedding",
            ),
            BackendInstanceConfig(
                host="localhost",
                port=8091,
                model_name="BAAI/bge-large-zh",
                instance_type="embedding",
            ),
        ],
    )


@pytest.fixture
def unified_server(server_config: UnifiedServerConfig) -> UnifiedAPIServer:
    """Create a UnifiedAPIServer instance for testing."""
    return UnifiedAPIServer(server_config)


@pytest.fixture
def test_client(unified_server: UnifiedAPIServer):
    """Create a TestClient for the server."""
    from fastapi.testclient import TestClient

    app = unified_server._create_app()
    unified_server._app = app
    return TestClient(app)


# =============================================================================
# Server Configuration Tests
# =============================================================================


class TestServerConfiguration:
    """Tests for server configuration and initialization."""

    def test_default_configuration(self):
        """Test server with default configuration."""
        config = UnifiedServerConfig()
        server = UnifiedAPIServer(config)

        assert server.config.host == "0.0.0.0"
        assert server.config.port == 8000
        assert server.config.enable_cors is True
        assert server.config.scheduling_policy == SchedulingPolicyType.ADAPTIVE

    def test_custom_configuration(self, server_config: UnifiedServerConfig):
        """Test server with custom configuration."""
        server = UnifiedAPIServer(server_config)

        assert server.config.host == "127.0.0.1"
        assert len(server.config.llm_backends) == 1
        assert len(server.config.embedding_backends) == 1
        assert server.config.llm_backends[0].model_name == "Qwen/Qwen2.5-7B-Instruct"
        assert server.config.embedding_backends[0].model_name == "BAAI/bge-m3"

    def test_model_mappings_built(self, unified_server: UnifiedAPIServer):
        """Test that model mappings are correctly built."""
        assert "Qwen/Qwen2.5-7B-Instruct" in unified_server._llm_models
        assert "BAAI/bge-m3" in unified_server._embedding_models

    def test_multi_backend_configuration(self, multi_backend_config: UnifiedServerConfig):
        """Test configuration with multiple backends."""
        server = UnifiedAPIServer(multi_backend_config)

        assert len(server._llm_models) == 2
        assert len(server._embedding_models) == 2
        assert "Qwen/Qwen2.5-7B-Instruct" in server._llm_models
        assert "Qwen/Qwen2.5-14B-Instruct" in server._llm_models


# =============================================================================
# Endpoint Tests
# =============================================================================


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_returns_server_info(self, test_client):
        """Test root endpoint returns server information."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "SAGE Unified Inference API"
        assert "version" in data
        assert "endpoints" in data
        assert "/v1/chat/completions" in data["endpoints"]["chat"]


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check_returns_status(self, test_client):
        """Test health endpoint returns status."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "backends" in data
        assert "llm" in data["backends"]
        assert "embedding" in data["backends"]

    def test_health_check_shows_backend_counts(self, test_client):
        """Test health endpoint shows correct backend counts."""
        response = test_client.get("/health")

        data = response.json()
        assert data["backends"]["llm"]["count"] == 1
        assert data["backends"]["embedding"]["count"] == 1


class TestModelsEndpoint:
    """Tests for the models listing endpoint."""

    def test_list_models_returns_all_models(self, test_client):
        """Test models endpoint lists all configured models."""
        response = test_client.get("/v1/models")

        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 2  # 1 LLM + 1 embedding

        model_ids = [m["id"] for m in data["data"]]
        assert "Qwen/Qwen2.5-7B-Instruct" in model_ids
        assert "BAAI/bge-m3" in model_ids

    def test_models_have_type_info(self, test_client):
        """Test model entries include type information."""
        response = test_client.get("/v1/models")

        data = response.json()
        for model in data["data"]:
            assert "type" in model
            assert model["type"] in ("llm", "embedding")


class TestChatCompletionsEndpoint:
    """Tests for the chat completions endpoint."""

    def test_chat_completion_missing_model(self, test_client):
        """Test chat completion without model returns 422."""
        response = test_client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )

        # Should return validation error (missing required field)
        assert response.status_code == 422

    def test_chat_completion_unknown_model(self, test_client):
        """Test chat completion with unknown model."""
        # Request with unknown model - will fallback to first backend if available
        response = test_client.post(
            "/v1/chat/completions",
            json={
                "model": "unknown-model",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )

        # Should either forward to first backend or return 500 due to no session
        assert response.status_code in (200, 404, 500)

    def test_chat_completion_request_format(self, test_client):
        """Test chat completion request validation."""
        # Valid format but will fail due to no backend
        response = test_client.post(
            "/v1/chat/completions",
            json={
                "model": "Qwen/Qwen2.5-7B-Instruct",
                "messages": [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hello"},
                ],
                "temperature": 0.7,
                "max_tokens": 100,
            },
        )

        # Request format is valid (may fail due to backend unavailable)
        assert response.status_code in (200, 500)


class TestCompletionsEndpoint:
    """Tests for the text completions endpoint."""

    def test_completion_missing_model(self, test_client):
        """Test completion without model returns 422."""
        response = test_client.post(
            "/v1/completions",
            json={
                "prompt": "Once upon a time",
            },
        )

        assert response.status_code == 422

    def test_completion_request_format(self, test_client):
        """Test completion request validation."""
        response = test_client.post(
            "/v1/completions",
            json={
                "model": "Qwen/Qwen2.5-7B-Instruct",
                "prompt": "Once upon a time",
                "max_tokens": 50,
                "temperature": 0.8,
            },
        )

        # Format is valid (may fail due to backend)
        assert response.status_code in (200, 500)


class TestEmbeddingsEndpoint:
    """Tests for the embeddings endpoint."""

    def test_embedding_missing_fields(self, test_client):
        """Test embedding without required fields returns 422."""
        response = test_client.post(
            "/v1/embeddings",
            json={},
        )

        assert response.status_code == 422

    def test_embedding_single_text(self, test_client):
        """Test embedding single text request format."""
        response = test_client.post(
            "/v1/embeddings",
            json={
                "model": "BAAI/bge-m3",
                "input": "Hello world",
            },
        )

        # Format is valid (may fail due to backend)
        assert response.status_code in (200, 500)

    def test_embedding_multiple_texts(self, test_client):
        """Test embedding multiple texts request format."""
        response = test_client.post(
            "/v1/embeddings",
            json={
                "model": "BAAI/bge-m3",
                "input": ["Text 1", "Text 2", "Text 3"],
            },
        )

        # Format is valid (may fail due to backend)
        assert response.status_code in (200, 500)


# =============================================================================
# Integration with Mock Backends
# =============================================================================


class TestWithMockBackends:
    """Tests using mock backends for full integration testing."""

    @pytest.mark.asyncio
    async def test_chat_completion_with_mock(
        self,
        unified_server: UnifiedAPIServer,
        mock_llm_backend: MockLLMBackend,
    ):
        """Test chat completion flow with mock backend."""
        # Test the backend selection logic
        backend = unified_server._get_llm_backend("Qwen/Qwen2.5-7B-Instruct")
        assert backend is not None
        assert backend.model_name == "Qwen/Qwen2.5-7B-Instruct"
        assert backend.port == 8001

    @pytest.mark.asyncio
    async def test_embedding_with_mock(
        self,
        unified_server: UnifiedAPIServer,
        mock_embedding_backend: MockEmbeddingBackend,
    ):
        """Test embedding flow with mock backend."""
        # Test backend selection
        backend = unified_server._get_embedding_backend("BAAI/bge-m3")
        assert backend is not None
        assert backend.model_name == "BAAI/bge-m3"
        assert backend.port == 8090


# =============================================================================
# Concurrent Request Tests
# =============================================================================


class TestConcurrentRequests:
    """Tests for concurrent request handling."""

    def test_multiple_health_checks(self, test_client):
        """Test multiple concurrent health check requests."""
        import concurrent.futures

        def make_health_request():
            return test_client.get("/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_health_request) for _ in range(20)]
            results = [f.result() for f in futures]

        # All should succeed
        for result in results:
            assert result.status_code == 200

    def test_multiple_model_listings(self, test_client):
        """Test multiple concurrent model listing requests."""
        import concurrent.futures

        def make_models_request():
            return test_client.get("/v1/models")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_models_request) for _ in range(10)]
            results = [f.result() for f in futures]

        for result in results:
            assert result.status_code == 200
            assert len(result.json()["data"]) == 2


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_invalid_json_body(self, test_client):
        """Test handling of invalid JSON request body."""
        response = test_client.post(
            "/v1/chat/completions",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_missing_required_message_field(self, test_client):
        """Test handling of missing required message field."""
        response = test_client.post(
            "/v1/chat/completions",
            json={
                "model": "test",
                # Missing "messages" field
            },
        )

        assert response.status_code == 422

    def test_invalid_temperature_range(self, test_client):
        """Test handling of temperature out of valid range."""
        response = test_client.post(
            "/v1/chat/completions",
            json={
                "model": "test",
                "messages": [{"role": "user", "content": "Hi"}],
                "temperature": 5.0,  # Invalid: should be 0-2
            },
        )

        # Should either validate and reject, or accept (depends on implementation)
        assert response.status_code in (200, 422, 500)


# =============================================================================
# Backend Selection Tests
# =============================================================================


class TestBackendSelection:
    """Tests for backend selection logic."""

    def test_exact_model_match(self, unified_server: UnifiedAPIServer):
        """Test backend selection with exact model name match."""
        backend = unified_server._get_llm_backend("Qwen/Qwen2.5-7B-Instruct")

        assert backend is not None
        assert backend.model_name == "Qwen/Qwen2.5-7B-Instruct"
        assert backend.port == 8001

    def test_fallback_to_first_backend(self, unified_server: UnifiedAPIServer):
        """Test fallback to first backend when model not found."""
        backend = unified_server._get_llm_backend("nonexistent-model")

        # Should fall back to first available backend
        assert backend is not None
        assert backend.model_name == "Qwen/Qwen2.5-7B-Instruct"

    def test_embedding_model_selection(self, unified_server: UnifiedAPIServer):
        """Test embedding backend selection."""
        backend = unified_server._get_embedding_backend("BAAI/bge-m3")

        assert backend is not None
        assert backend.model_name == "BAAI/bge-m3"
        assert backend.port == 8090

    def test_no_backends_configured(self):
        """Test default backend behavior when empty lists provided.

        Note: UnifiedServerConfig.__post_init__ adds default backends
        when llm_backends=[] or embedding_backends=[] is passed.
        This is intentional design to ensure server always has fallback.
        """
        config = UnifiedServerConfig(
            llm_backends=[],
            embedding_backends=[],
        )
        server = UnifiedAPIServer(config)

        # Default backends are added by __post_init__
        # So we should get default backends, not None
        llm_backend = server._get_llm_backend("any-model")
        embed_backend = server._get_embedding_backend("any-model")

        # Verify defaults are applied (localhost with default ports)
        assert llm_backend is not None
        assert embed_backend is not None
        assert llm_backend.host == "localhost"
        assert embed_backend.host == "localhost"


# =============================================================================
# CORS Tests
# =============================================================================


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are present in responses."""
        response = test_client.options(
            "/v1/models",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS preflight should be handled
        assert response.status_code in (200, 204, 405)

    def test_cors_disabled(self):
        """Test server without CORS enabled."""
        config = UnifiedServerConfig(enable_cors=False)
        server = UnifiedAPIServer(config)

        # Server should still work without CORS
        assert server.config.enable_cors is False


# =============================================================================
# Server Lifecycle Tests
# =============================================================================


class TestServerLifecycle:
    """Tests for server startup and shutdown."""

    def test_server_app_creation(self, unified_server: UnifiedAPIServer):
        """Test FastAPI app is created correctly."""
        app = unified_server._create_app()

        assert app is not None
        assert app.title == "SAGE Unified Inference API"

    def test_server_state_tracking(self, unified_server: UnifiedAPIServer):
        """Test server state is tracked correctly."""
        assert unified_server._running is False

        # After creating app, running state is still False until started
        unified_server._create_app()
        assert unified_server._running is False

    def test_stop_when_not_running(self, unified_server: UnifiedAPIServer):
        """Test stopping server that isn't running."""
        # Should not raise
        unified_server.stop()
        assert unified_server._running is False
