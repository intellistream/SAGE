"""
Test suite for VDBMemoryCollection statistics functionality.

This module tests the memory statistics and audit capabilities added to VDBMemoryCollection,
including:
- Memory usage tracking
- Retrieval performance monitoring
- Index rebuild frequency tracking
"""

import json
import os
import shutil
import tempfile
import time

import numpy as np

try:
    import pytest

    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False

from sage.common.components.sage_embedding.embedding_api import apply_embedding_model
from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import (
    VDBMemoryCollection,
)

if PYTEST_AVAILABLE:

    @pytest.fixture
    def test_dir():
        """Create a temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup after test
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

    @pytest.fixture
    def embedding_model():
        """Create embedding model for generating vectors."""
        return apply_embedding_model("mockembedder")

    def normalize_vector(vector):
        """Normalize a vector using L2 normalization."""
        if hasattr(vector, "detach") and hasattr(vector, "cpu"):
            vector = vector.detach().cpu().numpy()
        if isinstance(vector, list):
            vector = np.array(vector)
        if not isinstance(vector, np.ndarray):
            vector = np.array(vector)
        vector = vector.astype(np.float32)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    @pytest.fixture
    def collection():
        """Create a test collection."""
        config = {"name": "test_stats_collection"}
        return VDBMemoryCollection(config=config)

    @pytest.fixture
    def collection_with_index(collection):
        """Create a collection with an index."""
        index_config = {
            "name": "test_index",
            "embedding_model": "mockembedder",
            "dim": 128,
            "backend_type": "FAISS",
            "description": "Test index for statistics",
            "index_parameter": {},
        }
        collection.create_index(config=index_config)
        return collection

    def test_initial_statistics(collection):
        """Test that statistics are initialized correctly."""
        stats = collection.get_statistics()

        assert stats["insert_count"] == 0
        assert stats["retrieve_count"] == 0
        assert stats["index_create_count"] == 0
        assert stats["index_rebuild_count"] == 0
        assert stats["total_vectors_stored"] == 0
        assert len(stats["retrieve_stats"]) == 0
        assert len(stats["index_stats"]) == 0

    def test_index_creation_statistics(collection_with_index):
        """Test statistics tracking for index creation."""
        stats = collection_with_index.get_statistics()

        assert stats["index_create_count"] == 1
        assert "test_index" in stats["index_stats"]
        assert stats["index_stats"]["test_index"]["vector_count"] == 0
        assert stats["index_stats"]["test_index"]["created_time"] is not None

    def test_insert_statistics(collection_with_index, embedding_model):
        """Test statistics tracking for data insertion."""
        # Insert data
        text1 = "Test document 1"
        text2 = "Test document 2"
        vec1 = normalize_vector(embedding_model.encode(text1))
        vec2 = normalize_vector(embedding_model.encode(text2))
        collection_with_index.insert(
            content=text1, index_names="test_index", vector=vec1, metadata={"type": "test"}
        )
        collection_with_index.insert(
            content=text2, index_names="test_index", vector=vec2, metadata={"type": "test"}
        )

        stats = collection_with_index.get_statistics()

        assert stats["insert_count"] == 2
        assert stats["index_stats"]["test_index"]["vector_count"] == 2
        assert stats["total_vectors_stored"] == 2

    def test_batch_insert_statistics(collection_with_index, embedding_model):
        """Test statistics tracking for batch insertion."""
        # Batch insert data
        texts = ["Document 1", "Document 2", "Document 3"]
        metadatas = [{"id": i} for i in range(len(texts))]
        collection_with_index.batch_insert_data(texts, metadatas)

        # Initialize the index to add vectors
        vectors = [normalize_vector(embedding_model.encode(text)) for text in texts]
        item_ids = collection_with_index.get_all_ids()
        collection_with_index.init_index("test_index", vectors, item_ids)

        stats = collection_with_index.get_statistics()

        # Check that vectors were added to the index
        assert stats["index_stats"]["test_index"]["vector_count"] == 3
        assert stats["total_vectors_stored"] == 3

    def test_retrieve_statistics(collection_with_index, embedding_model):
        """Test statistics tracking for retrieval operations."""
        # Insert and initialize data
        texts = ["Python programming", "Machine learning", "Data science"]
        collection_with_index.batch_insert_data(texts, None)
        vectors = [normalize_vector(embedding_model.encode(text)) for text in texts]
        item_ids = collection_with_index.get_all_ids()
        collection_with_index.init_index("test_index", vectors, item_ids)

        # Perform retrieval
        query_vec = normalize_vector(embedding_model.encode("programming"))
        collection_with_index.retrieve(query=query_vec, index_name="test_index", top_k=2)

        stats = collection_with_index.get_statistics()

        assert stats["retrieve_count"] == 1
        assert len(stats["retrieve_stats"]) == 1

        retrieve_stat = stats["retrieve_stats"][0]
        assert "timestamp" in retrieve_stat
        assert "duration" in retrieve_stat
        assert retrieve_stat["duration"] >= 0
        assert retrieve_stat["result_count"] >= 0
        assert retrieve_stat["index_name"] == "test_index"
        assert retrieve_stat["requested_topk"] == 2

    def test_multiple_retrievals_statistics(collection_with_index, embedding_model):
        """Test statistics for multiple retrieval operations."""
        # Insert and initialize data
        texts = ["AI research", "Neural networks", "Deep learning"]
        collection_with_index.batch_insert_data(texts, None)
        vectors = [normalize_vector(embedding_model.encode(text)) for text in texts]
        item_ids = collection_with_index.get_all_ids()
        collection_with_index.init_index("test_index", vectors, item_ids)

        # Perform multiple retrievals
        query_vec = normalize_vector(embedding_model.encode("AI"))
        for _ in range(5):
            collection_with_index.retrieve(query=query_vec, index_name="test_index", top_k=1)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        stats = collection_with_index.get_statistics()

        assert stats["retrieve_count"] == 5
        assert len(stats["retrieve_stats"]) == 5

    def test_index_rebuild_statistics(collection_with_index, embedding_model):
        """Test statistics tracking for index rebuild operations."""
        # Insert initial data
        texts = ["Initial data"]
        collection_with_index.batch_insert_data(texts, None)
        vectors = [normalize_vector(embedding_model.encode(text)) for text in texts]
        item_ids = collection_with_index.get_all_ids()
        collection_with_index.init_index("test_index", vectors, item_ids)

        # Rebuild the index
        collection_with_index.update_index("test_index", vectors, item_ids)

        stats = collection_with_index.get_statistics()

        assert stats["index_rebuild_count"] == 1
        assert stats["index_stats"]["test_index"]["last_rebuild_time"] is not None

    def test_memory_stats(collection_with_index, embedding_model):
        """Test memory statistics calculation."""
        # Insert data
        texts = [f"Document {i}" for i in range(10)]
        collection_with_index.batch_insert_data(texts, None)
        vectors = [normalize_vector(embedding_model.encode(text)) for text in texts]
        item_ids = collection_with_index.get_all_ids()
        collection_with_index.init_index("test_index", vectors, item_ids)

        memory_stats = collection_with_index.get_memory_stats()

        assert memory_stats["total_vectors"] == 10
        assert memory_stats["estimated_memory_mb"] > 0
        assert "test_index" in memory_stats["index_stats"]
        assert memory_stats["index_stats"]["test_index"]["vector_count"] == 10

    def test_retrieve_stats_method(collection_with_index, embedding_model):
        """Test the get_retrieve_stats method."""
        # Insert and initialize data
        texts = ["Test data"]
        collection_with_index.batch_insert_data(texts, None)
        vectors = [normalize_vector(embedding_model.encode(text)) for text in texts]
        item_ids = collection_with_index.get_all_ids()
        collection_with_index.init_index("test_index", vectors, item_ids)

        # Perform retrievals
        query_vec = normalize_vector(embedding_model.encode("test"))
        for _ in range(3):
            collection_with_index.retrieve(query=query_vec, index_name="test_index")

        retrieve_stats = collection_with_index.get_retrieve_stats()

        assert retrieve_stats["total_retrieve_count"] == 3
        assert retrieve_stats["avg_duration"] >= 0
        assert len(retrieve_stats["recent_stats"]) == 3

        # Test with last_n parameter
        retrieve_stats_last_2 = collection_with_index.get_retrieve_stats(last_n=2)
        assert len(retrieve_stats_last_2["recent_stats"]) == 2

    def test_index_rebuild_stats_method(collection_with_index, embedding_model):
        """Test the get_index_rebuild_stats method."""
        rebuild_stats = collection_with_index.get_index_rebuild_stats()

        assert rebuild_stats["total_rebuild_count"] == 0
        assert "test_index" in rebuild_stats["index_details"]
        assert rebuild_stats["index_details"]["test_index"]["vector_count"] == 0

        # Rebuild index
        texts = ["Data"]
        collection_with_index.batch_insert_data(texts, None)
        vectors = [normalize_vector(embedding_model.encode(text)) for text in texts]
        item_ids = collection_with_index.get_all_ids()
        collection_with_index.init_index("test_index", vectors, item_ids)
        collection_with_index.update_index("test_index", vectors, item_ids)

        rebuild_stats = collection_with_index.get_index_rebuild_stats()
        assert rebuild_stats["total_rebuild_count"] == 1


def test_reset_statistics(collection_with_index, embedding_model):
    """Test resetting statistics."""
    # Insert data and perform operations - insert adds to index directly
    text1 = "Test"
    vec1 = normalize_vector(embedding_model.encode(text1))
    collection_with_index.insert(
        content=text1, index_names="test_index", vector=vec1, metadata={"key": "value"}
    )

    # Batch insert more data - only stores, doesn't add to index yet
    texts = ["Data1", "Data2"]
    collection_with_index.batch_insert_data(texts, None)

    # Init index with all stored data (this will include the first insert too)
    all_ids = collection_with_index.get_all_ids()
    all_texts = [collection_with_index.text_storage.get(item_id) for item_id in all_ids]
    vectors = [normalize_vector(embedding_model.encode(text)) for text in all_texts]
    collection_with_index.init_index("test_index", vectors, all_ids)

    query_vec = normalize_vector(embedding_model.encode("test"))
    collection_with_index.retrieve(query=query_vec, index_name="test_index")

    # Reset statistics
    collection_with_index.reset_statistics()

    stats = collection_with_index.get_statistics()

    assert stats["insert_count"] == 0
    assert stats["retrieve_count"] == 0
    assert stats["index_create_count"] == 0
    assert stats["index_rebuild_count"] == 0
    # total_vectors_stored reflects actual state, not a counter that can be reset
    # 1 from insert + 3 from init_index (which re-adds everything) = 4 total
    assert stats["total_vectors_stored"] == 4
    assert len(stats["retrieve_stats"]) == 0


def test_statistics_persistence(collection_with_index, test_dir, embedding_model):
    """Test that statistics are persisted and restored correctly."""
    # Perform operations
    text1 = "Test document"
    vec1 = normalize_vector(embedding_model.encode(text1))
    collection_with_index.insert(content=text1, index_names="test_index", vector=vec1)

    texts = ["Doc1", "Doc2"]
    collection_with_index.batch_insert_data(texts, None)
    vectors = [normalize_vector(embedding_model.encode(text)) for text in texts]
    item_ids = collection_with_index.get_all_ids()
    collection_with_index.init_index("test_index", vectors, item_ids)

    query_vec = normalize_vector(embedding_model.encode("test"))
    collection_with_index.retrieve(query=query_vec, index_name="test_index")

    # Get statistics before saving
    stats_before = collection_with_index.get_statistics()

    # Save collection
    save_path = os.path.join(test_dir, "stats_test")
    collection_with_index.store(save_path)

    # Load collection
    collection_dir = os.path.join(save_path, "vdb_collection", "test_stats_collection")
    loaded_collection = VDBMemoryCollection.load("test_stats_collection", collection_dir)

    # Get statistics after loading
    stats_after = loaded_collection.get_statistics()

    # Compare key statistics
    assert stats_after["insert_count"] == stats_before["insert_count"]
    assert stats_after["retrieve_count"] == stats_before["retrieve_count"]
    assert stats_after["index_create_count"] == stats_before["index_create_count"]
    assert stats_after["total_vectors_stored"] == stats_before["total_vectors_stored"]


def test_statistics_with_multiple_indexes(collection, embedding_model):
    """Test statistics tracking with multiple indexes."""
    # Create two indexes
    for i in range(2):
        index_config = {
            "name": f"index_{i}",
            "embedding_model": "mockembedder",
            "dim": 128,
            "backend_type": "FAISS",
            "description": f"Test index {i}",
            "index_parameter": {},
        }
        collection.create_index(config=index_config)

    # Insert data to different indexes
    text0 = "Document for index 0"
    text1 = "Document for index 1"
    vec0 = normalize_vector(embedding_model.encode(text0))
    vec1 = normalize_vector(embedding_model.encode(text1))
    collection.insert(content=text0, index_names="index_0", vector=vec0)
    collection.insert(content=text1, index_names="index_1", vector=vec1)

    stats = collection.get_statistics()

    assert stats["index_create_count"] == 2
    assert len(stats["index_stats"]) == 2
    assert stats["insert_count"] == 2
    assert stats["total_vectors_stored"] == 2


def test_statistics_accuracy_after_operations(collection_with_index, embedding_model):
    """Test that statistics remain accurate after multiple operations."""
    # Perform a series of operations
    texts = ["Doc1", "Doc2", "Doc3"]
    collection_with_index.batch_insert_data(texts, None)
    vectors = [normalize_vector(embedding_model.encode(text)) for text in texts]
    item_ids = collection_with_index.get_all_ids()
    collection_with_index.init_index("test_index", vectors, item_ids)

    # Insert additional items
    text4 = "Doc4"
    text5 = "Doc5"
    vec4 = normalize_vector(embedding_model.encode(text4))
    vec5 = normalize_vector(embedding_model.encode(text5))
    collection_with_index.insert(content=text4, index_names="test_index", vector=vec4)
    collection_with_index.insert(content=text5, index_names="test_index", vector=vec5)

    # Perform retrievals
    query_vec1 = normalize_vector(embedding_model.encode("test"))
    query_vec2 = normalize_vector(embedding_model.encode("doc"))
    collection_with_index.retrieve(query=query_vec1, index_name="test_index", top_k=3)
    collection_with_index.retrieve(query=query_vec2, index_name="test_index", top_k=2)

    stats = collection_with_index.get_statistics()

    assert stats["insert_count"] == 2  # Only single inserts counted
    assert stats["retrieve_count"] == 2
    assert stats["total_vectors_stored"] == 5  # 3 from batch + 2 from insert
    assert stats["index_stats"]["test_index"]["vector_count"] == 5


if __name__ == "__main__":
    # Run a simple test to verify the module works
    from sage.common.components.sage_embedding.embedding_api import apply_embedding_model

    def normalize_vector_main(vector):
        """Normalize a vector using L2 normalization."""
        if hasattr(vector, "detach") and hasattr(vector, "cpu"):
            vector = vector.detach().cpu().numpy()
        if isinstance(vector, list):
            vector = np.array(vector)
        if not isinstance(vector, np.ndarray):
            vector = np.array(vector)
        vector = vector.astype(np.float32)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    # Create embedding model
    embedding_model = apply_embedding_model("mockembedder")

    config = {"name": "manual_test"}
    collection = VDBMemoryCollection(config=config)

    index_config = {
        "name": "test_index",
        "embedding_model": "mockembedder",
        "dim": 128,
        "backend_type": "FAISS",
        "description": "Manual test index",
        "index_parameter": {},
    }
    collection.create_index(config=index_config)

    # Test insert
    text1 = "Test document 1"
    vec1 = normalize_vector_main(embedding_model.encode(text1))
    collection.insert(
        content=text1, index_names="test_index", vector=vec1, metadata={"type": "test"}
    )

    # Test batch insert
    texts = ["Doc A", "Doc B", "Doc C"]
    collection.batch_insert_data(texts, None)
    vectors = [normalize_vector_main(embedding_model.encode(text)) for text in texts]
    item_ids = collection.get_all_ids()
    collection.init_index("test_index", vectors, item_ids)

    # Test retrieve
    query_vec = normalize_vector_main(embedding_model.encode("test"))
    collection.retrieve(query=query_vec, index_name="test_index", top_k=2)

    # Print statistics
    print("\n=== Statistics ===")
    print(json.dumps(collection.get_statistics(), indent=2, default=str))

    print("\n=== Memory Stats ===")
    print(json.dumps(collection.get_memory_stats(), indent=2))

    print("\n=== Retrieve Stats ===")
    print(json.dumps(collection.get_retrieve_stats(), indent=2, default=str))

    print("\n=== Index Rebuild Stats ===")
    print(json.dumps(collection.get_index_rebuild_stats(), indent=2, default=str))

    print("\n✅ Manual test completed successfully!")
