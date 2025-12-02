# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Unit tests for UnifiedInferenceClient.

Tests the unified client that combines LLM and Embedding capabilities
via Control Plane mode (unified entry point).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from sage.common.components.sage_llm.unified_client import (
    InferenceResult,
    UnifiedClientConfig,
    UnifiedClientMode,
    UnifiedInferenceClient,
)

if TYPE_CHECKING:
    pass


class TestUnifiedClientConfig:
    """Tests for UnifiedClientConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = UnifiedClientConfig()

        assert config.llm_base_url is None
        assert config.llm_model is None
        assert config.llm_api_key == ""
        assert config.embedding_base_url is None
        assert config.embedding_model is None
        assert config.embedding_api_key == ""
        assert config.timeout == 60.0
        assert config.max_retries == 3
        assert config.temperature == 0.7
        assert config.max_tokens == 512
        assert config.top_p == 1.0

    def test_custom_values(self):
        """Test configuration with custom values."""
        config = UnifiedClientConfig(
            llm_base_url="http://localhost:8001/v1",
            llm_model="qwen-7b",
            llm_api_key="test-key",  # pragma: allowlist secret
            embedding_base_url="http://localhost:8090/v1",
            embedding_model="bge-m3",
            timeout=30.0,
            max_retries=5,
            temperature=0.5,
        )

        assert config.llm_base_url == "http://localhost:8001/v1"
        assert config.llm_model == "qwen-7b"
        assert config.llm_api_key == "test-key"  # pragma: allowlist secret
        assert config.embedding_base_url == "http://localhost:8090/v1"
        assert config.embedding_model == "bge-m3"
        assert config.timeout == 30.0
        assert config.max_retries == 5
        assert config.temperature == 0.5


class TestUnifiedClientMode:
    """Tests for UnifiedClientMode constants."""

    def test_control_plane_mode(self):
        """Test CONTROL_PLANE mode value."""
        assert UnifiedClientMode.CONTROL_PLANE == "control_plane"


class TestInferenceResult:
    """Tests for InferenceResult dataclass."""

    def test_chat_result(self):
        """Test creating a chat inference result."""
        result = InferenceResult(
            request_id="req-123",
            request_type="chat",
            content="Hello, world.",
            model="qwen-7b",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            latency_ms=100.5,
        )

        assert result.request_id == "req-123"
        assert result.request_type == "chat"
        assert result.content == "Hello, world."
        assert result.model == "qwen-7b"
        assert result.usage["total_tokens"] == 15
        assert result.latency_ms == 100.5

    def test_embed_result(self):
        """Test creating an embedding inference result."""
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        result = InferenceResult(
            request_id="emb-456",
            request_type="embed",
            content=embeddings,
            model="bge-m3",
            usage={"prompt_tokens": 20},
            latency_ms=50.0,
        )

        assert result.request_id == "emb-456"
        assert result.request_type == "embed"
        assert result.content == embeddings
        assert len(result.content) == 2


class TestUnifiedInferenceClientCreate:
    """Tests for UnifiedInferenceClient.create() factory method."""

    def test_direct_init_blocked(self):
        """Test that direct instantiation is blocked."""
        with pytest.raises(RuntimeError, match="Use UnifiedInferenceClient.create"):
            UnifiedInferenceClient(
                llm_base_url="http://localhost:8001/v1",
                llm_model="qwen-7b",
            )

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    def test_create_with_auto_detection(self, mock_embed_detect, mock_llm_detect):
        """Test create() with auto-detection of endpoints."""
        mock_llm_detect.return_value = ("http://localhost:8001/v1", "qwen-7b", "")
        mock_embed_detect.return_value = ("http://localhost:8090/v1", "bge-m3", "")

        client = UnifiedInferenceClient.create()

        assert client.config.llm_base_url == "http://localhost:8001/v1"
        assert client.config.llm_model == "qwen-7b"
        assert client.config.embedding_base_url == "http://localhost:8090/v1"
        assert client.config.embedding_model == "bge-m3"

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    def test_create_with_explicit_models(self, mock_embed_detect, mock_llm_detect):
        """Test create() with explicit model names."""
        mock_llm_detect.return_value = ("http://localhost:8001/v1", None, "")
        mock_embed_detect.return_value = ("http://localhost:8090/v1", None, "")

        client = UnifiedInferenceClient.create(
            default_llm_model="custom-llm",
            default_embedding_model="custom-embed",
        )

        assert client.config.llm_model == "custom-llm"
        assert client.config.embedding_model == "custom-embed"


class TestUnifiedClientProperties:
    """Tests for UnifiedInferenceClient properties."""

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    def test_is_llm_available(self, mock_embed_detect, mock_llm_detect):
        """Test is_llm_available property."""
        mock_llm_detect.return_value = (None, None, "")
        mock_embed_detect.return_value = (None, None, "")

        client = UnifiedInferenceClient.create()
        assert client.is_llm_available == client._llm_available

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    def test_is_embedding_available(self, mock_embed_detect, mock_llm_detect):
        """Test is_embedding_available property."""
        mock_llm_detect.return_value = (None, None, "")
        mock_embed_detect.return_value = (None, None, "")

        client = UnifiedInferenceClient.create()
        assert client.is_embedding_available == client._embedding_available

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    def test_is_control_plane_mode(self, mock_embed_detect, mock_llm_detect):
        """Test is_control_plane_mode property.

        Note: With the new unified create() entry point, Control Plane mode
        is always enabled (manager is always initialized).
        """
        mock_llm_detect.return_value = (None, None, "")
        mock_embed_detect.return_value = (None, None, "")

        client = UnifiedInferenceClient.create()
        # New behavior: Control Plane mode is always enabled
        assert client.is_control_plane_mode is True

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    def test_get_status(self, mock_embed_detect, mock_llm_detect):
        """Test get_status method."""
        mock_llm_detect.return_value = ("http://localhost:8001/v1", "qwen-7b", "")
        mock_embed_detect.return_value = (None, None, "")

        client = UnifiedInferenceClient.create()
        status = client.get_status()

        assert "mode" in status
        assert "llm_available" in status
        assert "embedding_available" in status
        assert "llm_base_url" in status
        assert "embedding_base_url" in status


class TestUnifiedClientEndpointDetection:
    """Tests for endpoint detection methods."""

    @patch("sage.common.components.sage_llm.unified_client.os.environ", {})
    @patch.object(UnifiedInferenceClient, "_check_endpoint_health", return_value=False)
    def test_detect_llm_endpoint_no_endpoints(self, mock_health):
        """Test LLM endpoint detection when no endpoints available."""
        base_url, model, api_key = UnifiedInferenceClient._detect_llm_endpoint()

        assert base_url is None
        assert model is None
        assert api_key == ""

    @patch(
        "sage.common.components.sage_llm.unified_client.os.environ",
        {
            "SAGE_CHAT_BASE_URL": "http://test:8001/v1",
            "SAGE_CHAT_MODEL": "test-model",
            "SAGE_CHAT_API_KEY": "test-key",  # pragma: allowlist secret
        },
    )
    def test_detect_llm_endpoint_from_env(self):
        """Test LLM endpoint detection from environment variables."""
        base_url, model, api_key = UnifiedInferenceClient._detect_llm_endpoint()

        assert base_url == "http://test:8001/v1"
        assert model == "test-model"
        assert api_key == "test-key"  # pragma: allowlist secret

    @patch("sage.common.components.sage_llm.unified_client.os.environ", {})
    @patch.object(UnifiedInferenceClient, "_check_endpoint_health", return_value=True)
    def test_detect_llm_endpoint_local_server(self, mock_health):
        """Test LLM endpoint detection finds local server."""
        base_url, model, api_key = UnifiedInferenceClient._detect_llm_endpoint(
            prefer_local=True,
            ports=(8001, 8000),
        )

        assert base_url == "http://localhost:8001/v1"
        assert model is None
        assert api_key == ""

    @patch("sage.common.components.sage_llm.unified_client.os.environ", {})
    @patch.object(UnifiedInferenceClient, "_check_endpoint_health", return_value=False)
    def test_detect_embedding_endpoint_no_endpoints(self, mock_health):
        """Test Embedding endpoint detection when no endpoints available."""
        base_url, model, api_key = UnifiedInferenceClient._detect_embedding_endpoint()

        assert base_url is None
        assert model is None
        assert api_key == ""

    @patch(
        "sage.common.components.sage_llm.unified_client.os.environ",
        {
            "SAGE_EMBEDDING_BASE_URL": "http://test:8090/v1",
            "SAGE_EMBEDDING_MODEL": "bge-m3",
        },
    )
    def test_detect_embedding_endpoint_from_env(self):
        """Test Embedding endpoint detection from environment variables."""
        base_url, model, api_key = UnifiedInferenceClient._detect_embedding_endpoint()

        assert base_url == "http://test:8090/v1"
        assert model == "bge-m3"


class TestUnifiedClientHealthCheck:
    """Tests for endpoint health check."""

    @patch("sage.common.components.sage_llm.unified_client.httpx.Client")
    def test_check_endpoint_health_models_endpoint(self, mock_client_class):
        """Test health check using /models endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = UnifiedInferenceClient._check_endpoint_health("http://localhost:8001/v1")

        assert result is True

    @patch("sage.common.components.sage_llm.unified_client.httpx.Client")
    def test_check_endpoint_health_failure(self, mock_client_class):
        """Test health check when endpoint is down."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client_class.return_value = mock_client

        result = UnifiedInferenceClient._check_endpoint_health("http://localhost:8001/v1")

        assert result is False


class TestUnifiedClientChat:
    """Tests for chat method."""

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    def test_chat_no_llm_available(self, mock_embed_detect, mock_llm_detect):
        """Test chat raises error when LLM not available."""
        mock_llm_detect.return_value = (None, None, "")
        mock_embed_detect.return_value = (None, None, "")

        client = UnifiedInferenceClient.create()

        with pytest.raises(RuntimeError, match="LLM endpoint not available"):
            client.chat([{"role": "user", "content": "Hello"}])

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    @patch.object(UnifiedInferenceClient, "_get_default_llm_model", return_value="test-model")
    def test_chat_mode(self, mock_get_model, mock_embed_detect, mock_llm_detect):
        """Test chat method."""
        mock_llm_detect.return_value = ("http://localhost:8001/v1", "qwen-7b", "")
        mock_embed_detect.return_value = (None, None, "")

        client = UnifiedInferenceClient.create()
        client._llm_available = True

        # Mock the OpenAI client
        mock_response = MagicMock()
        mock_response.id = "resp-123"
        mock_response.model = "qwen-7b"
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello."
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        client._llm_client = MagicMock()
        client._llm_client.chat.completions.create.return_value = mock_response

        result = client.chat([{"role": "user", "content": "Hi"}])

        assert result == "Hello."

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    @patch.object(UnifiedInferenceClient, "_get_default_llm_model", return_value="test-model")
    def test_chat_with_return_result(self, mock_get_model, mock_embed_detect, mock_llm_detect):
        """Test chat with return_result=True."""
        mock_llm_detect.return_value = ("http://localhost:8001/v1", "qwen-7b", "")
        mock_embed_detect.return_value = (None, None, "")

        client = UnifiedInferenceClient.create()
        client._llm_available = True

        mock_response = MagicMock()
        mock_response.id = "resp-123"
        mock_response.model = "qwen-7b"
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello."
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        client._llm_client = MagicMock()
        client._llm_client.chat.completions.create.return_value = mock_response

        result = client.chat(
            [{"role": "user", "content": "Hi"}],
            return_result=True,
        )

        assert isinstance(result, InferenceResult)
        assert result.request_type == "chat"
        assert result.content == "Hello."


class TestUnifiedClientGenerate:
    """Tests for generate method."""

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    def test_generate_no_llm_available(self, mock_embed_detect, mock_llm_detect):
        """Test generate raises error when LLM not available."""
        mock_llm_detect.return_value = (None, None, "")
        mock_embed_detect.return_value = (None, None, "")

        client = UnifiedInferenceClient.create()

        with pytest.raises(RuntimeError, match="LLM endpoint not available"):
            client.generate("Hello")

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    @patch.object(UnifiedInferenceClient, "_get_default_llm_model", return_value="test-model")
    def test_generate_mode(self, mock_get_model, mock_embed_detect, mock_llm_detect):
        """Test generate method."""
        mock_llm_detect.return_value = ("http://localhost:8001/v1", "qwen-7b", "")
        mock_embed_detect.return_value = (None, None, "")

        client = UnifiedInferenceClient.create()
        client._llm_available = True

        # Mock the OpenAI client (completions API)
        mock_response = MagicMock()
        mock_response.id = "gen-123"
        mock_response.model = "qwen-7b"
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].text = "Once upon a time..."
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 10
        mock_response.usage.total_tokens = 15

        client._llm_client = MagicMock()
        client._llm_client.completions.create.return_value = mock_response

        result = client.generate("Once upon")

        assert result == "Once upon a time..."


class TestUnifiedClientEmbed:
    """Tests for embed method."""

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    def test_embed_no_embedding_available(self, mock_embed_detect, mock_llm_detect):
        """Test embed raises error when embedding not available."""
        mock_llm_detect.return_value = (None, None, "")
        mock_embed_detect.return_value = (None, None, "")

        client = UnifiedInferenceClient.create()

        with pytest.raises(RuntimeError, match="Embedding endpoint not available"):
            client.embed(["Hello"])

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    @patch.object(UnifiedInferenceClient, "_get_default_embedding_model", return_value="bge-m3")
    def test_embed_single_text(self, mock_get_model, mock_embed_detect, mock_llm_detect):
        """Test embed with single text input."""
        mock_llm_detect.return_value = (None, None, "")
        mock_embed_detect.return_value = ("http://localhost:8090/v1", "bge-m3", "")

        client = UnifiedInferenceClient.create()
        client._embedding_available = True

        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1, 0.2, 0.3]

        mock_response = MagicMock()
        mock_response.data = [mock_embedding]
        mock_response.model = "bge-m3"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.total_tokens = 5

        client._embedding_client = MagicMock()
        client._embedding_client.embeddings.create.return_value = mock_response

        result = client.embed("Hello")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    @patch.object(UnifiedInferenceClient, "_get_default_embedding_model", return_value="bge-m3")
    def test_embed_multiple_texts(self, mock_get_model, mock_embed_detect, mock_llm_detect):
        """Test embed with multiple texts."""
        mock_llm_detect.return_value = (None, None, "")
        mock_embed_detect.return_value = ("http://localhost:8090/v1", "bge-m3", "")

        client = UnifiedInferenceClient.create()
        client._embedding_available = True

        mock_embedding1 = MagicMock()
        mock_embedding1.embedding = [0.1, 0.2, 0.3]
        mock_embedding2 = MagicMock()
        mock_embedding2.embedding = [0.4, 0.5, 0.6]

        mock_response = MagicMock()
        mock_response.data = [mock_embedding1, mock_embedding2]
        mock_response.model = "bge-m3"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.total_tokens = 10

        client._embedding_client = MagicMock()
        client._embedding_client.embeddings.create.return_value = mock_response

        result = client.embed(["Hello", "World"])

        # Result should be list of embeddings when return_result=False (default)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    @patch.object(UnifiedInferenceClient, "_get_default_embedding_model", return_value="bge-m3")
    def test_embed_with_return_result(self, mock_get_model, mock_embed_detect, mock_llm_detect):
        """Test embed with return_result=True."""
        mock_llm_detect.return_value = (None, None, "")
        mock_embed_detect.return_value = ("http://localhost:8090/v1", "bge-m3", "")

        client = UnifiedInferenceClient.create()
        client._embedding_available = True

        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1, 0.2, 0.3]

        mock_response = MagicMock()
        mock_response.data = [mock_embedding]
        mock_response.model = "bge-m3"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.total_tokens = 5

        client._embedding_client = MagicMock()
        client._embedding_client.embeddings.create.return_value = mock_response

        result = client.embed("Hello", return_result=True)

        assert isinstance(result, InferenceResult)
        assert result.request_type == "embed"
        assert result.content == [[0.1, 0.2, 0.3]]


class TestUnifiedClientSingleton:
    """Tests for singleton/instance caching."""

    def test_get_instance_creates_new(self):
        """Test get_instance creates new instance."""
        UnifiedInferenceClient.clear_instances()

        with patch.object(UnifiedInferenceClient, "create") as mock_create:
            mock_create.return_value = MagicMock(spec=UnifiedInferenceClient)
            _client = UnifiedInferenceClient.get_instance("test-key")  # noqa: F841

            mock_create.assert_called_once()

    def test_get_instance_returns_cached(self):
        """Test get_instance returns cached instance."""
        UnifiedInferenceClient.clear_instances()

        with patch.object(UnifiedInferenceClient, "create") as mock_create:
            mock_instance = MagicMock(spec=UnifiedInferenceClient)
            mock_create.return_value = mock_instance

            client1 = UnifiedInferenceClient.get_instance("test-key")
            client2 = UnifiedInferenceClient.get_instance("test-key")

            assert client1 is client2
            mock_create.assert_called_once()

    def test_clear_instances(self):
        """Test clear_instances removes all cached instances."""
        UnifiedInferenceClient.clear_instances()

        with patch.object(UnifiedInferenceClient, "create") as mock_create:
            mock_create.return_value = MagicMock(spec=UnifiedInferenceClient)
            UnifiedInferenceClient.get_instance("key1")
            UnifiedInferenceClient.get_instance("key2")

            assert len(UnifiedInferenceClient._instances) == 2

            UnifiedInferenceClient.clear_instances()

            assert len(UnifiedInferenceClient._instances) == 0


class TestUnifiedClientFactoryMethods:
    """Tests for factory methods."""

    @patch.object(UnifiedInferenceClient, "_detect_llm_endpoint")
    @patch.object(UnifiedInferenceClient, "_detect_embedding_endpoint")
    def test_create(self, mock_embed_detect, mock_llm_detect):
        """Test create() factory method."""
        mock_llm_detect.return_value = ("http://localhost:8001/v1", "qwen-7b", "")
        mock_embed_detect.return_value = ("http://localhost:8090/v1", "bge-m3", "")

        client = UnifiedInferenceClient.create()

        assert client.config.llm_base_url == "http://localhost:8001/v1"
        assert client.config.llm_model == "qwen-7b"
        assert client.config.embedding_base_url == "http://localhost:8090/v1"
        assert client.config.embedding_model == "bge-m3"

    @patch(
        "sage.common.components.sage_llm.unified_client.os.environ",
        {
            "SAGE_UNIFIED_BASE_URL": "http://unified:8000/v1",
            "SAGE_UNIFIED_MODEL": "unified-model",
        },
    )
    def test_create_with_unified_env(self):
        """Test create() with unified base URL from environment."""
        client = UnifiedInferenceClient.create()

        assert client.config.llm_base_url == "http://unified:8000/v1"
        assert client.config.embedding_base_url == "http://unified:8000/v1"
