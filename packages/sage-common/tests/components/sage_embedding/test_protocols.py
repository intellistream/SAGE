"""Tests for EmbeddingProtocol and adapters.

This module tests the unified embedding interface protocols used by
selectors and other components that require text embeddings.
"""

import pytest

from sage.common.components.sage_embedding.protocols import (
    EmbeddingClientAdapter,
    EmbeddingProtocol,
    adapt_embedding_client,
)


class TestEmbeddingProtocol:
    """Tests for EmbeddingProtocol interface compliance."""

    def test_protocol_is_runtime_checkable(self):
        """EmbeddingProtocol should be runtime checkable."""

        # A class implementing the protocol
        class ValidEmbedder:
            def embed(self, texts: list[str], model=None) -> list[list[float]]:
                return [[0.1, 0.2] for _ in texts]

            def get_dim(self) -> int:
                return 2

        embedder = ValidEmbedder()
        assert isinstance(embedder, EmbeddingProtocol)

    def test_protocol_rejects_incomplete_implementation(self):
        """Classes missing required methods should not match protocol."""

        class MissingEmbed:
            def get_dim(self) -> int:
                return 2

        class MissingGetDim:
            def embed(self, texts: list[str], model=None) -> list[list[float]]:
                return [[0.1] for _ in texts]

        assert not isinstance(MissingEmbed(), EmbeddingProtocol)
        assert not isinstance(MissingGetDim(), EmbeddingProtocol)


class TestEmbeddingClientAdapter:
    """Tests for EmbeddingClientAdapter."""

    def test_adapter_wraps_single_text_interface(self):
        """Adapter should convert single-text embed to batch embed."""

        class SingleTextEmbedder:
            def embed(self, text: str) -> list[float]:
                return [len(text) * 0.1, len(text) * 0.2]

            def embed_batch(self, texts: list[str]) -> list[list[float]]:
                return [self.embed(t) for t in texts]

            def get_dim(self) -> int:
                return 2

        raw = SingleTextEmbedder()
        adapter = EmbeddingClientAdapter(raw)

        # Test batch embedding
        result = adapter.embed(["hello", "world", "test"])
        assert len(result) == 3
        assert all(len(vec) == 2 for vec in result)

    def test_adapter_uses_embed_batch_when_available(self):
        """Adapter should prefer embed_batch for efficiency."""
        batch_called = []

        class EmbedderWithBatch:
            def embed(self, text: str) -> list[float]:
                return [0.1]

            def embed_batch(self, texts: list[str]) -> list[list[float]]:
                batch_called.append(len(texts))
                return [[0.1] for _ in texts]

            def get_dim(self) -> int:
                return 1

        adapter = EmbeddingClientAdapter(EmbedderWithBatch())
        adapter.embed(["a", "b", "c"])

        assert batch_called == [3], "Should call embed_batch once with all texts"

    def test_adapter_fallback_to_single_embed(self):
        """Adapter should fallback to single embed if batch unavailable."""
        single_calls = []

        class EmbedderWithoutBatch:
            def embed(self, text: str) -> list[float]:
                single_calls.append(text)
                return [0.1]

            def get_dim(self) -> int:
                return 1

        adapter = EmbeddingClientAdapter(EmbedderWithoutBatch())
        result = adapter.embed(["x", "y"])

        assert len(result) == 2
        assert single_calls == ["x", "y"]

    def test_adapter_get_dim(self):
        """Adapter should delegate get_dim to wrapped embedder."""

        class Embedder384:
            def embed(self, text: str) -> list[float]:
                return [0.0] * 384

            def get_dim(self) -> int:
                return 384

        adapter = EmbeddingClientAdapter(Embedder384())
        assert adapter.get_dim() == 384

    def test_adapter_ignores_model_parameter(self):
        """Adapter should accept but ignore model parameter."""

        class SimpleEmbedder:
            def embed(self, text: str) -> list[float]:
                return [1.0]

            def embed_batch(self, texts: list[str]) -> list[list[float]]:
                return [[1.0] for _ in texts]

            def get_dim(self) -> int:
                return 1

        adapter = EmbeddingClientAdapter(SimpleEmbedder())
        # Should work with any model parameter
        result = adapter.embed(["test"], model="any-model")
        assert result == [[1.0]]


class TestAdaptEmbeddingClient:
    """Tests for adapt_embedding_client function."""

    def test_adapt_passes_through_compliant_embedder(self):
        """Embedders with batch interface should not be wrapped."""

        class BatchEmbedder:
            def embed(self, texts: list[str], model=None) -> list[list[float]]:
                return [[0.1] for _ in texts]

            def get_dim(self) -> int:
                return 1

        original = BatchEmbedder()
        adapted = adapt_embedding_client(original)

        # Should return the same instance
        assert adapted is original

    def test_adapt_wraps_single_text_embedder(self):
        """Single-text embedders should be wrapped with adapter."""

        class SingleTextEmbedder:
            def embed(self, text: str) -> list[float]:
                return [0.1]

            def embed_batch(self, texts: list[str]) -> list[list[float]]:
                return [[0.1] for _ in texts]

            def get_dim(self) -> int:
                return 1

        original = SingleTextEmbedder()
        adapted = adapt_embedding_client(original)

        assert isinstance(adapted, EmbeddingClientAdapter)
        assert adapted is not original

    def test_adapt_raises_for_invalid_embedder(self):
        """Should raise TypeError for objects without embed/get_dim."""

        class NotAnEmbedder:
            pass

        with pytest.raises(TypeError, match="Missing 'embed' or 'get_dim' method"):
            adapt_embedding_client(NotAnEmbedder())

    def test_adapt_handles_embedder_with_text_param(self):
        """Embedders with 'text' parameter should be wrapped."""

        class TextParamEmbedder:
            def embed(self, text: str) -> list[float]:
                return [0.5]

            def get_dim(self) -> int:
                return 1

        adapted = adapt_embedding_client(TextParamEmbedder())
        assert isinstance(adapted, EmbeddingClientAdapter)


class TestIntegrationWithRealEmbedders:
    """Integration tests with actual embedding implementations."""

    def test_adapt_hash_embedding(self):
        """Test adapting HashEmbedding from factory."""
        from sage.common.components.sage_embedding.factory import EmbeddingFactory

        # Create hash embedder (lightweight, no model download)
        raw = EmbeddingFactory.create("hash", dim=64)
        adapted = adapt_embedding_client(raw)

        # Should be wrapped
        assert isinstance(adapted, EmbeddingClientAdapter)

        # Should work with batch interface
        vectors = adapted.embed(["hello", "world"])
        assert len(vectors) == 2
        assert all(len(v) == 64 for v in vectors)

        # Dimension should match
        assert adapted.get_dim() == 64

    def test_adapt_mock_embedding(self):
        """Test adapting MockEmbedding."""
        from sage.common.components.sage_embedding.factory import EmbeddingFactory

        raw = EmbeddingFactory.create("mockembedder", fixed_dim=128)
        adapted = adapt_embedding_client(raw)

        vectors = adapted.embed(["test1", "test2", "test3"])
        assert len(vectors) == 3
        assert all(len(v) == 128 for v in vectors)

    def test_gorilla_selector_interface_compatibility(self):
        """Test that adapted embedder works with Gorilla's expected interface."""
        from sage.common.components.sage_embedding.factory import EmbeddingFactory

        # This is what Gorilla selector expects
        raw = EmbeddingFactory.create("hash", dim=64)
        embedding_client = EmbeddingClientAdapter(raw)

        # Gorilla calls: embed(texts=[...], model=...)
        result = embedding_client.embed(
            texts=["search query", "tool description"],
            model="default",  # Gorilla passes model parameter
        )

        assert len(result) == 2
        assert all(isinstance(v, list) for v in result)
        assert all(isinstance(x, float) for v in result for x in v)
