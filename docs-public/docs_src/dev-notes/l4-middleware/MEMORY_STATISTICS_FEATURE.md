# Memory Statistics Feature for VDBMemoryCollection

## Overview

This document describes the memory statistics and audit functionality added to `VDBMemoryCollection`
in the neuromem submodule.

## Issue Reference

- GitHub Issue: #610 (Parent issue)
- Related Enhancement: 内存统计审查功能 (Memory Statistics Audit Functionality)

## Motivation

The VDBMemoryCollection previously lacked observability features needed for production deployments
and debugging:

1. **No memory usage monitoring** - Unable to track total vectors stored or memory consumption
1. **No retrieval performance metrics** - No tracking of recall time or accuracy
1. **No index rebuild tracking** - Unknown frequency of index rebuilds

## Implementation

### Statistics Tracked

The implementation adds comprehensive statistics tracking without impacting existing functionality:

```python
statistics = {
    "insert_count": 0,              # Number of insert operations
    "retrieve_count": 0,             # Number of retrieve operations
    "index_create_count": 0,         # Number of indexes created
    "index_rebuild_count": 0,        # Number of index rebuilds
    "total_vectors_stored": 0,       # Total vectors across all indexes
    "retrieve_stats": [],            # List of retrieval operations with details
    "index_stats": {}                # Per-index statistics
}
```

### Modified Methods

#### 1. `__init__()`

- Initializes statistics structure

#### 2. `create_index()`

- Increments `index_create_count`
- Creates entry in `index_stats` with creation timestamp

#### 3. `init_index()`

- Updates vector count in index stats
- Recalculates `total_vectors_stored`

#### 4. `update_index()`

- Increments `index_rebuild_count`
- Records rebuild timestamp

#### 5. `insert()`

- Increments `insert_count`
- Updates vector count for the index
- Recalculates `total_vectors_stored`

#### 6. `retrieve()`

- Increments `retrieve_count`
- Records detailed statistics:
  - Timestamp
  - Duration (in seconds)
  - Result count
  - Index name
  - Requested topk

#### 7. `store()`

- Persists statistics to `config.json`

#### 8. `load()`

- Restores statistics from `config.json`
- Backwards compatible (works without statistics in old configs)

### New API Methods

#### `get_statistics()`

Returns all statistics as a dictionary.

```python
stats = collection.get_statistics()
# Returns complete statistics structure
```

#### `get_memory_stats()`

Returns memory usage information with estimated memory consumption.

```python
memory_stats = collection.get_memory_stats()
# Returns:
# {
#     "total_vectors": 1000,
#     "estimated_memory_mb": 0.49,
#     "index_stats": {
#         "index_name": {
#             "vector_count": 1000,
#             "created_time": 1700000000.0
#         }
#     }
# }
```

Memory estimation formula:

- Each vector: `dim × 4 bytes (float32) × 1.2 (20% metadata overhead)`
- Result in MB: `total_bytes / (1024 × 1024)`

#### `get_retrieve_stats(last_n=None)`

Returns retrieval performance statistics.

```python
retrieve_stats = collection.get_retrieve_stats(last_n=10)
# Returns:
# {
#     "total_retrieve_count": 50,
#     "avg_duration": 0.0023,  # seconds
#     "recent_stats": [
#         {
#             "timestamp": 1700000000.0,
#             "duration": 0.002,
#             "result_count": 5,
#             "index_name": "my_index",
#             "requested_topk": 5
#         },
#         ...
#     ]
# }
```

#### `get_index_rebuild_stats()`

Returns index rebuild frequency information.

```python
rebuild_stats = collection.get_index_rebuild_stats()
# Returns:
# {
#     "total_rebuild_count": 2,
#     "index_details": {
#         "index_name": {
#             "vector_count": 1000,
#             "last_rebuild_time": 1700000100.0,
#             "created_time": 1700000000.0
#         }
#     }
# }
```

#### `reset_statistics()`

Resets all counters while preserving index structure.

```python
collection.reset_statistics()
```

## Usage Examples

### Basic Usage

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import (
    VDBMemoryCollection,
)

# Create collection
config = {"name": "my_collection"}
collection = VDBMemoryCollection(config=config)

# Create index
index_config = {
    "name": "my_index",
    "embedding_model": "mockembedder",
    "dim": 128,
    "backend_type": "FAISS",
    "description": "My index",
    "index_parameter": {},
}
collection.create_index(config=index_config)

# Insert data
collection.insert("my_index", "Document 1", metadata={"id": 1})
collection.insert("my_index", "Document 2", metadata={"id": 2})

# Retrieve
results = collection.retrieve("Document", "my_index", topk=5)

# Check statistics
print("Memory usage:", collection.get_memory_stats())
print("Retrieval performance:", collection.get_retrieve_stats())
print("All statistics:", collection.get_statistics())
```

### Monitoring Production Deployment

```python
# Periodically check memory usage
memory_stats = collection.get_memory_stats()
if memory_stats["estimated_memory_mb"] > THRESHOLD:
    logger.warning(f"High memory usage: {memory_stats['estimated_memory_mb']} MB")

# Monitor retrieval performance
retrieve_stats = collection.get_retrieve_stats(last_n=100)
if retrieve_stats["avg_duration"] > 0.1:  # 100ms threshold
    logger.warning(f"Slow retrievals: {retrieve_stats['avg_duration']}s average")

# Check index rebuild frequency
rebuild_stats = collection.get_index_rebuild_stats()
if rebuild_stats["total_rebuild_count"] > 10:
    logger.info("Frequent rebuilds detected, consider optimization")
```

### Debugging Issues

```python
# Get detailed retrieval statistics
retrieve_stats = collection.get_retrieve_stats(last_n=10)
for stat in retrieve_stats["recent_stats"]:
    print(f"Query at {stat['timestamp']}: {stat['duration']}s, {stat['result_count']} results")

# Check per-index statistics
stats = collection.get_statistics()
for index_name, index_stat in stats["index_stats"].items():
    print(f"Index {index_name}: {index_stat['vector_count']} vectors")
```

## Testing

Comprehensive tests are provided in:

- `packages/sage-middleware/tests/components/sage_mem/test_vdb_statistics.py`

Tests cover:

- Initial statistics state
- Insert operation tracking
- Batch insert tracking
- Retrieve operation tracking
- Index creation tracking
- Index rebuild tracking
- Memory estimation
- Statistics persistence (save/load)
- Multiple index scenarios
- Statistics reset functionality

Run tests with:

```bash
pytest packages/sage-middleware/tests/components/sage_mem/test_vdb_statistics.py -v
```

Or run the manual test:

```bash
python packages/sage-middleware/tests/components/sage_mem/test_vdb_statistics.py
```

## Backwards Compatibility

The implementation is fully backwards compatible:

1. **Old collections without statistics**: Load correctly with default statistics
1. **Existing code**: Works without modification
1. **New methods**: Optional, existing code doesn't need them
1. **Persistence**: Old configs without statistics field are handled gracefully

## Performance Impact

The implementation has minimal performance impact:

1. **Insert operations**: ~5 integer increments per operation
1. **Retrieve operations**: ~1 timestamp, ~6 arithmetic operations
1. **Memory overhead**: ~few KB for statistics structure
1. **No impact on**: Core embedding, indexing, or search algorithms

## Implementation Notes

### Submodule Changes

The core implementation is in the neuromem submodule:

- Repository: `https://github.com/intellistream/neuromem.git`
- Branch: `feat/memory-statistics` (local)
- File: `memory_collection/vdb_collection.py`

### Test Location

Tests are in the main SAGE repository:

- File: `packages/sage-middleware/tests/components/sage_mem/test_vdb_statistics.py`

## Future Enhancements

Potential future improvements:

1. **Accuracy metrics**: Track recall@k, precision metrics
1. **Query latency percentiles**: P50, P95, P99
1. **Memory breakdown**: Per-component memory usage
1. **Export to monitoring systems**: Prometheus, Grafana integration
1. **Anomaly detection**: Automatic alerts for unusual patterns
1. **Index efficiency metrics**: Fill rate, fragmentation
1. **Historical trends**: Time-series statistics

## References

- Issue #610: 内存统计审查功能
- VDBMemoryCollection documentation
- neuromem repository: https://github.com/intellistream/neuromem
