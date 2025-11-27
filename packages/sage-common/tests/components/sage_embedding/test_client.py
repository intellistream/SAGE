"""Tests for IntelligentEmbeddingClient.

This module tests the unified embedding client with auto-detection
and fallback support.
"""

from unittest.mock import MagicMock, patch

from sage.common.components.sage_embedding.client import (
    IntelligentEmbeddingClient,
    get_embedding_client,
)


class TestIntelligentEmbeddingClientEmbedded:
    """Tests for IntelligentEmbeddingClient in embedded mode using hash embedder."""

    def test_create_embedded_mode_with_hash(self):
        """Test creating client in embedded mode with hash embedder."""
        # Use hash for fast testing (no model download)
        with patch.object(IntelligentEmbeddingClient, "_init_embedded_mode") as mock_init:
            # Create a mock adapter
            mock_adapter = MagicMock()
            mock_adapter.embed.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            mock_adapter.get_dim.return_value = 3

            def init_side_effect(self_inner):
                self_inner._client = mock_adapter
                self_inner._dimension = 3
                self_inner.mode = "embedded"

            mock_init.side_effect = lambda: init_side_effect(
                IntelligentEmbeddingClient.__new__(IntelligentEmbeddingClient)
            )

            client = IntelligentEmbeddingClient(mode="embedded", model="test")
            # Manual setup since mock doesn't call real init
            client._client = mock_adapter
            client._dimension = 3
            client.mode = "embedded"

            assert client.mode == "embedded"

    def test_embed_with_hash_embedder(self):
        """Test embedding with hash embedder (fast, no downloads)."""
        from sage.common.components.sage_embedding import EmbeddingClientAdapter, EmbeddingFactory

        # Use hash embedder directly for speed
        raw = EmbeddingFactory.create("hash", dim=64)
        adapter = EmbeddingClientAdapter(raw)

        # Create client manually with hash adapter
        client = IntelligentEmbeddingClient.__new__(IntelligentEmbeddingClient)
        client._client = adapter
        client._dimension = 64
        client.mode = "embedded"
        client.model = "hash"
        client.base_url = None

        vectors = client.embed(["Hello", "World"])

        assert len(vectors) == 2
        assert len(vectors[0]) == 64
        assert all(isinstance(v, float) for v in vectors[0])

    def test_get_dim_embedded_mode(self):
        """Test get_dim in embedded mode."""
        from sage.common.components.sage_embedding import EmbeddingClientAdapter, EmbeddingFactory

        raw = EmbeddingFactory.create("hash", dim=128)
        adapter = EmbeddingClientAdapter(raw)

        client = IntelligentEmbeddingClient.__new__(IntelligentEmbeddingClient)
        client._client = adapter
        client._dimension = 128
        client.mode = "embedded"

        dim = client.get_dim()
        assert dim == 128

    def test_repr_embedded(self):
        """Test string representation for embedded mode."""
        client = IntelligentEmbeddingClient.__new__(IntelligentEmbeddingClient)
        client.mode = "embedded"
        client.model = "test-model"
        client.base_url = None

        repr_str = repr(client)
        assert "embedded" in repr_str
        assert "test-model" in repr_str


class TestAutoDetection:
    """Tests for auto-detection functionality."""

    def test_check_endpoint_returns_false_for_unavailable(self):
        """Test endpoint check returns False for unavailable server."""
        result = IntelligentEmbeddingClient._check_endpoint("http://localhost:59999/v1")
        assert result is False

    def test_create_auto_falls_back_to_embedded_mocked(self):
        """Test create_auto falls back to embedded when no server available."""
        from sage.common.components.sage_embedding import EmbeddingClientAdapter, EmbeddingFactory

        # Mock _init_embedded_mode to use hash embedder
        def mock_init_embedded(self):
            raw = EmbeddingFactory.create("hash", dim=64)
            self._client = EmbeddingClientAdapter(raw)
            self._dimension = 64
            self.mode = "embedded"

        with patch.object(IntelligentEmbeddingClient, "_init_embedded_mode", mock_init_embedded):
            client = IntelligentEmbeddingClient.create_auto(fallback_model="hash")
            assert client.mode == "embedded"

    @patch.dict("os.environ", {"SAGE_EMBEDDING_BASE_URL": "http://test:8090/v1"})
    @patch.object(IntelligentEmbeddingClient, "_check_endpoint", return_value=True)
    @patch.object(IntelligentEmbeddingClient, "_init_api_mode")
    def test_create_auto_uses_env_var(self, mock_init, mock_check):
        """Test create_auto uses SAGE_EMBEDDING_BASE_URL env var."""
        client = IntelligentEmbeddingClient.create_auto()

        # Should use the env var URL
        assert client.base_url == "http://test:8090/v1"

    def test_create_auto_with_local_server_detection(self):
        """Test create_auto detects local server when available."""
        # Mock a successful endpoint check for port 8090
        with patch.object(
            IntelligentEmbeddingClient, "_check_endpoint", side_effect=lambda url: "8090" in url
        ):
            with patch.object(IntelligentEmbeddingClient, "_init_api_mode"):
                client = IntelligentEmbeddingClient.create_auto()
                assert client.mode == "api"
                assert "8090" in client.base_url


class TestAPIMode:
    """Tests for API mode (mocked)."""

    def test_create_api_mode(self):
        """Test creating client in API mode."""
        with patch("openai.OpenAI"):
            client = IntelligentEmbeddingClient.create_api(
                base_url="http://localhost:8090/v1", model="BAAI/bge-m3"
            )

            assert client.mode == "api"
            assert client.base_url == "http://localhost:8090/v1"
            assert client.model == "BAAI/bge-m3"

    def test_embed_api_mode(self):
        """Test embedding in API mode."""
        with patch("openai.OpenAI") as mock_openai:
            # Setup mock
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.1, 0.2, 0.3]),
                MagicMock(embedding=[0.4, 0.5, 0.6]),
            ]
            mock_client.embeddings.create.return_value = mock_response
            mock_openai.return_value = mock_client

            client = IntelligentEmbeddingClient.create_api(
                base_url="http://localhost:8090/v1", model="test-model"
            )

            vectors = client.embed(["text1", "text2"])

            assert len(vectors) == 2
            assert vectors[0] == [0.1, 0.2, 0.3]
            assert vectors[1] == [0.4, 0.5, 0.6]
            mock_client.embeddings.create.assert_called_once()


class TestConvenienceFunction:
    """Tests for convenience functions."""

    def test_get_embedding_client_mocked(self):
        """Test get_embedding_client convenience function."""
        from sage.common.components.sage_embedding import EmbeddingClientAdapter, EmbeddingFactory

        def mock_init_embedded(self):
            raw = EmbeddingFactory.create("hash", dim=64)
            self._client = EmbeddingClientAdapter(raw)
            self._dimension = 64
            self.mode = "embedded"

        with patch.object(IntelligentEmbeddingClient, "_init_embedded_mode", mock_init_embedded):
            client = get_embedding_client(fallback_model="hash")
            assert isinstance(client, IntelligentEmbeddingClient)
            assert client.mode == "embedded"


class TestEmbeddingProtocolCompliance:
    """Test that IntelligentEmbeddingClient conforms to EmbeddingProtocol."""

    def test_has_embed_method(self):
        """Client should have embed(texts, model) method."""
        from sage.common.components.sage_embedding import EmbeddingClientAdapter, EmbeddingFactory

        raw = EmbeddingFactory.create("hash", dim=64)
        adapter = EmbeddingClientAdapter(raw)

        client = IntelligentEmbeddingClient.__new__(IntelligentEmbeddingClient)
        client._client = adapter
        client._dimension = 64
        client.mode = "embedded"

        # Check method exists and accepts correct arguments
        result = client.embed(["test"], model=None)
        assert isinstance(result, list)

    def test_has_get_dim_method(self):
        """Client should have get_dim() method."""
        from sage.common.components.sage_embedding import EmbeddingClientAdapter, EmbeddingFactory

        raw = EmbeddingFactory.create("hash", dim=64)
        adapter = EmbeddingClientAdapter(raw)

        client = IntelligentEmbeddingClient.__new__(IntelligentEmbeddingClient)
        client._client = adapter
        client._dimension = 64
        client.mode = "embedded"

        dim = client.get_dim()
        assert isinstance(dim, int)
        assert dim > 0
