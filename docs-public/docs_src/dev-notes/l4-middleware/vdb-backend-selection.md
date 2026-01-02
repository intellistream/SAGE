# VDB Backend Selection Guide

## Overview

SAGE's NeuroMem VDB system supports two backends:

- **FAISS** (Python): Facebook AI Similarity Search (third-party library)
- **SageDB** (C++): **Self-developed** high-performance vector database

## Key Differences

### SageDB (Self-Developed C++)

- ✅ **Fully custom implementation** - NOT based on FAISS
- ✅ C++20 codebase with pybind11 Python bindings
- ✅ Optimized for write-heavy workloads
- ✅ 10x faster single insert, 1.14x faster batch insert
- ✅ Custom metadata system and indexing
- 🔄 **Future**: ANNS algorithms will migrate to sage-libs for modularity

### FAISS (Third-Party Python)

- ✅ Mature library from Facebook AI Research
- ✅ Optimized for read-heavy workloads
- ✅ 2.8-3x faster similarity search
- ✅ Rich ecosystem and extensive documentation

## Performance Comparison

Based on benchmarks with 5000 vectors (dimension=128):

| Operation                   | FAISS     | SageDB    | Winner                       |
| --------------------------- | --------- | --------- | ---------------------------- |
| Single Insert (100 vectors) | 5.67 ms   | 0.57 ms   | 🚀 **SageDB (10x faster)**   |
| Batch Insert (5000 vectors) | 26.78 ms  | 23.50 ms  | 🚀 **SageDB (1.14x faster)** |
| Search (k=1)                | 26.98 ms  | 78.36 ms  | ⚡ **FAISS (2.9x faster)**   |
| Search (k=5)                | 28.92 ms  | 79.97 ms  | ⚡ **FAISS (2.8x faster)**   |
| Search (k=10)               | 28.16 ms  | 86.20 ms  | ⚡ **FAISS (3.1x faster)**   |
| Search (k=50)               | 31.87 ms  | 91.87 ms  | ⚡ **FAISS (2.9x faster)**   |
| Memory Usage                | 944.46 MB | 944.73 MB | ➡️ **Same**                  |

## Decision Matrix

### Use SageDB for:

**Write-Heavy Workloads**:

- Chat applications with frequent message insertions
- Session storage systems
- Real-time data ingestion pipelines
- Systems where insert latency is critical

**Characteristics**:

- 10x faster single insert
- 1.14x faster batch insert
- Self-developed C++ core (independent of FAISS)
- Custom write path optimizations
- Zero memory overhead vs FAISS
- Full control over implementation

**Example Use Cases**:

```python
# Gateway session storage (config.yaml)
gateway:
  memory:
    backend: short_term
    vdb:
      backend_type: SageDB  # 🚀 Fast session message insertion
      dimension: 1024
      retrieval_limit: 50
```

### Use FAISS for:

**Read-Heavy Workloads**:

- RAG retrieval systems
- Semantic search engines
- Large-scale similarity search
- Systems where search latency is critical

**Characteristics**:

- 2.8-3x faster similarity search
- Mature Python ecosystem
- Excellent for high QPS scenarios
- Same memory footprint as SageDB

**Example Use Cases**:

```python
# Production RAG system
collection.create_index({
    "name": "knowledge_base",
    "dim": 1024,
    "backend_type": "FAISS",  # ⚡ Fast retrieval
    "description": "Production knowledge base"
})
```

## Hybrid Strategy

For systems with both write and read requirements:

```python
# Session storage: SageDB (write-heavy)
session_config = {
    "backend_type": "SageDB",
    "dim": 768,
}

# Knowledge base: FAISS (read-heavy)
kb_config = {
    "backend_type": "FAISS",
    "dim": 1024,
}
```

## Configuration

### Gateway (config/config.yaml)

```yaml
gateway:
  memory:
    backend: short_term
    vdb:
      backend_type: SageDB  # or "FAISS"
      dimension: 1024
      retrieval_limit: 50
```

### Python API

```python
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

manager = MemoryManager()
collection = manager.create_collection({"name": "my_collection"})

# SageDB backend
collection.create_index({
    "name": "write_heavy_index",
    "dim": 1024,
    "backend_type": "SageDB",  # 🚀 Fast writes
})

# FAISS backend
collection.create_index({
    "name": "read_heavy_index",
    "dim": 1024,
    "backend_type": "FAISS",  # ⚡ Fast reads
})
```

## Benchmark Reproduction

Run the benchmark yourself:

```bash
cd /home/shuhao/SAGE
python benchmark_vdb_backends.py
```

The script tests:

- Single insert performance (100 vectors)
- Batch insert performance (5000 vectors)
- Search performance (k=1, 5, 10, 50)
- Memory usage

## Technical Notes

### Why is SageDB insert faster?

- Self-developed C++ implementation optimized for writes
- Direct memory management without FAISS overhead
- Custom indexing structure for fast insertions
- Minimal Python/C++ boundary crossing
- Efficient metadata handling

### Why is FAISS search faster?

- Mature implementation with decades of optimization
- Heavily optimized for batch search operations
- Benefits from extensive performance tuning
- Direct SIMD optimizations
- **Note**: SageDB search performance will improve with ANNS algorithm migration

### Memory Usage

Both backends maintain similar memory footprints (~945 MB for 5000 vectors @ dim=128) as they use
efficient C++ data structures.

## Summary

- **SageDB**: Self-developed C++ vector database (NOT FAISS-based)
- **Default recommendation**: Use **SageDB** for Gateway session storage (write-heavy)
- **Default recommendation**: Use **FAISS** for RAG knowledge bases (read-heavy)
- **Performance**: Choose based on read/write ratio
- **Memory**: No significant difference between backends
- **Configuration**: Easily switchable via `config.yaml` or Python API
- **Future**: ANNS algorithms will migrate to sage-libs for better modularity

______________________________________________________________________

**Last Updated**: 2025-12-28\
**Benchmark Environment**: 5000 vectors, dim=128, single-threaded\
**Tested Versions**: SAGE v0.2.0\
**Important Note**: SageDB is a self-developed C++ implementation, independent of FAISS
