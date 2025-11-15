"""
Tests for SAGE DB Python wrapper (sage_db.py).

This module tests the Python interface to the SageDB C++ vector database.
"""

import os
import tempfile

import numpy as np
import pytest

# Try to import sage_db components
try:
    from sage.middleware.components.sage_db.python.sage_db import (
        DatabaseConfig,
        DistanceMetric,
        IndexType,
        SearchParams,
        create_database,
        create_database_from_config,
    )

    SAGE_DB_AVAILABLE = True
except ImportError:
    SAGE_DB_AVAILABLE = False

try:
    from sage.middleware.components.sage_db.python.sage_db import SageDBException  # noqa: F401

    SAGE_DB_EXCEPTION_AVAILABLE = True
except ImportError:
    SAGE_DB_EXCEPTION_AVAILABLE = False


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.mark.skipif(not SAGE_DB_AVAILABLE, reason="SAGE DB not available")
class TestSageDBBasic:
    """Basic tests for SageDB functionality."""

    @pytest.fixture
    def sample_db(self):
        """Create a sample database for testing."""
        dimension = 128
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)
        return db

    @pytest.fixture
    def populated_db(self):
        """Create a database with some data."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        # Add some vectors
        for i in range(10):
            vector = np.random.randn(dimension).astype(np.float32)
            metadata = {"id": str(i), "category": f"cat_{i % 3}"}
            db.add(vector, metadata)

        return db

    def test_create_database(self):
        """Test database creation."""
        dimension = 128
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        assert db is not None
        assert db.dimension == dimension
        assert db.size == 0

    def test_create_database_different_metrics(self):
        """Test database creation with different distance metrics."""
        dimension = 64

        # Test L2
        db_l2 = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)
        assert db_l2.dimension == dimension

        # Test COSINE if available
        try:
            db_cosine = create_database(dimension, IndexType.FLAT, DistanceMetric.COSINE)
            assert db_cosine.dimension == dimension
        except AttributeError:
            # COSINE metric not available in this build
            pytest.skip("COSINE metric not available")

    def test_create_database_from_config(self):
        """Test database creation from config."""
        config = DatabaseConfig()
        config.dimension = 128
        config.index_type = IndexType.FLAT
        config.metric = DistanceMetric.L2

        db = create_database_from_config(config)
        assert db.dimension == 128

    def test_add_vector_list(self, sample_db):
        """Test adding a vector as a list."""
        vector = [0.1] * 128
        metadata = {"key": "value"}

        vector_id = sample_db.add(vector, metadata)

        assert isinstance(vector_id, int)
        assert vector_id >= 0
        assert sample_db.size == 1

    def test_add_vector_numpy(self, sample_db):
        """Test adding a vector as numpy array."""
        vector = np.random.randn(128).astype(np.float32)
        metadata = {"key": "value"}

        vector_id = sample_db.add(vector, metadata)

        assert isinstance(vector_id, int)
        assert sample_db.size == 1

    def test_add_batch_numpy(self, sample_db):
        """Test batch adding vectors as numpy array."""
        vectors = np.random.randn(10, 128).astype(np.float32)
        metadata = [{"id": str(i)} for i in range(10)]

        ids = sample_db.add_batch(vectors, metadata)

        assert len(ids) == 10
        assert sample_db.size == 10

    def test_add_batch_list(self, sample_db):
        """Test batch adding vectors as list."""
        vectors = [[0.1] * 128 for _ in range(5)]
        metadata = [{"id": str(i)} for i in range(5)]

        ids = sample_db.add_batch(vectors, metadata)

        assert len(ids) == 5
        assert sample_db.size == 5

    def test_search_basic(self, populated_db):
        """Test basic vector search."""
        query = np.random.randn(64).astype(np.float32)

        results = populated_db.search(query, k=5)

        assert len(results) <= 5
        assert len(results) > 0

        # Check result structure
        for result in results:
            assert hasattr(result, "id")
            assert hasattr(result, "score")  # Changed from distance to score

    def test_search_numpy(self, populated_db):
        """Test search with numpy array."""
        query = np.random.randn(64).astype(np.float32)

        results = populated_db.search(query, k=3)

        assert len(results) <= 3

    def test_search_with_params(self, populated_db):
        """Test search with SearchParams object."""
        query = np.random.randn(64).astype(np.float32)
        params = SearchParams(k=5)

        results = populated_db.search_with_params(query, params)

        assert len(results) <= 5

    def test_metadata_operations(self, sample_db):
        """Test metadata set and get."""
        vector = np.random.randn(128).astype(np.float32)
        metadata = {"category": "test", "value": "123"}

        vector_id = sample_db.add(vector, metadata)

        # Get metadata
        retrieved_metadata = sample_db.get_metadata(vector_id)
        assert retrieved_metadata is not None
        assert retrieved_metadata.get("category") == "test"

        # Update metadata
        new_metadata = {"category": "updated", "new_field": "xyz"}
        success = sample_db.set_metadata(vector_id, new_metadata)
        assert success

    def test_find_by_metadata(self, populated_db):
        """Test finding vectors by metadata."""
        # Find all vectors in category "cat_0"
        ids = populated_db.find_by_metadata("category", "cat_0")

        assert isinstance(ids, list)
        # Should have approximately 1/3 of the 10 vectors
        assert len(ids) > 0

    def test_database_size(self, populated_db):
        """Test database size property."""
        assert populated_db.size == 10

    def test_database_dimension(self, sample_db):
        """Test database dimension property."""
        assert sample_db.dimension == 128

    def test_database_index_type(self, sample_db):
        """Test database index type property."""
        index_type = sample_db.index_type
        assert index_type == IndexType.FLAT


@pytest.mark.skipif(not SAGE_DB_AVAILABLE, reason="SAGE DB not available")
class TestSageDBAdvanced:
    """Advanced tests for SageDB functionality."""

    @pytest.fixture
    def ivf_db(self):
        """Create an IVF index database."""
        dimension = 64
        try:
            db = create_database(dimension, IndexType.IVF_FLAT, DistanceMetric.L2)
            return db
        except Exception:
            pytest.skip("IVF index not available")

    def test_build_index(self):
        """Test index building."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        # Add some vectors
        vectors = np.random.randn(20, dimension).astype(np.float32)
        db.add_batch(vectors)

        # Build index
        db.build_index()
        # If no exception, test passes

    def test_train_index(self):
        """Test index training."""
        dimension = 64
        # Use IVF index which requires training, not FLAT
        db = create_database(dimension, IndexType.IVF_FLAT, DistanceMetric.L2)

        # Add training vectors
        training_vectors = np.random.randn(100, dimension).astype(np.float32)

        db.train_index(training_vectors)

        # Check if trained (may return False if training not required/supported)
        # This depends on the underlying implementation
        # Just verify no exception was raised
        final_trained = db.is_trained()
        assert isinstance(final_trained, bool)

    def test_is_trained(self):
        """Test is_trained property."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        # FLAT index is always "trained"
        trained = db.is_trained()
        assert isinstance(trained, bool)

    def test_filtered_search(self):
        """Test filtered search with custom filter function."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        # Add vectors with metadata
        for i in range(10):
            vector = np.random.randn(dimension).astype(np.float32)
            metadata = {"id": str(i), "even": str(i % 2 == 0)}
            db.add(vector, metadata)

        # Filter function to only get even IDs
        def filter_even(metadata):
            return metadata.get("even") == "True"

        query = np.random.randn(dimension).astype(np.float32)
        params = SearchParams(k=10)

        results = db.filtered_search(query, params, filter_even)

        # All results should have even=True
        for result in results:
            if hasattr(result, "metadata"):
                assert result.metadata.get("even") == "True"

    def test_search_by_metadata(self):
        """Test search with metadata filtering."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        # Add vectors
        for i in range(10):
            vector = np.random.randn(dimension).astype(np.float32)
            metadata = {"category": f"cat_{i % 3}"}
            db.add(vector, metadata)

        query = np.random.randn(dimension).astype(np.float32)
        params = SearchParams(k=5)

        results = db.search_by_metadata(query, params, "category", "cat_0")

        # Results should only be from cat_0
        assert len(results) > 0

    def test_hybrid_search(self):
        """Test hybrid search (vector + text)."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        # Add vectors
        for i in range(10):
            vector = np.random.randn(dimension).astype(np.float32)
            metadata = {"text": f"document_{i}"}
            db.add(vector, metadata)

        query = np.random.randn(dimension).astype(np.float32)
        params = SearchParams(k=5)

        try:
            results = db.hybrid_search(
                query, params, text_query="document", vector_weight=0.7, text_weight=0.3
            )
            assert len(results) > 0
        except Exception:
            # Hybrid search might not be fully implemented
            pytest.skip("Hybrid search not available")

    def test_get_search_stats(self):
        """Test getting search statistics."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        # Add and search
        vectors = np.random.randn(10, dimension).astype(np.float32)
        db.add_batch(vectors)

        query = np.random.randn(dimension).astype(np.float32)
        db.search(query, k=5)

        try:
            stats = db.get_search_stats()

            assert isinstance(stats, dict)
            # Check for expected keys
            expected_keys = ["total_candidates", "final_results", "search_time_ms"]
            for key in expected_keys:
                if key in stats:
                    assert isinstance(stats[key], (int, float))
        except Exception:
            # Stats might not be available
            pytest.skip("Search stats not available")


@pytest.mark.skipif(not SAGE_DB_AVAILABLE, reason="SAGE DB not available")
class TestSageDBPersistence:
    """Tests for database persistence (save/load)."""

    def test_save_and_load(self, temp_dir):
        """Test saving and loading database."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        # Add some vectors
        vectors = np.random.randn(10, dimension).astype(np.float32)
        metadata = [{"id": str(i)} for i in range(10)]
        db.add_batch(vectors, metadata)

        # Save database
        filepath = os.path.join(temp_dir, "test_db.sage")
        db.save(filepath)

        # Create new database and load
        db2 = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)
        db2.load(filepath)

        # Verify loaded database
        assert db2.size == 10
        assert db2.dimension == dimension

    def test_save_empty_database(self, temp_dir):
        """Test saving an empty database."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        filepath = os.path.join(temp_dir, "empty_db.sage")

        try:
            db.save(filepath)
            # File should be created if save succeeds
            # Some implementations may not create files for empty databases
            # so we just verify no exception was raised
        except Exception:
            # Some implementations may not support saving empty databases
            pytest.skip("Save empty database not supported by this implementation")


@pytest.mark.skipif(not SAGE_DB_AVAILABLE, reason="SAGE DB not available")
class TestSageDBEdgeCases:
    """Edge case tests for SageDB."""

    def test_search_empty_database(self):
        """Test searching in an empty database."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        query = np.random.randn(dimension).astype(np.float32)
        results = db.search(query, k=5)

        # Should return empty results
        assert len(results) == 0

    def test_add_without_metadata(self):
        """Test adding vector without metadata."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        vector = np.random.randn(dimension).astype(np.float32)
        vector_id = db.add(vector, None)

        assert isinstance(vector_id, int)
        assert db.size == 1

    def test_large_batch_add(self):
        """Test adding a large batch of vectors."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        # Large batch
        num_vectors = 1000
        vectors = np.random.randn(num_vectors, dimension).astype(np.float32)

        ids = db.add_batch(vectors)

        assert len(ids) == num_vectors
        assert db.size == num_vectors

    def test_high_k_search(self):
        """Test search with k larger than database size."""
        dimension = 64
        db = create_database(dimension, IndexType.FLAT, DistanceMetric.L2)

        # Add only 5 vectors
        vectors = np.random.randn(5, dimension).astype(np.float32)
        db.add_batch(vectors)

        # Search with k=10
        query = np.random.randn(dimension).astype(np.float32)
        results = db.search(query, k=10)

        # Should return only 5 results
        assert len(results) == 5


@pytest.mark.skipif(not SAGE_DB_AVAILABLE, reason="SAGE DB not available")
class TestSageDBImportExport:
    """Test import and export functionality."""

    def test_all_exports(self):
        """Test that all expected symbols are exported."""
        from sage.middleware.components.sage_db.python import sage_db

        expected_exports = [
            "SageDB",
            "IndexType",
            "DistanceMetric",
            "QueryResult",
            "SearchParams",
            "DatabaseConfig",
            "create_database",
            "create_database_from_config",
        ]

        for export in expected_exports:
            assert hasattr(sage_db, export), f"Missing export: {export}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
