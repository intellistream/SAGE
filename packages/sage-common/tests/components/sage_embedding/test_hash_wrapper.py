"""
Comprehensive tests for HashEmbedding wrapper

Tests cover:
- Initialization and dimension handling
- Empty text embedding
- Text tokenization and embedding
- Edge cases (special characters, no tokens, short digest chunks)
- Batch embedding
- Model info and properties
"""

import pytest  # noqa: F401

from sage.common.components.sage_embedding.wrappers.hash_wrapper import HashEmbedding


class TestHashEmbeddingInitialization:
    """Test HashEmbedding initialization"""

    def test_default_initialization(self):
        """Test initialization with default dimension"""
        emb = HashEmbedding()
        assert emb.get_dim() == 384

    def test_custom_dimension(self):
        """Test initialization with custom dimension"""
        emb = HashEmbedding(dim=512)
        assert emb.get_dim() == 512

    def test_minimum_dimension_enforced(self):
        """Test minimum dimension of 64 is enforced"""
        emb = HashEmbedding(dim=32)
        assert emb.get_dim() == 64  # Should be clamped to 64

    def test_dimension_coercion_to_int(self):
        """Test dimension is coerced to int"""
        emb = HashEmbedding(dim=100.5)
        assert emb.get_dim() == 100
        assert isinstance(emb.get_dim(), int)


class TestHashEmbeddingEmbed:
    """Test embed method"""

    def test_embed_simple_text(self):
        """Test embedding simple text"""
        emb = HashEmbedding(dim=384)
        vec = emb.embed("hello world")

        assert len(vec) == 384
        assert all(isinstance(v, float) for v in vec)

    def test_embed_empty_string(self):
        """Test embedding empty string returns zero vector (line 74)"""
        emb = HashEmbedding(dim=384)
        vec = emb.embed("")

        assert len(vec) == 384
        assert all(v == 0.0 for v in vec)

    def test_embed_chinese_text(self):
        """Test embedding Chinese text"""
        emb = HashEmbedding(dim=256)
        vec = emb.embed("你好世界")

        assert len(vec) == 256
        assert sum(v * v for v in vec) > 0  # Non-zero vector

    def test_embed_special_characters_only(self):
        """Test text with only special characters (no alphanumeric/Chinese) (line 81)"""
        emb = HashEmbedding(dim=128)
        # Text with only special characters, no alphanumeric or Chinese
        vec = emb.embed("!@#$%^&*()")

        assert len(vec) == 128
        # Should use the original text as single token since no valid tokens found
        assert sum(v * v for v in vec) > 0  # Should still have some values

    def test_embed_mixed_alphanumeric(self):
        """Test embedding mixed alphanumeric text"""
        emb = HashEmbedding(dim=200)
        vec = emb.embed("test123abc456")

        assert len(vec) == 200
        assert sum(v * v for v in vec) > 0

    def test_embed_deterministic(self):
        """Test same text produces same embedding"""
        emb = HashEmbedding(dim=384)
        vec1 = emb.embed("test")
        vec2 = emb.embed("test")

        assert vec1 == vec2

    def test_embed_different_texts_different_vectors(self):
        """Test different texts produce different vectors"""
        emb = HashEmbedding(dim=384)
        vec1 = emb.embed("hello")
        vec2 = emb.embed("world")

        assert vec1 != vec2

    def test_embed_normalization(self):
        """Test output vectors are L2 normalized"""
        emb = HashEmbedding(dim=256)
        vec = emb.embed("normalize test")

        # L2 norm should be approximately 1.0
        norm = sum(v * v for v in vec) ** 0.5
        assert abs(norm - 1.0) < 1e-10

    def test_embed_with_small_dimension_for_chunk_edge_case(self):
        """Test with very small dimension to potentially trigger chunk padding (line 91)"""
        # Using a very small dimension increases chance of digest chunk being < 4 bytes
        emb = HashEmbedding(dim=64)
        vec = emb.embed("x")  # Single character

        assert len(vec) == 64
        assert sum(v * v for v in vec) > 0

    def test_embed_triggers_chunk_padding(self):
        """Test that ensures chunk padding is triggered (line 91)

        SHA256 produces 32-byte digest. When iterating with step=4,
        we get chunks at offsets: 0, 4, 8, 12, 16, 20, 24, 28, 32.
        At offset 32, digest[32:36] will be empty (len < 4).

        This test uses mocking to verify the padding logic is executed.
        """
        from unittest.mock import patch

        emb = HashEmbedding(dim=128)

        # Create a custom digest that will trigger the padding
        # We'll use a 31-byte digest so the last chunk is < 4 bytes
        def mock_sha256(_data):
            # Return an object with a digest() that gives 31 bytes
            class MockHash:
                def digest(self):
                    return b"x" * 31  # 31 bytes, so last chunk will be 3 bytes

            return MockHash()

        with patch("hashlib.sha256", side_effect=mock_sha256):
            vec = emb.embed("test")

        # Should still produce valid vector
        assert len(vec) == 128
        # The vector should have some non-zero values
        assert sum(v * v for v in vec) > 0


class TestHashEmbeddingBatch:
    """Test batch embedding"""

    def test_embed_batch_multiple_texts(self):
        """Test embedding multiple texts"""
        emb = HashEmbedding(dim=384)
        texts = ["hello", "world", "test"]
        vecs = emb.embed_batch(texts)

        assert len(vecs) == 3
        assert all(len(vec) == 384 for vec in vecs)

    def test_embed_batch_empty_list(self):
        """Test embedding empty list"""
        emb = HashEmbedding(dim=384)
        vecs = emb.embed_batch([])

        assert vecs == []

    def test_embed_batch_with_empty_strings(self):
        """Test batch with some empty strings"""
        emb = HashEmbedding(dim=256)
        texts = ["hello", "", "world"]
        vecs = emb.embed_batch(texts)

        assert len(vecs) == 3
        assert all(v == 0.0 for v in vecs[1])  # Middle one should be zero vector

    def test_embed_batch_consistency(self):
        """Test batch embedding is consistent with individual embedding"""
        emb = HashEmbedding(dim=384)
        text = "consistency test"

        vec_single = emb.embed(text)
        vec_batch = emb.embed_batch([text])[0]

        assert vec_single == vec_batch


class TestHashEmbeddingProperties:
    """Test properties and metadata"""

    def test_method_name_property(self):
        """Test method_name property returns 'hash' (line 114)"""
        emb = HashEmbedding()
        assert emb.method_name == "hash"

    def test_get_model_info(self):
        """Test get_model_info classmethod (lines 117-128)"""
        info = HashEmbedding.get_model_info()

        assert info["method"] == "hash"
        assert info["requires_api_key"] is False
        assert info["requires_model_download"] is False
        assert info["default_dimension"] == 384

    def test_get_dim_method(self):
        """Test get_dim method"""
        emb = HashEmbedding(dim=512)
        assert emb.get_dim() == 512


class TestHashEmbeddingEdgeCases:
    """Test edge cases and special scenarios"""

    def test_very_long_text(self):
        """Test embedding very long text"""
        emb = HashEmbedding(dim=384)
        long_text = " ".join(["word"] * 1000)
        vec = emb.embed(long_text)

        assert len(vec) == 384
        # Should still be normalized
        norm = sum(v * v for v in vec) ** 0.5
        assert abs(norm - 1.0) < 1e-10

    def test_whitespace_only(self):
        """Test text with only whitespace"""
        emb = HashEmbedding(dim=128)
        vec = emb.embed("   \t\n  ")

        assert len(vec) == 128
        # Should be treated as no valid tokens, use original text
        assert sum(v * v for v in vec) > 0

    def test_unicode_characters(self):
        """Test text with various Unicode characters"""
        emb = HashEmbedding(dim=256)
        vec = emb.embed("Hello 世界 🌍 مرحبا")

        assert len(vec) == 256
        assert sum(v * v for v in vec) > 0

    def test_case_insensitivity(self):
        """Test embedding is case insensitive"""
        emb = HashEmbedding(dim=384)
        vec1 = emb.embed("Hello World")
        vec2 = emb.embed("hello world")

        assert vec1 == vec2

    def test_with_kwargs_compatibility(self):
        """Test initialization with extra kwargs for compatibility"""
        emb = HashEmbedding(dim=256, extra_param="ignored", another="value")
        assert emb.get_dim() == 256

    def test_multiple_instances_independent(self):
        """Test multiple instances are independent"""
        emb1 = HashEmbedding(dim=256)
        emb2 = HashEmbedding(dim=512)

        assert emb1.get_dim() == 256
        assert emb2.get_dim() == 512

    def test_punctuation_handling(self):
        """Test text with various punctuation"""
        emb = HashEmbedding(dim=384)
        vec = emb.embed("Hello, world! How are you?")

        assert len(vec) == 384
        # Should extract "Hello", "world", "How", "are", "you"
        assert sum(v * v for v in vec) > 0
