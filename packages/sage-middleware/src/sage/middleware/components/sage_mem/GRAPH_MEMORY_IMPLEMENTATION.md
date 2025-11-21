# Graph Memory Collection Implementation

This directory contains the implementation for issue #648: Graph-based memory collection for neuromem.

## Overview

The GraphMemoryCollection provides graph-based memory management for RAG applications, allowing users to:
- Store information as nodes in a graph
- Define relationships (edges) between memory items
- Retrieve information through graph traversal
- Persist and load graph structures

## Implementation

### Core Components

1. **SimpleGraphIndex** (`memory_collection/graph_collection.py`)
   - In-memory graph implementation using adjacency lists
   - Supports weighted directed edges
   - Provides efficient neighbor lookups
   - Includes persistence (JSON-based)

2. **GraphMemoryCollection** (`memory_collection/graph_collection.py`)
   - Extends BaseMemoryCollection
   - Manages multiple graph indexes
   - Provides high-level graph operations
   - Integrates with MemoryManager

### Key Features

- **Node Management**: Add, remove, and query nodes with associated data
- **Edge Management**: Create weighted directed edges between nodes
- **Graph Traversal**: BFS-based traversal with depth and node limits
- **Neighbor Retrieval**: Get neighbors sorted by edge weight
- **Persistence**: Store and load graph structures to/from disk
- **Metadata Support**: Store and filter by metadata (inherited from BaseMemoryCollection)

### Usage Example

```python
from sage.middleware.components.sage_mem import GraphMemoryCollection, MemoryManager

# Create a graph collection
collection = GraphMemoryCollection("knowledge_graph")
collection.create_index({"name": "concepts"})

# Add nodes
collection.add_node("ai", "Artificial Intelligence", metadata={"field": "cs"})
collection.add_node("ml", "Machine Learning", metadata={"field": "cs"})

# Add edges
collection.add_edge("ai", "ml", weight=1.0)

# Retrieve neighbors
neighbors = collection.get_neighbors("ai", k=10)

# Graph traversal
results = collection.retrieve_by_graph("ai", max_depth=2, max_nodes=10)

# Persistence
collection.store()
loaded = GraphMemoryCollection.load("knowledge_graph")
```

## Files Modified

### In neuromem submodule:
- `memory_collection/graph_collection.py` - Main implementation
- `memory_collection/__init__.py` - Export SimpleGraphIndex
- `__init__.py` - Export GraphMemoryCollection and SimpleGraphIndex
- `memory_manager.py` - Updated TODO comment

### In main SAGE repository:
- `packages/sage-middleware/src/sage/middleware/components/sage_mem/__init__.py` - Export updates
- `packages/sage-middleware/tests/components/sage_mem/test_graph_collection.py` - Comprehensive tests
- `examples/tutorials/L4-middleware/memory_service/graph_memory_example.py` - Usage examples

## Testing

Run tests:
```bash
cd /home/runner/work/SAGE/SAGE
pytest packages/sage-middleware/tests/components/sage_mem/test_graph_collection.py -v
```

Or run the example:
```bash
python examples/tutorials/L4-middleware/memory_service/graph_memory_example.py
```

## Technical Details

### Graph Storage Structure

```
<data_dir>/graph_collection/<collection_name>/
├── config.json              # Collection configuration
├── text_storage.json        # Text content storage
├── metadata_storage.json    # Metadata storage
└── indexes/
    └── <index_name>/
        ├── nodes.json       # Node data
        └── edges.json       # Edge data
```

### Time Complexity

- Add node: O(1)
- Add edge: O(1)
- Remove node: O(E) where E is total edges
- Remove edge: O(E) where E is edges from node
- Get neighbors: O(N log N) where N is neighbor count
- Has node: O(1)
- BFS traversal: O(V + E) where V is nodes, E is edges

## Design Decisions

1. **No External Dependencies**: Implemented using Python built-ins to avoid adding NetworkX or similar graph libraries
2. **Adjacency List**: Chosen for efficient neighbor lookups, common in RAG scenarios
3. **Weighted Edges**: Allows representing relationship strength
4. **Directed Graphs**: Provides maximum flexibility; undirected can be simulated with bidirectional edges
5. **JSON Persistence**: Simple, human-readable format matching other neuromem components

## Future Enhancements

Possible future improvements:
- Graph algorithms (PageRank, centrality measures, shortest path)
- Graph database integration (Neo4j, ArangoDB)
- Undirected graph support
- Graph visualization utilities
- Optimization for very large graphs
- Streaming graph updates

## Related Issues

- #648: Graph Collection (original implementation issue)
- #609: Graph version memory (parent issue - deleted)

## Notes for neuromem Submodule

The changes to the neuromem submodule are currently uncommitted. When this submodule is next synced with its upstream repository (https://github.com/intellistream/neuromem), these changes should be committed there with an appropriate message.

The implementation is fully functional and tested, ready for production use within the SAGE framework.
