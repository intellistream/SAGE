"""
Tests for parallel VDB insertion.

This test suite validates:
1. ParallelVDBService - High-performance parallel batch insertion
2. EmbeddingService batch processing (foundation for parallel insertion)

Architecture:
    ParallelVDBService (SAGE middleware layer)
        ↓
    ThreadPoolExecutor (parallel batches)
        ↓
    EmbeddingService.embed() + VDBCollection.insert() (per batch)

Note: neuromem remains single-threaded; parallelization is at SAGE level.
"""

import pytest


class TestParallelVDBService:
    """Unit tests for ParallelVDBService."""

    def test_parallel_insert_result_dataclass(self):
        """Test ParallelInsertResult dataclass."""
        from sage.middleware.components.sage_mem.services import ParallelInsertResult

        result = ParallelInsertResult(
            total_texts=1000,
            total_inserted=995,
            total_failed=5,
            elapsed_seconds=10.5,
            throughput_per_second=95.2,
            batch_results=[{"batch_idx": 0, "inserted": 100}],
        )

        assert result.total_texts == 1000
        assert result.total_inserted == 995
        assert result.total_failed == 5

        # Test to_dict
        d = result.to_dict()
        assert d["total_texts"] == 1000
        assert d["throughput_per_second"] == 95.2

    def test_parallel_vdb_service_init(self):
        """Test ParallelVDBService initialization."""
        from unittest.mock import MagicMock

        from sage.middleware.components.sage_mem.services import ParallelVDBService

        mock_collection = MagicMock()
        embedding_config = {
            "method": "mockembedder",
            "batch_size": 32,
        }

        service = ParallelVDBService(
            collection=mock_collection,
            embedding_config=embedding_config,
            max_workers=4,
            default_batch_size=500,
        )

        assert service._max_workers == 4
        assert service._default_batch_size == 500
        assert service._embedding_config == embedding_config

    def test_parallel_vdb_service_not_setup_error(self):
        """Test error when calling methods before setup."""
        from unittest.mock import MagicMock

        from sage.middleware.components.sage_mem.services import ParallelVDBService

        mock_collection = MagicMock()
        service = ParallelVDBService(
            collection=mock_collection,
            embedding_config={"method": "mockembedder"},
        )

        with pytest.raises(RuntimeError, match="not setup"):
            service.parallel_batch_insert(["test"], index_name="idx")

    def test_parallel_vdb_service_metadata_length_mismatch(self):
        """Test error when metadata length doesn't match texts."""
        from unittest.mock import MagicMock

        from sage.middleware.components.sage_mem.services import ParallelVDBService

        mock_collection = MagicMock()
        service = ParallelVDBService(
            collection=mock_collection,
            embedding_config={"method": "mockembedder"},
        )
        # Manually set to avoid setup
        service._embedding_service = MagicMock()
        service._executor = MagicMock()

        with pytest.raises(ValueError, match="metadatas length"):
            service.parallel_batch_insert(
                texts=["a", "b", "c"],
                index_name="idx",
                metadatas=[{"x": 1}],  # Wrong length
            )


class TestEmbeddingServiceBatch:
    """Tests for EmbeddingService batch processing (foundation for parallel insert)."""

    def test_embedding_service_batch_processing(self):
        """Test EmbeddingService batch embedding capability."""
        pytest.skip(
            "Test requires SAGE installation with embedding models. "
            "Run with: pytest -v --runintegration"
        )

    def test_embedding_service_caching(self):
        """Test EmbeddingService LRU caching."""
        pytest.skip(
            "Test requires SAGE installation with embedding models. "
            "Run with: pytest -v --runintegration"
        )


# Integration tests (require full SAGE installation)
class TestParallelVDBServiceIntegration:
    """Integration tests for ParallelVDBService.

    These tests require a full SAGE installation with embedding models.
    Run with: pytest -v --runintegration
    """

    @pytest.mark.integration
    def test_parallel_insert_with_mock_embedder(self):
        """Test parallel insertion with mock embedder."""
        from sage.middleware.components.sage_mem.neuromem.memory_collection import (
            VDBMemoryCollection,
        )
        from sage.middleware.components.sage_mem.services import ParallelVDBService

        # Create collection
        collection = VDBMemoryCollection(config={"name": "test_parallel_insert"})
        collection.create_index(
            config={
                "name": "test_index",
                "dim": 128,
                "backend_type": "FAISS",
                "description": "Test index",
            }
        )

        # Create parallel service with mock embedder
        service = ParallelVDBService(
            collection=collection,
            embedding_config={
                "method": "mockembedder",
                "batch_size": 16,
                "normalize": True,
            },
            max_workers=2,
            default_batch_size=20,
        )
        service.setup()

        try:
            # Generate test data
            num_items = 50
            texts = [f"Test document {i} with some content" for i in range(num_items)]

            # Parallel insert
            result = service.parallel_batch_insert(
                texts=texts,
                index_name="test_index",
                batch_size=20,
                show_progress=False,
            )

            # Verify results
            assert result.total_texts == num_items
            assert result.total_inserted > 0
            assert result.elapsed_seconds > 0
            assert result.throughput_per_second > 0

        finally:
            service.cleanup()

    @pytest.mark.integration
    def test_parallel_insert_with_metadata(self):
        """Test parallel insertion with metadata."""
        from sage.middleware.components.sage_mem.neuromem.memory_collection import (
            VDBMemoryCollection,
        )
        from sage.middleware.components.sage_mem.services import ParallelVDBService

        collection = VDBMemoryCollection(config={"name": "test_parallel_metadata"})
        collection.create_index(
            config={
                "name": "test_index",
                "dim": 128,
                "backend_type": "FAISS",
            }
        )

        service = ParallelVDBService(
            collection=collection,
            embedding_config={"method": "mockembedder"},
            max_workers=2,
        )
        service.setup()

        try:
            texts = ["doc1", "doc2", "doc3"]
            metadatas = [
                {"category": "A"},
                {"category": "B"},
                {"category": "C"},
            ]

            result = service.parallel_batch_insert(
                texts=texts,
                index_name="test_index",
                metadatas=metadatas,
                show_progress=False,
            )

            assert result.total_texts == 3
            assert result.total_inserted > 0

        finally:
            service.cleanup()

    @pytest.mark.integration
    def test_convenience_function(self):
        """Test parallel_insert_to_vdb convenience function."""
        from sage.middleware.components.sage_mem.neuromem.memory_collection import (
            VDBMemoryCollection,
        )
        from sage.middleware.components.sage_mem.services import parallel_insert_to_vdb

        collection = VDBMemoryCollection(config={"name": "test_convenience"})
        collection.create_index(
            config={
                "name": "main_index",
                "dim": 128,
                "backend_type": "FAISS",
            }
        )

        texts = [f"Document {i}" for i in range(30)]

        result = parallel_insert_to_vdb(
            texts=texts,
            collection=collection,
            index_name="main_index",
            embedding_config={"method": "mockembedder"},
            max_workers=2,
            batch_size=10,
        )

        assert result.total_texts == 30
        assert result.total_inserted > 0


class TestEmbeddingServiceIntegration:
    """Integration tests for EmbeddingService (original tests)."""

    @pytest.mark.integration
    def test_batch_embed_large_dataset(self):
        """Test batch embedding with a large dataset."""
        from sage.common.components.sage_embedding import EmbeddingService

        config = {
            "method": "mockembedder",
            "batch_size": 32,
            "normalize": True,
            "cache_enabled": True,
            "cache_size": 1000,
        }

        service = EmbeddingService(config)
        service.setup()

        try:
            num_items = 100
            texts = [f"Test text {i}" for i in range(num_items)]

            result = service.embed(texts, return_stats=True)

            assert result["count"] == num_items
            assert len(result["vectors"]) == num_items
            assert "stats" in result

        finally:
            service.cleanup()

    @pytest.mark.integration
    def test_cache_hit_rate(self):
        """Test that caching improves performance for repeated texts."""
        from sage.common.components.sage_embedding import EmbeddingService

        config = {
            "method": "mockembedder",
            "batch_size": 16,
            "cache_enabled": True,
            "cache_size": 100,
        }

        service = EmbeddingService(config)
        service.setup()

        try:
            texts = ["repeated text"] * 50

            # First call - all cache misses
            service.embed(texts, return_stats=True)

            # Second call - should have cache hits
            result2 = service.embed(texts, return_stats=True)

            assert result2["stats"]["cache_hit_rate"] > 0

        finally:
            service.cleanup()


if __name__ == "__main__":
    print("=" * 70)
    print("Parallel VDB Insertion Tests")
    print("=" * 70)
    print("\nRun unit tests: pytest -v test_parallel_insert.py")
    print("Run integration tests: pytest -v --runintegration test_parallel_insert.py")
    print("\nUsage example:")
    print("""
from sage.middleware.components.sage_mem.services import ParallelVDBService
from sage.middleware.components.sage_mem.neuromem.memory_collection import VDBMemoryCollection

# Create collection
collection = VDBMemoryCollection(config={"name": "my_collection"})
collection.create_index(config={"name": "main", "dim": 384, "backend_type": "FAISS"})

# Create parallel service
service = ParallelVDBService(
    collection=collection,
    embedding_config={"method": "hf", "model": "BAAI/bge-small-zh-v1.5"},
    max_workers=4,
)
service.setup()

# Insert 100K documents in parallel
texts = [f"Document {i}" for i in range(100000)]
result = service.parallel_batch_insert(texts, index_name="main", batch_size=1000)
print(f"Throughput: {result.throughput_per_second:.0f} docs/sec")

service.cleanup()
""")
