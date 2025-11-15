"""
Tests for SAGE DB Service wrapper (sage_db_service.py).

This module tests the microservice-style wrapper for SAGE DB.
"""

import numpy as np
import pytest

# Try to import sage_db_service components
try:
    from sage.middleware.components.sage_db.python.micro_service.sage_db_service import (
        SageDBService,
        SageDBServiceConfig,
    )

    SAGE_DB_SERVICE_AVAILABLE = True
except ImportError:
    SAGE_DB_SERVICE_AVAILABLE = False


@pytest.mark.skipif(not SAGE_DB_SERVICE_AVAILABLE, reason="SAGE DB Service not available")
class TestSageDBServiceConfig:
    """Test SageDBServiceConfig dataclass."""

    def test_create_default_config(self):
        """Test creating default configuration."""
        config = SageDBServiceConfig()

        assert config.dimension == 4
        assert config.index_type == "AUTO"

    def test_create_custom_config(self):
        """Test creating custom configuration."""
        config = SageDBServiceConfig(dimension=128, index_type="FLAT")

        assert config.dimension == 128
        assert config.index_type == "FLAT"


@pytest.mark.skipif(not SAGE_DB_SERVICE_AVAILABLE, reason="SAGE DB Service not available")
class TestSageDBServiceBasic:
    """Basic tests for SageDBService."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        return SageDBService(dimension=64, index_type="FLAT")

    def test_create_service(self):
        """Test creating service instance."""
        service = SageDBService(dimension=128, index_type="FLAT")

        assert service is not None
        assert service._dim == 128

    def test_create_service_with_auto_index(self):
        """Test creating service with AUTO index type."""
        service = SageDBService(dimension=64, index_type="AUTO")

        assert service._dim == 64

    def test_create_service_default(self):
        """Test creating service with default parameters."""
        service = SageDBService()

        assert service._dim == 4

    def test_add_vector_numpy(self, service):
        """Test adding a single vector as numpy array."""
        vector = np.random.randn(64).astype(np.float32)
        metadata = {"key": "value", "id": "123"}

        vector_id = service.add(vector, metadata)

        assert isinstance(vector_id, int)
        assert vector_id >= 0

    def test_add_vector_list(self, service):
        """Test adding a single vector as list."""
        vector = [0.1] * 64
        metadata = {"type": "test"}

        vector_id = service.add(vector, metadata)

        assert isinstance(vector_id, int)

    def test_add_vector_without_metadata(self, service):
        """Test adding vector without metadata."""
        vector = np.random.randn(64).astype(np.float32)

        vector_id = service.add(vector)

        assert isinstance(vector_id, int)

    def test_add_batch_numpy(self, service):
        """Test adding batch of vectors as numpy array."""
        vectors = np.random.randn(10, 64).astype(np.float32)
        metadata_list = [{"id": str(i)} for i in range(10)]

        ids = service.add_batch(vectors, metadata_list)

        assert len(ids) == 10
        assert all(isinstance(vid, int) for vid in ids)

    def test_add_batch_list(self, service):
        """Test adding batch of vectors as list."""
        vectors = [[0.1] * 64 for _ in range(5)]
        metadata_list = [{"id": str(i)} for i in range(5)]

        ids = service.add_batch(vectors, metadata_list)

        assert len(ids) == 5

    def test_add_batch_without_metadata(self, service):
        """Test adding batch without metadata."""
        vectors = np.random.randn(5, 64).astype(np.float32)

        ids = service.add_batch(vectors)

        assert len(ids) == 5

    def test_search_numpy(self, service):
        """Test searching with numpy query."""
        # Add some vectors first
        vectors = np.random.randn(10, 64).astype(np.float32)
        service.add_batch(vectors)

        # Search
        query = np.random.randn(64).astype(np.float32)
        results = service.search(query, k=5)

        assert len(results) <= 5
        assert len(results) > 0

    def test_search_list(self, service):
        """Test searching with list query."""
        # Add some vectors
        vectors = np.random.randn(10, 64).astype(np.float32)
        service.add_batch(vectors)

        # Search with list
        query = [0.1] * 64
        results = service.search(query, k=3)

        assert len(results) <= 3

    def test_search_result_format(self, service):
        """Test that search results have correct format."""
        # Add vectors with metadata
        vectors = np.random.randn(5, 64).astype(np.float32)
        metadata_list = [{"category": f"cat_{i}"} for i in range(5)]
        service.add_batch(vectors, metadata_list)

        # Search
        query = np.random.randn(64).astype(np.float32)
        results = service.search(query, k=3, include_metadata=True)

        # Check format
        for result in results:
            assert "id" in result
            assert "score" in result
            assert "metadata" in result
            assert isinstance(result["id"], int)
            assert isinstance(result["score"], float)
            assert isinstance(result["metadata"], dict)

    def test_search_without_metadata(self, service):
        """Test search without including metadata."""
        # Add vectors
        vectors = np.random.randn(5, 64).astype(np.float32)
        service.add_batch(vectors)

        # Search without metadata
        query = np.random.randn(64).astype(np.float32)
        results = service.search(query, k=3, include_metadata=False)

        # Check that metadata is empty
        for result in results:
            assert result["metadata"] == {}

    def test_stats(self, service):
        """Test getting service statistics."""
        # Add some data
        vectors = np.random.randn(10, 64).astype(np.float32)
        service.add_batch(vectors)

        # Perform a search to generate stats
        query = np.random.randn(64).astype(np.float32)
        service.search(query, k=5)

        # Get stats
        stats = service.stats()

        assert isinstance(stats, dict)
        assert "size" in stats
        assert "dimension" in stats
        assert stats["size"] == 10
        assert stats["dimension"] == 64


@pytest.mark.skipif(not SAGE_DB_SERVICE_AVAILABLE, reason="SAGE DB Service not available")
class TestSageDBServiceValidation:
    """Test input validation for SageDBService."""

    def test_add_wrong_dimension(self):
        """Test that adding vector with wrong dimension raises error."""
        service = SageDBService(dimension=64)

        # Wrong dimension
        vector = np.random.randn(128).astype(np.float32)

        with pytest.raises(ValueError, match="vector shape must be"):
            service.add(vector)

    def test_add_wrong_shape(self):
        """Test that adding vector with wrong shape raises error."""
        service = SageDBService(dimension=64)

        # 2D instead of 1D
        vector = np.random.randn(1, 64).astype(np.float32)

        with pytest.raises(ValueError, match="vector shape must be"):
            service.add(vector)

    def test_add_batch_wrong_dimension(self):
        """Test that adding batch with wrong dimension raises error."""
        service = SageDBService(dimension=64)

        # Wrong second dimension
        vectors = np.random.randn(10, 128).astype(np.float32)

        with pytest.raises(ValueError, match="vectors shape must be"):
            service.add_batch(vectors)

    def test_add_batch_wrong_shape(self):
        """Test that adding batch with wrong shape raises error."""
        service = SageDBService(dimension=64)

        # 1D instead of 2D
        vectors = np.random.randn(64).astype(np.float32)

        with pytest.raises(ValueError, match="vectors shape must be"):
            service.add_batch(vectors)

    def test_add_batch_list_wrong_dimension(self):
        """Test that adding batch list with wrong dimension raises error."""
        service = SageDBService(dimension=64)

        # Wrong dimension
        vectors = [[0.1] * 128 for _ in range(5)]

        with pytest.raises(ValueError, match="vectors shape must be"):
            service.add_batch(vectors)


@pytest.mark.skipif(not SAGE_DB_SERVICE_AVAILABLE, reason="SAGE DB Service not available")
class TestSageDBServiceWorkflow:
    """Integration tests for complete workflows."""

    def test_end_to_end_workflow(self):
        """Test complete workflow from creation to search."""
        # 1. Create service
        service = SageDBService(dimension=128, index_type="FLAT")

        # 2. Add single vectors
        for i in range(5):
            vector = np.random.randn(128).astype(np.float32)
            metadata = {"id": str(i), "type": "single"}
            service.add(vector, metadata)

        # 3. Add batch
        batch_vectors = np.random.randn(10, 128).astype(np.float32)
        batch_metadata = [{"id": str(i + 5), "type": "batch"} for i in range(10)]
        service.add_batch(batch_vectors, batch_metadata)

        # 4. Search
        query = np.random.randn(128).astype(np.float32)
        results = service.search(query, k=5)

        assert len(results) == 5

        # 5. Check stats
        stats = service.stats()
        assert stats["size"] == 15

    def test_multiple_searches(self):
        """Test multiple consecutive searches."""
        service = SageDBService(dimension=64, index_type="FLAT")

        # Add data
        vectors = np.random.randn(20, 64).astype(np.float32)
        service.add_batch(vectors)

        # Perform multiple searches
        for _ in range(5):
            query = np.random.randn(64).astype(np.float32)
            results = service.search(query, k=3)
            assert len(results) <= 3

    def test_incremental_additions(self):
        """Test incremental addition of vectors."""
        service = SageDBService(dimension=64)

        # Add vectors incrementally
        for i in range(10):
            vector = np.random.randn(64).astype(np.float32)
            service.add(vector, {"step": str(i)})

        # Verify size
        stats = service.stats()
        assert stats["size"] == 10

    def test_different_k_values(self):
        """Test searching with different k values."""
        service = SageDBService(dimension=64)

        # Add data
        vectors = np.random.randn(20, 64).astype(np.float32)
        service.add_batch(vectors)

        query = np.random.randn(64).astype(np.float32)

        # Test different k values
        for k in [1, 5, 10, 15, 20, 25]:
            results = service.search(query, k=k)
            expected_results = min(k, 20)  # Can't return more than available
            assert len(results) == expected_results

    def test_empty_database_search(self):
        """Test searching in empty database."""
        service = SageDBService(dimension=64)

        query = np.random.randn(64).astype(np.float32)
        results = service.search(query, k=5)

        # Should return empty list
        assert len(results) == 0


@pytest.mark.skipif(not SAGE_DB_SERVICE_AVAILABLE, reason="SAGE DB Service not available")
class TestSageDBServiceEdgeCases:
    """Edge case tests for SageDBService."""

    def test_service_with_small_dimension(self):
        """Test service with very small dimension."""
        service = SageDBService(dimension=2)

        vector = np.array([0.1, 0.2], dtype=np.float32)
        vector_id = service.add(vector)

        assert isinstance(vector_id, int)

    def test_service_with_large_dimension(self):
        """Test service with large dimension."""
        service = SageDBService(dimension=2048)

        vector = np.random.randn(2048).astype(np.float32)
        vector_id = service.add(vector)

        assert isinstance(vector_id, int)

    def test_search_with_k_zero(self):
        """Test search with k=0."""
        service = SageDBService(dimension=64)

        vectors = np.random.randn(10, 64).astype(np.float32)
        service.add_batch(vectors)

        query = np.random.randn(64).astype(np.float32)
        results = service.search(query, k=0)

        # Should return empty results
        assert len(results) == 0

    def test_invalid_index_type(self):
        """Test that invalid index type falls back to AUTO."""
        service = SageDBService(dimension=64, index_type="INVALID_TYPE")

        # Should still work (fallback to AUTO)
        vector = np.random.randn(64).astype(np.float32)
        vector_id = service.add(vector)

        assert isinstance(vector_id, int)

    def test_metadata_with_special_characters(self):
        """Test metadata with special characters."""
        service = SageDBService(dimension=64)

        vector = np.random.randn(64).astype(np.float32)
        metadata = {
            "name": "Test Item",
            "description": "Item with special chars: !@#$%^&*()",
            "unicode": "测试中文",
        }

        vector_id = service.add(vector, metadata)
        assert isinstance(vector_id, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
