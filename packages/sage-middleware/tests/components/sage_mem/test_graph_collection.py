"""
Tests for GraphMemoryCollection functionality.
"""

import os
import shutil

try:
    import pytest

    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

    # Create a dummy fixture decorator
    def pytest_fixture(func):
        return func

    class pytest:  # type: ignore[no-redef]
        fixture = staticmethod(pytest_fixture)


from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    GraphMemoryCollection,
)
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.middleware.components.sage_mem.neuromem.utils.path_utils import (
    get_default_data_dir,
)


@pytest.fixture
def cleanup_data():
    """Fixture to clean up test data after tests."""
    yield
    # Cleanup after test
    data_dir = get_default_data_dir()
    if os.path.exists(data_dir):
        shutil.rmtree(os.path.dirname(data_dir))


def test_graph_collection_basic(cleanup_data):
    """Test basic graph collection operations."""
    # Create a graph collection
    collection = GraphMemoryCollection({"name": "test_graph"})

    # Create an index
    assert collection.create_index({"name": "default"}) is True
    assert "default" in collection.indexes

    # Test duplicate index creation
    assert collection.create_index({"name": "default"}) is False

    # Add nodes
    node1_id = collection.add_node("node1", "First node content")
    node2_id = collection.add_node("node2", "Second node content")
    node3_id = collection.add_node("node3", "Third node content")

    assert node1_id == "node1"
    assert node2_id == "node2"
    assert node3_id == "node3"

    # Add edges
    collection.add_edge("node1", "node2", weight=1.0)
    collection.add_edge("node1", "node3", weight=0.5)
    collection.add_edge("node2", "node3", weight=0.8)

    # Get neighbors
    neighbors = collection.get_neighbors("node1", k=10)
    assert len(neighbors) == 2
    assert neighbors[0]["node_id"] == "node2"  # Higher weight comes first

    # Test graph traversal
    traversal_results = collection.retrieve_by_graph("node1", max_depth=2, max_nodes=10)
    assert len(traversal_results) > 0
    assert any(r["node_id"] == "node1" for r in traversal_results)

    print("✅ Test: Basic graph collection operations passed!")


def test_graph_collection_persistence(cleanup_data):
    """Test graph collection persistence (store and load)."""
    collection_name = "persist_test_graph"

    # Create and populate a graph collection
    collection = GraphMemoryCollection({"name": collection_name})
    collection.create_index({"name": "main_index"})

    # Add nodes with metadata
    collection.add_node("alice", "Alice is a researcher", metadata={"role": "researcher"})
    collection.add_node("bob", "Bob is a developer", metadata={"role": "developer"})
    collection.add_node("charlie", "Charlie is a manager", metadata={"role": "manager"})

    # Add relationships
    collection.add_edge("alice", "bob", weight=0.9)
    collection.add_edge("alice", "charlie", weight=0.7)
    collection.add_edge("bob", "charlie", weight=0.6)

    # Store to disk
    result = collection.store()
    assert "collection_path" in result

    # Create a new instance and load
    loaded_collection = GraphMemoryCollection.load(collection_name)

    # Verify loaded data
    assert loaded_collection.name == collection_name
    assert "main_index" in loaded_collection.indexes

    # Verify nodes and edges were loaded
    neighbors = loaded_collection.get_neighbors("alice", k=10)
    assert len(neighbors) == 2
    assert neighbors[0]["node_id"] == "bob"  # Higher weight

    # Verify text storage was loaded
    all_ids = loaded_collection.get_all_ids()
    assert len(all_ids) > 0

    print("✅ Test: Graph collection persistence passed!")


def test_graph_collection_with_manager(cleanup_data):
    """Test graph collection through MemoryManager."""
    manager = MemoryManager()

    # Create a graph collection via manager
    config = {
        "name": "manager_graph",
        "backend_type": "graph",
        "description": "Test graph collection",
    }

    collection = manager.create_collection(config)
    assert collection is not None
    assert isinstance(collection, GraphMemoryCollection)

    # Use the collection
    collection.create_index({"name": "knowledge_graph"})  # type: ignore[union-attr]
    collection.add_node("concept1", "Artificial Intelligence")  # type: ignore[union-attr]
    collection.add_node("concept2", "Machine Learning")  # type: ignore[union-attr]
    collection.add_node("concept3", "Deep Learning")  # type: ignore[union-attr]

    collection.add_edge("concept1", "concept2", weight=1.0)  # type: ignore[union-attr]
    collection.add_edge("concept2", "concept3", weight=0.9)  # type: ignore[union-attr]

    # Test manager operations
    assert manager.has_collection("manager_graph")

    # Store via manager
    manager.store_collection("manager_graph")

    # Delete and reload
    del manager
    manager = MemoryManager()

    # Get the collection from disk
    loaded_collection = manager.get_collection("manager_graph")
    assert loaded_collection is not None

    # Verify loaded data
    neighbors = loaded_collection.get_neighbors("concept1", k=10)  # type: ignore[union-attr]
    assert len(neighbors) > 0  # type: ignore[arg-type]

    # Cleanup
    manager.delete_collection("manager_graph")

    print("✅ Test: Graph collection with MemoryManager passed!")


def test_graph_index_operations(cleanup_data):
    """Test low-level graph index operations."""
    from sage.middleware.components.sage_mem.neuromem.memory_collection import (
        SimpleGraphIndex,
    )

    index = SimpleGraphIndex("test_index")

    # Add nodes
    index.add_node("n1", "Node 1 data")
    index.add_node("n2", "Node 2 data")
    index.add_node("n3", "Node 3 data")

    # Check node existence
    assert index.has_node("n1")
    assert index.has_node("n2")
    assert not index.has_node("n4")

    # Add edges
    index.add_edge("n1", "n2", 1.0)
    index.add_edge("n1", "n3", 0.5)
    index.add_edge("n2", "n3", 0.8)

    # Get neighbors (returns list of (node_id, weight) tuples)
    neighbors = index.get_neighbors("n1", k=10)
    assert len(neighbors) == 2
    assert neighbors[0][0] == "n2"  # Higher weight

    # NOTE: get_incoming_neighbors was removed from SimpleGraphIndex
    # Skip testing incoming neighbors

    # Get node data
    data = index.get_node_data("n1")
    assert data == "Node 1 data"

    # Remove edge
    index.remove_edge("n1", "n2")
    neighbors = index.get_neighbors("n1", k=10)
    assert len(neighbors) == 1
    assert neighbors[0][0] == "n3"

    # Remove node
    index.remove_node("n3")
    assert not index.has_node("n3")
    neighbors = index.get_neighbors("n1", k=10)
    assert len(neighbors) == 0

    print("✅ Test: Graph index operations passed!")


def test_graph_traversal(cleanup_data):
    """Test graph traversal with multiple depths."""
    collection = GraphMemoryCollection({"name": "traversal_test"})
    collection.create_index({"name": "default"})

    # Create a small graph structure
    # n1 -> n2 -> n4
    # n1 -> n3 -> n5
    collection.add_node("n1", "Root node")
    collection.add_node("n2", "Second level A")
    collection.add_node("n3", "Second level B")
    collection.add_node("n4", "Third level A")
    collection.add_node("n5", "Third level B")

    collection.add_edge("n1", "n2", 1.0)
    collection.add_edge("n1", "n3", 0.9)
    collection.add_edge("n2", "n4", 0.8)
    collection.add_edge("n3", "n5", 0.7)

    # Test depth 1 traversal
    results_depth1 = collection.retrieve_by_graph("n1", max_depth=1, max_nodes=10)
    node_ids = [r["node_id"] for r in results_depth1]
    assert "n1" in node_ids
    assert "n2" in node_ids or "n3" in node_ids

    # Test depth 2 traversal
    results_depth2 = collection.retrieve_by_graph("n1", max_depth=2, max_nodes=10)
    node_ids = [r["node_id"] for r in results_depth2]
    assert len(node_ids) >= 3  # At least n1 and some neighbors
    assert "n1" in node_ids

    # Test max_nodes limit
    results_limited = collection.retrieve_by_graph("n1", max_depth=2, max_nodes=3)
    assert len(results_limited) <= 3

    print("✅ Test: Graph traversal passed!")


def test_graph_metadata(cleanup_data):
    """Test graph collection with metadata."""
    collection = GraphMemoryCollection({"name": "metadata_test"})
    collection.create_index({"name": "default"})

    # Add nodes with metadata
    collection.add_node(
        "doc1", "Python programming guide", metadata={"language": "python", "type": "guide"}
    )
    collection.add_node(
        "doc2", "Python best practices", metadata={"language": "python", "type": "tips"}
    )
    collection.add_node("doc3", "Java tutorial", metadata={"language": "java", "type": "guide"})

    # Add edges to create graph structure for traversal
    collection.add_edge("doc1", "doc2", 0.9)
    collection.add_edge("doc1", "doc3", 0.5)

    # Retrieve via graph traversal starting from doc1
    results = collection.retrieve(start_node="doc1", with_metadata=True, max_depth=2)
    assert len(results) >= 1  # At least the start node should be returned
    # Check that results have metadata
    for r in results:
        if "metadata" in r:
            assert isinstance(r["metadata"], dict)

    print("✅ Test: Graph metadata operations passed!")


if __name__ == "__main__":
    # Run tests manually
    cleanup = type(
        "Cleanup", (), {"__enter__": lambda self: None, "__exit__": lambda *args: None}
    )()

    print("\n=== Running Graph Collection Tests ===\n")

    test_graph_collection_basic(cleanup)
    test_graph_collection_persistence(cleanup)
    test_graph_collection_with_manager(cleanup)
    test_graph_index_operations(cleanup)
    test_graph_traversal(cleanup)
    test_graph_metadata(cleanup)

    print("\n=== All Graph Collection Tests Passed! ===\n")

    # Final cleanup
    data_dir = get_default_data_dir()
    if os.path.exists(data_dir):
        shutil.rmtree(os.path.dirname(data_dir))
        print(f"✅ Cleaned up test data directory: {data_dir}")
