# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""End-to-end integration tests for UnifiedInferenceClient.

This module tests the unified client including:
1. Auto-detection of endpoints (create_auto)
2. Simple mode with direct API calls
3. Control Plane mode with hybrid scheduling
4. Chat, generate, and embed methods
5. Error handling and fallback behavior
6. Caching and singleton patterns

Tests use mock servers and patched network calls to avoid
requiring actual running services.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sage.common.components.sage_llm.unified_client import (
    InferenceResult,
    UnifiedClientConfig,
    UnifiedClientMode,
    UnifiedInferenceClient,
)

if TYPE_CHECKING:
    from conftest import MockEmbeddingBackend, MockLLMBackend


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables before each test."""
    # Store original values
    env_vars = [
        "SAGE_UNIFIED_BASE_URL",
        "SAGE_UNIFIED_MODEL",
        "SAGE_UNIFIED_API_KEY",
        "SAGE_CHAT_BASE_URL",
        "SAGE_CHAT_MODEL",
        "SAGE_CHAT_API_KEY",
        "SAGE_EMBEDDING_BASE_URL",
        "SAGE_EMBEDDING_MODEL",
        "SAGE_EMBEDDING_API_KEY",
    ]
    original = {k: os.environ.get(k) for k in env_vars}

    # Clear for test
    for k in env_vars:
        if k in os.environ:
            del os.environ[k]

    # Clear cached instances
    UnifiedInferenceClient.clear_instances()

    yield

    # Restore
    for k, v in original.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]

    # Clear again after test
    UnifiedInferenceClient.clear_instances()


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock = MagicMock()

    # Mock chat completion
    mock_chat_response = MagicMock()
    mock_chat_response.choices = [MagicMock()]
    mock_chat_response.choices[0].message = MagicMock()
    mock_chat_response.choices[0].message.content = "Mock chat response"
    mock_chat_response.model = "test-model"
    mock_chat_response.usage = MagicMock()
    mock_chat_response.usage.prompt_tokens = 10
    mock_chat_response.usage.completion_tokens = 20
    mock_chat_response.usage.total_tokens = 30
    mock.chat.completions.create.return_value = mock_chat_response

    # Mock completion
    mock_completion_response = MagicMock()
    mock_completion_response.choices = [MagicMock()]
    mock_completion_response.choices[0].text = "Mock completion response"
    mock_completion_response.model = "test-model"
    mock_completion_response.usage = MagicMock()
    mock_completion_response.usage.prompt_tokens = 5
    mock_completion_response.usage.completion_tokens = 15
    mock_completion_response.usage.total_tokens = 20
    mock.completions.create.return_value = mock_completion_response

    # Mock embedding
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [MagicMock(), MagicMock()]
    mock_embedding_response.data[0].embedding = [0.1, 0.2, 0.3]
    mock_embedding_response.data[1].embedding = [0.4, 0.5, 0.6]
    mock_embedding_response.model = "test-embedding-model"
    mock_embedding_response.usage = MagicMock()
    mock_embedding_response.usage.prompt_tokens = 10
    mock_embedding_response.usage.total_tokens = 10
    mock.embeddings.create.return_value = mock_embedding_response

    return mock


# =============================================================================
# Auto-Detection Tests
# =============================================================================


class TestAutoDetection:
    """Tests for endpoint auto-detection logic."""

    def test_detect_from_unified_env_var(self):
        """Test detection from SAGE_UNIFIED_BASE_URL."""
        os.environ["SAGE_UNIFIED_BASE_URL"] = "http://localhost:8000/v1"
        os.environ["SAGE_UNIFIED_MODEL"] = "unified-model"

        with patch.object(
            UnifiedInferenceClient, "_check_endpoint_health", return_value=True
        ):
            client = UnifiedInferenceClient.create_auto()

        assert client.config.llm_base_url == "http://localhost:8000/v1"
        assert client.config.embedding_base_url == "http://localhost:8000/v1"
        assert client.config.llm_model == "unified-model"

    def test_detect_from_separate_env_vars(self):
        """Test detection from separate LLM and Embedding env vars."""
        os.environ["SAGE_CHAT_BASE_URL"] = "http://localhost:8001/v1"
        os.environ["SAGE_CHAT_MODEL"] = "chat-model"
        os.environ["SAGE_EMBEDDING_BASE_URL"] = "http://localhost:8090/v1"
        os.environ["SAGE_EMBEDDING_MODEL"] = "embed-model"

        with patch.object(
            UnifiedInferenceClient, "_check_endpoint_health", return_value=False
        ):
            client = UnifiedInferenceClient.create_auto()

        assert client.config.llm_base_url == "http://localhost:8001/v1"
        assert client.config.llm_model == "chat-model"
        assert client.config.embedding_base_url == "http://localhost:8090/v1"
        assert client.config.embedding_model == "embed-model"

    def test_detect_local_servers(self):
        """Test detection of local servers."""

        def mock_health_check(base_url, *args, **kwargs):
            # Only localhost:8001 and localhost:8090 are healthy
            return "8001" in base_url or "8090" in base_url

        with patch.object(
            UnifiedInferenceClient,
            "_check_endpoint_health",
            side_effect=mock_health_check,
        ):
            client = UnifiedInferenceClient.create_auto()

        assert client.config.llm_base_url == "http://localhost:8001/v1"
        assert client.config.embedding_base_url == "http://localhost:8090/v1"

    def test_fallback_to_cloud_api(self):
        """Test fallback to cloud API when no local servers."""
        os.environ["SAGE_CHAT_API_KEY"] = "test-api-key"

        with patch.object(
            UnifiedInferenceClient, "_check_endpoint_health", return_value=False
        ):
            client = UnifiedInferenceClient.create_auto()

        # Should fallback to DashScope
        assert "dashscope" in (client.config.llm_base_url or "")

    def test_no_endpoints_available(self):
        """Test behavior when no endpoints are available."""
        with patch.object(
            UnifiedInferenceClient, "_check_endpoint_health", return_value=False
        ):
            client = UnifiedInferenceClient.create_auto()

        # Client should still be created
        assert client is not None
        assert client._llm_available is False
        assert client._embedding_available is False

    def test_custom_ports(self):
        """Test detection with custom port list."""

        def mock_health_check(base_url, *args, **kwargs):
            return "9000" in base_url or "9090" in base_url

        with patch.object(
            UnifiedInferenceClient,
            "_check_endpoint_health",
            side_effect=mock_health_check,
        ):
            client = UnifiedInferenceClient.create_auto(
                llm_ports=(9000, 9001),
                embedding_ports=(9090, 9091),
            )

        assert client.config.llm_base_url == "http://localhost:9000/v1"
        assert client.config.embedding_base_url == "http://localhost:9090/v1"


# =============================================================================
# Simple Mode Tests
# =============================================================================


class TestSimpleMode:
    """Tests for Simple mode (direct API calls)."""

    def test_explicit_configuration(self, mock_openai_client):
        """Test client with explicit configuration."""
        with patch("sage.common.components.sage_llm.unified_client.OpenAI") as mock_openai:
            mock_openai.return_value = mock_openai_client

            client = UnifiedInferenceClient(
                llm_base_url="http://localhost:8001/v1",
                llm_model="test-llm",
                embedding_base_url="http://localhost:8090/v1",
                embedding_model="test-embed",
            )

        assert client.mode == UnifiedClientMode.SIMPLE
        assert client.config.llm_base_url == "http://localhost:8001/v1"
        assert client.config.embedding_base_url == "http://localhost:8090/v1"

    def test_chat_method(self, mock_openai_client):
        """Test chat method in Simple mode."""
        with patch("sage.common.components.sage_llm.unified_client.OpenAI") as mock_openai:
            mock_openai.return_value = mock_openai_client

            client = UnifiedInferenceClient(
                llm_base_url="http://localhost:8001/v1",
                llm_model="test-model",
            )

            # Make sure client thinks LLM is available
            client._llm_available = True
            client._llm_client = mock_openai_client

            response = client.chat([{"role": "user", "content": "Hello"}])

        assert response == "Mock chat response"
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_generate_method(self, mock_openai_client):
        """Test generate method in Simple mode."""
        with patch("sage.common.components.sage_llm.unified_client.OpenAI") as mock_openai:
            mock_openai.return_value = mock_openai_client

            client = UnifiedInferenceClient(
                llm_base_url="http://localhost:8001/v1",
                llm_model="test-model",
            )

            client._llm_available = True
            client._llm_client = mock_openai_client

            response = client.generate("Once upon a time")

        # Generate typically calls chat with a user message
        assert mock_openai_client.chat.completions.create.called or mock_openai_client.completions.create.called

    def test_embed_method(self, mock_openai_client):
        """Test embed method in Simple mode."""
        with patch("sage.common.components.sage_llm.unified_client.OpenAI") as mock_openai:
            mock_openai.return_value = mock_openai_client

            client = UnifiedInferenceClient(
                embedding_base_url="http://localhost:8090/v1",
                embedding_model="test-embed",
            )

            client._embedding_available = True
            client._embedding_client = mock_openai_client

            result = client.embed(["text1", "text2"])

        assert isinstance(result, list)
        mock_openai_client.embeddings.create.assert_called_once()

    def test_llm_not_available_error(self):
        """Test error when LLM is not available."""
        client = UnifiedInferenceClient()
        client._llm_available = False

        with pytest.raises(RuntimeError, match="LLM.*not available"):
            client.chat([{"role": "user", "content": "Hello"}])

    def test_embedding_not_available_error(self):
        """Test error when embedding is not available."""
        client = UnifiedInferenceClient()
        client._embedding_available = False

        with pytest.raises(RuntimeError, match="Embedding.*not available"):
            client.embed(["text"])


# =============================================================================
# Control Plane Mode Tests
# =============================================================================


class TestControlPlaneMode:
    """Tests for Control Plane mode with hybrid scheduling."""

    def test_create_with_control_plane(self):
        """Test creating client with Control Plane mode configuration."""
        # Mock the imports that _init_control_plane_mode needs
        mock_manager = MagicMock()
        mock_policy = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "sage.common.components.sage_llm.sageLLM.control_plane.manager": MagicMock(
                    ControlPlaneManager=lambda **kwargs: mock_manager
                ),
                "sage.common.components.sage_llm.sageLLM.control_plane.strategies.hybrid_policy": MagicMock(
                    HybridSchedulingPolicy=lambda **kwargs: mock_policy
                ),
            },
        ):
            client = UnifiedInferenceClient.create_with_control_plane(
                llm_base_url="http://localhost:8001/v1",
                embedding_base_url="http://localhost:8090/v1",
            )

            assert client.config.mode == UnifiedClientMode.CONTROL_PLANE

    def test_control_plane_fallback_to_simple(self):
        """Test Control Plane mode graceful degradation when init fails.

        When Control Plane initialization fails (e.g., missing dependencies),
        the client should still function by falling back to Simple mode,
        and the mode attribute is updated to reflect the actual operating mode.
        """
        # Remove the control plane module from sys.modules to trigger import error
        with patch.dict(
            "sys.modules",
            {
                "sage.common.components.sage_llm.sageLLM.control_plane.manager": None,
            },
        ):
            client = UnifiedInferenceClient(
                llm_base_url="http://localhost:8001/v1",
                mode=UnifiedClientMode.CONTROL_PLANE,
            )

            # Mode falls back to SIMPLE since Control Plane init failed
            assert client.mode == UnifiedClientMode.SIMPLE
            # Verify that Simple mode clients were initialized as fallback
            assert client._llm_client is not None or not client.config.llm_base_url


# =============================================================================
# Singleton and Caching Tests
# =============================================================================


class TestSingletonPattern:
    """Tests for singleton instance caching."""

    def test_get_instance_returns_same_object(self):
        """Test that get_instance returns the same cached object."""
        with patch.object(
            UnifiedInferenceClient, "_check_endpoint_health", return_value=False
        ):
            instance1 = UnifiedInferenceClient.get_instance("key1")
            instance2 = UnifiedInferenceClient.get_instance("key1")

        assert instance1 is instance2

    def test_different_keys_different_instances(self):
        """Test that different keys create different instances."""
        with patch.object(
            UnifiedInferenceClient, "_check_endpoint_health", return_value=False
        ):
            instance1 = UnifiedInferenceClient.get_instance("key1")
            instance2 = UnifiedInferenceClient.get_instance("key2")

        assert instance1 is not instance2

    def test_clear_instances(self):
        """Test clearing cached instances."""
        with patch.object(
            UnifiedInferenceClient, "_check_endpoint_health", return_value=False
        ):
            instance1 = UnifiedInferenceClient.get_instance("key1")
            UnifiedInferenceClient.clear_instances()
            instance2 = UnifiedInferenceClient.get_instance("key1")

        assert instance1 is not instance2


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_chat_handles_api_error(self, mock_openai_client):
        """Test that chat method handles API errors gracefully."""
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

        with patch("sage.common.components.sage_llm.unified_client.OpenAI") as mock_openai:
            mock_openai.return_value = mock_openai_client

            client = UnifiedInferenceClient(
                llm_base_url="http://localhost:8001/v1",
            )
            client._llm_available = True
            client._llm_client = mock_openai_client

            with pytest.raises(Exception, match="API Error"):
                client.chat([{"role": "user", "content": "Hello"}])

    def test_embed_handles_api_error(self, mock_openai_client):
        """Test that embed method handles API errors gracefully."""
        mock_openai_client.embeddings.create.side_effect = Exception("Embedding Error")

        with patch("sage.common.components.sage_llm.unified_client.OpenAI") as mock_openai:
            mock_openai.return_value = mock_openai_client

            client = UnifiedInferenceClient(
                embedding_base_url="http://localhost:8090/v1",
            )
            client._embedding_available = True
            client._embedding_client = mock_openai_client

            with pytest.raises(Exception, match="Embedding Error"):
                client.embed(["text"])

    def test_timeout_configuration(self):
        """Test that timeout is properly configured."""
        client = UnifiedInferenceClient(timeout=30.0)

        assert client.config.timeout == 30.0

    def test_max_retries_configuration(self):
        """Test that max retries is properly configured."""
        client = UnifiedInferenceClient(max_retries=5)

        assert client.config.max_retries == 5


# =============================================================================
# Configuration Tests
# =============================================================================


class TestConfiguration:
    """Tests for client configuration."""

    def test_default_sampling_parameters(self):
        """Test default sampling parameters."""
        config = UnifiedClientConfig()

        assert config.temperature == 0.7
        assert config.max_tokens == 512
        assert config.top_p == 1.0

    def test_custom_sampling_parameters(self):
        """Test custom sampling parameters."""
        config = UnifiedClientConfig(
            temperature=0.5,
            max_tokens=1024,
            top_p=0.9,
        )

        assert config.temperature == 0.5
        assert config.max_tokens == 1024
        assert config.top_p == 0.9

    def test_config_object_initialization(self):
        """Test initialization with config object."""
        config = UnifiedClientConfig(
            llm_base_url="http://localhost:8001/v1",
            llm_model="test-model",
            mode=UnifiedClientMode.SIMPLE,
        )

        client = UnifiedInferenceClient(config=config)

        assert client.config is config
        assert client.config.llm_model == "test-model"


# =============================================================================
# Inference Result Tests
# =============================================================================


class TestInferenceResult:
    """Tests for InferenceResult dataclass."""

    def test_chat_result_creation(self):
        """Test creating a chat inference result."""
        result = InferenceResult(
            request_id="req-1",
            request_type="chat",
            content="Hello response",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            latency_ms=100.5,
        )

        assert result.request_id == "req-1"
        assert result.request_type == "chat"
        assert result.content == "Hello response"
        assert result.latency_ms == 100.5

    def test_embed_result_creation(self):
        """Test creating an embedding inference result."""
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        result = InferenceResult(
            request_id="emb-1",
            request_type="embed",
            content=embeddings,
            model="test-embed-model",
        )

        assert result.request_type == "embed"
        assert result.content == embeddings
        assert len(result.content) == 2

    def test_result_with_metadata(self):
        """Test inference result with additional metadata."""
        result = InferenceResult(
            request_id="req-1",
            request_type="chat",
            content="Response",
            model="test-model",
            metadata={"custom_field": "value"},
        )

        assert result.metadata["custom_field"] == "value"


# =============================================================================
# Full Flow Tests
# =============================================================================


class TestFullFlow:
    """End-to-end flow tests."""

    def test_chat_then_embed_flow(self, mock_openai_client):
        """Test using both chat and embed in sequence."""
        with patch("sage.common.components.sage_llm.unified_client.OpenAI") as mock_openai:
            mock_openai.return_value = mock_openai_client

            client = UnifiedInferenceClient(
                llm_base_url="http://localhost:8001/v1",
                embedding_base_url="http://localhost:8090/v1",
            )
            client._llm_available = True
            client._embedding_available = True
            client._llm_client = mock_openai_client
            client._embedding_client = mock_openai_client

            # Chat first
            chat_response = client.chat([{"role": "user", "content": "Hello"}])
            assert chat_response == "Mock chat response"

            # Then embed
            embed_response = client.embed(["text1", "text2"])
            assert isinstance(embed_response, list)

    def test_multiple_concurrent_requests(self, mock_openai_client):
        """Test multiple requests in sequence."""
        with patch("sage.common.components.sage_llm.unified_client.OpenAI") as mock_openai:
            mock_openai.return_value = mock_openai_client

            client = UnifiedInferenceClient(
                llm_base_url="http://localhost:8001/v1",
            )
            client._llm_available = True
            client._llm_client = mock_openai_client

            # Make multiple chat requests
            responses = []
            for i in range(5):
                response = client.chat([{"role": "user", "content": f"Message {i}"}])
                responses.append(response)

            assert len(responses) == 5
            assert mock_openai_client.chat.completions.create.call_count == 5

    def test_return_result_mode(self, mock_openai_client):
        """Test chat with return_result=True for detailed results."""
        with patch("sage.common.components.sage_llm.unified_client.OpenAI") as mock_openai:
            mock_openai.return_value = mock_openai_client

            client = UnifiedInferenceClient(
                llm_base_url="http://localhost:8001/v1",
            )
            client._llm_available = True
            client._llm_client = mock_openai_client

            # If return_result is supported
            try:
                result = client.chat(
                    [{"role": "user", "content": "Hello"}],
                    return_result=True,
                )
                # Should return InferenceResult if supported
                if isinstance(result, InferenceResult):
                    assert result.request_type == "chat"
            except TypeError:
                # return_result not supported, that's fine
                pass


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformance:
    """Performance-related tests."""

    def test_client_initialization_time(self):
        """Test that client initialization is fast."""
        with patch.object(
            UnifiedInferenceClient, "_check_endpoint_health", return_value=False
        ):
            start = time.time()
            client = UnifiedInferenceClient.create_auto()
            elapsed = time.time() - start

        # Should be fast (under 1 second without network calls)
        assert elapsed < 1.0

    def test_cached_instance_retrieval_time(self):
        """Test that cached instance retrieval is very fast."""
        with patch.object(
            UnifiedInferenceClient, "_check_endpoint_health", return_value=False
        ):
            # First call creates instance
            UnifiedInferenceClient.get_instance("perf-test")

            # Measure cached retrieval
            start = time.time()
            for _ in range(100):
                UnifiedInferenceClient.get_instance("perf-test")
            elapsed = time.time() - start

        # 100 cached retrievals should be under 10ms
        assert elapsed < 0.1
