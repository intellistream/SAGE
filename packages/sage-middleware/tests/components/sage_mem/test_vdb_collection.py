"""
Unit tests for VDBMemoryCollection.
Tests initialization and index creation validation.
"""

import pytest

try:
    from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import (
        VDBMemoryCollection,
    )

    VDB_AVAILABLE = True
except ImportError as e:
    VDB_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"VDBMemoryCollection not available: {e}")


@pytest.mark.unit
class TestVDBMemoryCollectionInit:
    """Test VDBMemoryCollection initialization."""

    def test_initialization(self):
        """Test basic initialization."""
        if not VDB_AVAILABLE:
            pytest.skip("VDBMemoryCollection not available")

        config = {"name": "test_vdb"}
        collection = VDBMemoryCollection(config)

        assert collection.name == "test_vdb"
        assert collection.index_info == {}
        assert collection.embedding_model_factory == {}

    def test_init_without_name_raises_error(self):
        """Test initialization without name raises KeyError."""
        if not VDB_AVAILABLE:
            pytest.skip("VDBMemoryCollection not available")

        with pytest.raises(KeyError):
            VDBMemoryCollection({})


@pytest.mark.unit
class TestVDBMemoryCollectionIndexValidation:
    """Test create_index validation logic."""

    def test_create_index_without_name(self):
        """Test create_index without name returns None."""
        if not VDB_AVAILABLE:
            pytest.skip("VDBMemoryCollection not available")

        collection = VDBMemoryCollection({"name": "test"})
        result = collection.create_index({"dim": 384, "embedding_model": "model"})
        assert result is None

    def test_create_index_without_embedding_model(self):
        """Test create_index without embedding_model returns None."""
        if not VDB_AVAILABLE:
            pytest.skip("VDBMemoryCollection not available")

        collection = VDBMemoryCollection({"name": "test"})
        result = collection.create_index({"name": "idx", "dim": 384})
        assert result is None

    def test_create_index_without_dim(self):
        """Test create_index without dim returns None."""
        if not VDB_AVAILABLE:
            pytest.skip("VDBMemoryCollection not available")

        collection = VDBMemoryCollection({"name": "test"})
        result = collection.create_index({"name": "idx", "embedding_model": "model"})
        assert result is None

    def test_create_index_with_invalid_dim_type(self):
        """Test create_index with non-int dim returns None."""
        if not VDB_AVAILABLE:
            pytest.skip("VDBMemoryCollection not available")

        collection = VDBMemoryCollection({"name": "test"})
        result = collection.create_index(
            {"name": "idx", "dim": "invalid", "embedding_model": "model"}
        )
        assert result is None

    def test_create_index_with_invalid_model_type(self):
        """Test create_index with non-string model returns None."""
        if not VDB_AVAILABLE:
            pytest.skip("VDBMemoryCollection not available")

        collection = VDBMemoryCollection({"name": "test"})
        result = collection.create_index({"name": "idx", "dim": 384, "embedding_model": 123})
        assert result is None

    def test_create_duplicate_index(self):
        """Test creating duplicate index returns None."""
        if not VDB_AVAILABLE:
            pytest.skip("VDBMemoryCollection not available")

        collection = VDBMemoryCollection({"name": "test"})
        collection.index_info["existing"] = {"dim": 384}
        result = collection.create_index(
            {"name": "existing", "dim": 384, "embedding_model": "model"}
        )
        assert result is None
