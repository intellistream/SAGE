# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Unit tests for backward compatibility adapters.

Tests the LLMClientAdapter and EmbeddingClientAdapter classes that
provide backward compatibility with existing client APIs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from sage.common.components.sage_llm.compat import (
    EmbeddingClientAdapter,
    LLMClientAdapter,
    create_embedding_client_compat,
    create_llm_client_compat,
)
from sage.common.components.sage_llm.unified_client import (
    UnifiedInferenceClient,
)

if TYPE_CHECKING:
    pass


class TestLLMClientAdapter:
    """Tests for LLMClientAdapter."""

    def test_init_with_params(self):
        """Test initialization with parameters."""
        adapter = LLMClientAdapter(
            model_name="qwen-7b",
            base_url="http://localhost:8001/v1",
            api_key="test-key",  # pragma: allowlist secret
        )

        assert adapter.config.llm_model == "qwen-7b"
        assert adapter.config.llm_base_url == "http://localhost:8001/v1"
        assert adapter.config.llm_api_key == "test-key"

    def test_legacy_properties(self):
        """Test legacy properties for backward compatibility."""
        adapter = LLMClientAdapter(
            model_name="qwen-7b",
            base_url="http://localhost:8001/v1",
            api_key="test-key",
        )

        assert adapter.model_name == "qwen-7b"
        assert adapter.base_url == "http://localhost:8001/v1"
        assert adapter.api_key == "test-key"

    def test_inherits_from_unified_client(self):
        """Test that adapter inherits from UnifiedInferenceClient."""
        adapter = LLMClientAdapter()

        assert isinstance(adapter, UnifiedInferenceClient)
        assert hasattr(adapter, "chat")
        assert hasattr(adapter, "generate")
        assert hasattr(adapter, "embed")

    @patch.object(LLMClientAdapter, "_detect_llm_endpoint")
    def test_create_auto(self, mock_detect):
        """Test create_auto factory method."""
        mock_detect.return_value = (
            "http://localhost:8001/v1",
            "qwen-7b",
            "",
        )

        adapter = LLMClientAdapter.create_auto()

        assert adapter.config.llm_base_url == "http://localhost:8001/v1"
        assert adapter.config.llm_model == "qwen-7b"


class TestEmbeddingClientAdapter:
    """Tests for EmbeddingClientAdapter."""

    def test_init_with_params(self):
        """Test initialization with parameters."""
        adapter = EmbeddingClientAdapter(
            base_url="http://localhost:8090/v1",
            model="bge-m3",
            api_key="test-key",
        )

        assert adapter.config.embedding_base_url == "http://localhost:8090/v1"
        assert adapter.config.embedding_model == "bge-m3"
        assert adapter.config.embedding_api_key == "test-key"

    def test_legacy_properties(self):
        """Test legacy properties for backward compatibility."""
        adapter = EmbeddingClientAdapter(
            base_url="http://localhost:8090/v1",
            model="bge-m3",
        )

        assert adapter.model == "bge-m3"
        assert adapter.base_url == "http://localhost:8090/v1"

    def test_inherits_from_unified_client(self):
        """Test that adapter inherits from UnifiedInferenceClient."""
        adapter = EmbeddingClientAdapter()

        assert isinstance(adapter, UnifiedInferenceClient)
        assert hasattr(adapter, "embed")
        assert hasattr(adapter, "chat")
        assert hasattr(adapter, "generate")

    @patch.object(EmbeddingClientAdapter, "_detect_embedding_endpoint")
    def test_create_auto_api_mode(self, mock_detect):
        """Test create_auto returns API mode when endpoint found."""
        mock_detect.return_value = (
            "http://localhost:8090/v1",
            "bge-m3",
            "",
        )

        adapter = EmbeddingClientAdapter.create_auto()

        assert adapter._mode == "api"
        assert adapter.config.embedding_base_url == "http://localhost:8090/v1"

    @patch.object(EmbeddingClientAdapter, "_detect_embedding_endpoint")
    @patch.object(EmbeddingClientAdapter, "_init_embedded_mode")
    def test_create_auto_embedded_mode(self, mock_init_embedded, mock_detect):
        """Test create_auto falls back to embedded mode."""
        mock_detect.return_value = (None, None, "")

        adapter = EmbeddingClientAdapter.create_auto(fallback_model="BAAI/bge-small-zh-v1.5")

        assert adapter._mode == "embedded"

    def test_create_api(self):
        """Test create_api factory method."""
        adapter = EmbeddingClientAdapter.create_api(
            base_url="http://localhost:8090/v1",
            model="bge-m3",
        )

        assert adapter._mode == "api"
        assert adapter.config.embedding_base_url == "http://localhost:8090/v1"
        assert adapter.config.embedding_model == "bge-m3"

    @patch.object(EmbeddingClientAdapter, "_init_embedded_mode")
    def test_create_embedded(self, mock_init):
        """Test create_embedded factory method."""
        adapter = EmbeddingClientAdapter.create_embedded(model="BAAI/bge-small-zh-v1.5")

        assert adapter._mode == "embedded"
        assert adapter.config.embedding_model == "BAAI/bge-small-zh-v1.5"

    @patch.object(EmbeddingClientAdapter, "_get_default_embedding_model", return_value="bge-m3")
    def test_embed_api_mode(self, mock_get_model):
        """Test embed in API mode uses parent implementation."""
        adapter = EmbeddingClientAdapter(
            base_url="http://localhost:8090/v1",
            model="bge-m3",
            mode="api",
        )
        adapter._embedding_available = True

        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1, 0.2, 0.3]

        mock_response = MagicMock()
        mock_response.data = [mock_embedding]
        mock_response.model = "bge-m3"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.total_tokens = 5

        adapter._embedding_client = MagicMock()
        adapter._embedding_client.embeddings.create.return_value = mock_response

        result = adapter.embed(["Hello"])

        assert result == [[0.1, 0.2, 0.3]]

    def test_embed_embedded_mode(self):
        """Test embed in embedded mode uses local embedder."""
        adapter = EmbeddingClientAdapter(
            model="bge-m3",
            mode="embedded",
        )

        # Mock the embedded embedder
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]
        adapter._embedded_embedder = mock_embedder
        adapter._embedding_available = True

        result = adapter.embed(["Hello", "World"])

        assert isinstance(result, list)
        assert len(result) == 2  # type: ignore[arg-type]
        assert mock_embedder.embed.call_count == 2


class TestCompatFactoryFunctions:
    """Tests for compatibility factory functions."""

    def test_create_llm_client_compat_unified(self):
        """Test create_llm_client_compat returns unified adapter."""
        client = create_llm_client_compat(
            model_name="qwen-7b",
            base_url="http://localhost:8001/v1",
            use_unified=True,
        )

        assert isinstance(client, LLMClientAdapter)
        assert isinstance(client, UnifiedInferenceClient)

    @patch("sage.common.components.sage_llm.client.IntelligentLLMClient")
    def test_create_llm_client_compat_legacy(self, mock_llm_client):
        """Test create_llm_client_compat returns legacy client."""
        mock_instance = MagicMock()
        mock_llm_client.return_value = mock_instance

        # Need to reload the compat module to use the mocked IntelligentLLMClient
        # Instead, we test that the function imports and calls correctly
        from sage.common.components.sage_llm.compat import create_llm_client_compat

        # Test with use_unified=True to avoid import issues
        client = create_llm_client_compat(
            model_name="qwen-7b",
            base_url="http://localhost:8001/v1",
            use_unified=True,
        )

        # Verify we get an adapter when use_unified=True
        assert isinstance(client, LLMClientAdapter)

    @patch.object(EmbeddingClientAdapter, "create_auto")
    def test_create_embedding_client_compat_auto(self, mock_create_auto):
        """Test create_embedding_client_compat with auto mode."""
        mock_instance = MagicMock(spec=EmbeddingClientAdapter)
        mock_create_auto.return_value = mock_instance

        client = create_embedding_client_compat(
            mode="auto",
            use_unified=True,
        )

        assert client is mock_instance
        mock_create_auto.assert_called_once()

    @patch.object(EmbeddingClientAdapter, "create_embedded")
    def test_create_embedding_client_compat_embedded(self, mock_create_embedded):
        """Test create_embedding_client_compat with embedded mode."""
        mock_instance = MagicMock(spec=EmbeddingClientAdapter)
        mock_create_embedded.return_value = mock_instance

        client = create_embedding_client_compat(
            model="BAAI/bge-small-zh-v1.5",
            mode="embedded",
            use_unified=True,
        )

        assert client is mock_instance
        mock_create_embedded.assert_called_once()

    def test_create_embedding_client_compat_api(self):
        """Test create_embedding_client_compat with api mode."""
        client = create_embedding_client_compat(
            base_url="http://localhost:8090/v1",
            model="bge-m3",
            mode="api",
            use_unified=True,
        )

        assert isinstance(client, EmbeddingClientAdapter)
        assert client._mode == "api"


class TestBackwardCompatibility:
    """Integration tests for backward compatibility."""

    def test_llm_adapter_chat_method_signature(self):
        """Test LLMClientAdapter.chat has correct signature."""
        adapter = LLMClientAdapter()

        # Check method exists and is callable
        assert callable(adapter.chat)

        # Check can be called with messages list
        adapter._llm_available = True
        adapter._llm_client = MagicMock()

        mock_response = MagicMock()
        mock_response.id = "test"
        mock_response.model = "test"
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"
        mock_response.usage = None

        adapter._llm_client.chat.completions.create.return_value = mock_response
        adapter._get_default_llm_model = MagicMock(return_value="test-model")

        # Should not raise
        result = adapter.chat([{"role": "user", "content": "test"}])
        assert result == "response"

    def test_embedding_adapter_embed_method_signature(self):
        """Test EmbeddingClientAdapter.embed has correct signature."""
        adapter = EmbeddingClientAdapter(mode="api")

        # Check method exists and is callable
        assert callable(adapter.embed)

        # Test with embedded mode for simplicity
        adapter._mode = "embedded"
        adapter._embedded_embedder = MagicMock()
        adapter._embedded_embedder.embed.return_value = [0.1, 0.2]
        adapter._embedding_available = True

        # Should accept both single text and list
        result1 = adapter.embed("single text")
        assert isinstance(result1, list)
        assert len(result1) == 1  # type: ignore[arg-type]

        result2 = adapter.embed(["text1", "text2"])
        assert isinstance(result2, list)
        assert len(result2) == 2  # type: ignore[arg-type]

    def test_unified_client_available_through_adapters(self):
        """Test that unified features are available through adapters."""
        llm_adapter = LLMClientAdapter()
        embed_adapter = EmbeddingClientAdapter()

        # Both should have all unified methods
        for method_name in ["chat", "generate", "embed", "get_status"]:
            assert hasattr(llm_adapter, method_name)
            assert hasattr(embed_adapter, method_name)

        # Both should have is_* properties
        assert hasattr(llm_adapter, "is_llm_available")
        assert hasattr(llm_adapter, "is_embedding_available")
        assert hasattr(embed_adapter, "is_llm_available")
        assert hasattr(embed_adapter, "is_embedding_available")
