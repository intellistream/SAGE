"""Focused tests for the MockEmbedding wrapper."""

import pytest

from sage.common.components.sage_embedding.wrappers.mock_wrapper import MockEmbedding


@pytest.mark.unit
class TestMockEmbedding:
    """Validate deterministic behavior and metadata."""

    def test_embed_returns_expected_dimension(self):
        emb = MockEmbedding(fixed_dim=96)

        vector = emb.embed("hello world")

        assert isinstance(vector, list)
        assert len(vector) == 96
        assert all(0 <= value <= 1 for value in vector)

    def test_embed_is_deterministic_with_seed(self):
        emb1 = MockEmbedding(fixed_dim=32, seed=42)
        emb2 = MockEmbedding(fixed_dim=32, seed=42)

        vec1 = emb1.embed("repeatable text")
        vec2 = emb2.embed("repeatable text")

        assert vec1 == vec2

    def test_embed_varies_without_seed(self):
        emb1 = MockEmbedding(fixed_dim=32)
        emb2 = MockEmbedding(fixed_dim=32)

        vec1 = emb1.embed("random text")
        vec2 = emb2.embed("random text")

        # Very small chance of equality, acceptable for unit test coverage purposes
        assert vec1 != vec2

    def test_get_model_info_and_properties(self):
        emb = MockEmbedding(fixed_dim=80)

        info = emb.get_model_info()

        assert info["method"] == "mockembedder"
        assert info["default_dimension"] == 128
        assert emb.method_name == "mockembedder"
        assert emb.get_dim() == 80
