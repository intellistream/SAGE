#!/usr/bin/env python3
"""
Standalone validation script for GraphMemoryCollection implementation.
This script tests the core functionality without requiring a full SAGE installation.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add the sage package to path
sage_path = Path(__file__).parent / "packages" / "sage-middleware" / "src"
sys.path.insert(0, str(sage_path))

# Add sage-common to path (for logger dependency)
common_path = Path(__file__).parent / "packages" / "sage-common" / "src"
sys.path.insert(0, str(common_path))

print(f"Testing from: {sage_path}")
print("=" * 70)

try:
    # Test 1: Import the modules
    print("\n✓ Test 1: Importing modules...")
    from sage.middleware.components.sage_mem.neuromem.memory_collection.graph_collection import (
        GraphMemoryCollection,
        SimpleGraphIndex,
    )
    print("  ✓ Successfully imported GraphMemoryCollection and SimpleGraphIndex")

    # Test 2: Create a SimpleGraphIndex
    print("\n✓ Test 2: Creating SimpleGraphIndex...")
    index = SimpleGraphIndex("test_index")
    
    index.add_node("n1", "Node 1 data")
    index.add_node("n2", "Node 2 data")
    index.add_node("n3", "Node 3 data")
    
    assert index.has_node("n1"), "Node n1 should exist"
    assert index.has_node("n2"), "Node n2 should exist"
    assert not index.has_node("n4"), "Node n4 should not exist"
    print("  ✓ Nodes added successfully")
    
    index.add_edge("n1", "n2", 1.0)
    index.add_edge("n1", "n3", 0.5)
    
    neighbors = index.get_neighbors("n1", k=10)
    assert len(neighbors) == 2, "Should have 2 neighbors"
    assert neighbors[0] == "n2", "First neighbor should be n2 (higher weight)"
    print("  ✓ Edges and neighbor retrieval working")
    
    # Test 3: Test persistence
    print("\n✓ Test 3: Testing SimpleGraphIndex persistence...")
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = os.path.join(tmpdir, "test_index")
        index.store(save_path)
        
        assert os.path.exists(os.path.join(save_path, "nodes.json")), "nodes.json should exist"
        assert os.path.exists(os.path.join(save_path, "edges.json")), "edges.json should exist"
        
        # Load it back
        loaded_index = SimpleGraphIndex.load("test_index", save_path)
        assert loaded_index.has_node("n1"), "Loaded index should have n1"
        assert loaded_index.has_node("n2"), "Loaded index should have n2"
        
        loaded_neighbors = loaded_index.get_neighbors("n1", k=10)
        assert len(loaded_neighbors) == 2, "Loaded index should have 2 neighbors"
        print("  ✓ Persistence working correctly")
    
    # Test 4: Test GraphMemoryCollection (basic)
    print("\n✓ Test 4: Testing GraphMemoryCollection basics...")
    collection = GraphMemoryCollection("test_collection")
    
    result = collection.create_index({"name": "default"})
    assert result is True, "Index creation should succeed"
    assert "default" in collection.indexes, "Index should be in collection"
    print("  ✓ GraphMemoryCollection created and index added")
    
    # Test 5: Test node operations
    print("\n✓ Test 5: Testing node and edge operations...")
    node_id = collection.add_node("concept1", "Artificial Intelligence")
    assert node_id == "concept1", "Node ID should match"
    
    collection.add_node("concept2", "Machine Learning")
    collection.add_node("concept3", "Deep Learning")
    
    collection.add_edge("concept1", "concept2", weight=1.0)
    collection.add_edge("concept2", "concept3", weight=0.9)
    
    neighbors = collection.get_neighbors("concept1", k=10)
    assert len(neighbors) > 0, "Should have neighbors"
    assert neighbors[0]["node_id"] == "concept2", "First neighbor should be concept2"
    print("  ✓ Node and edge operations working")
    
    # Test 6: Test graph traversal
    print("\n✓ Test 6: Testing graph traversal...")
    traversal = collection.retrieve_by_graph("concept1", max_depth=2, max_nodes=10)
    assert len(traversal) > 0, "Traversal should return results"
    node_ids = [item["node_id"] for item in traversal]
    assert "concept1" in node_ids, "Start node should be in results"
    print("  ✓ Graph traversal working")
    
    # Test 7: Test persistence
    print("\n✓ Test 7: Testing GraphMemoryCollection persistence...")
    with tempfile.TemporaryDirectory() as tmpdir:
        result = collection.store(tmpdir)
        assert "collection_path" in result, "Store should return path"
        
        collection_path = result["collection_path"]
        assert os.path.exists(collection_path), "Collection path should exist"
        assert os.path.exists(os.path.join(collection_path, "config.json")), "config.json should exist"
        
        # Load it back
        loaded = GraphMemoryCollection.load("test_collection", collection_path)
        assert loaded.name == "test_collection", "Loaded collection should have correct name"
        assert "default" in loaded.indexes, "Loaded collection should have index"
        
        # Verify data is intact
        loaded_neighbors = loaded.get_neighbors("concept1", k=10)
        assert len(loaded_neighbors) > 0, "Loaded collection should have neighbors"
        print("  ✓ GraphMemoryCollection persistence working")
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
