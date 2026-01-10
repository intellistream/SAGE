# ANN - Unified Approximate Nearest Neighbor (Externalized)

**Location**: `sage.libs.ann`\
**Layer**: L3 (Algorithm Library)\
**Status**: ✅ Implementations moved to external package `isage-anns`

## Overview

This module provides the unified interface and factory for ANN (Approximate Nearest Neighbor)
algorithms. Concrete implementations have been externalized to the independent package
[`isage-anns`](https://pypi.org/project/isage-anns/).

`sage-libs` now serves as the **interface/registry layer** only. Heavy implementations/C++ code live
in the external repository.

## Installation

Install via extras (recommended):

```bash
pip install -e packages/sage-libs[anns]
# Or directly
pip install isage-anns
```

If `isage-anns` is missing, attempts to create/use ANN implementations will **fail fast** with an
actionable error—no silent fallbacks.

## What Remains Here

- **Interface contracts**: `AnnIndex`, `AnnIndexMeta`
- **Factory functions**: `create`, `register`, `registered`, `as_mapping`
- **Registry**: Algorithm registration system
- **Backward-compat shims**: Until all imports point to external package

## Usage

```python
from sage.libs.ann import create

# Create ANN index (requires isage-anns package)
index = create("faiss_hnsw", dim=128, metric="l2")

# Add vectors
index.add(vectors)

# Search
results = index.search(query_vector, k=10)
```

## Supported Algorithms (in isage-anns)

- FAISS variants (HNSW, IVF, Flat)
- VSAG HNSW
- DiskANN
- Custom implementations (Candy, CUFE, GTI, PUCK, etc.)

See [isage-anns documentation](https://github.com/intellistream/sage-anns) for full list.

## Architecture

```
sage.libs.ann (L3)
  ├── interface/          # AnnIndex base class, registry
  └── [implementations in isage-anns package]

isage-anns (External PyPI Package)
  ├── faiss_hnsw          # FAISS HNSW implementation
  ├── vsag_hnsw           # VSAG HNSW implementation
  ├── diskann             # DiskANN implementation
  └── ...                 # Other implementations
```

## Used By

- `sage.middleware.components.sage_db` (SageVDB backend)
- `sage.benchmark.benchmark_anns` (L5 benchmarking)
- RAG pipelines requiring vector search

## Design Principles

1. **Registry Pattern**: Unified factory for all ANN algorithms
1. **Interface Stability**: Base classes remain in sage-libs
1. **Fail Fast**: No silent fallbacks on missing implementations
1. **External Implementations**: Heavy code in independent package
1. **Backward Compatibility**: Shims for existing imports

## Migration Notes

### From Old ANNS Module

```python
# Old (deprecated)
from sage.libs.ann import create

# New (current)
from sage.libs.ann import create
```

### External Package Structure

The external `isage-anns` package structure:

```
isage-anns/
  ├── src/isage_anns/
  │   ├── base.py           # Re-exports from sage.libs.ann
  │   ├── faiss_hnsw.py     # FAISS HNSW wrapper
  │   ├── vsag_hnsw.py      # VSAG HNSW wrapper
  │   └── ...
  └── pyproject.toml
```

## Troubleshooting

### Error: "ANN implementations have moved to external package"

**Solution**: Install the external package:

```bash
pip install isage-anns
```

### Error: "Algorithm 'xxx' not registered"

**Solution**: Ensure `isage-anns` is installed and the algorithm is available:

```python
from sage.libs.ann import registered
print(registered())  # List available algorithms
```

## References

- External repo: https://github.com/intellistream/sage-anns
- PyPI package: https://pypi.org/project/isage-anns/
- Migration docs: `packages/sage-libs/docs/anns/MIGRATION.md`
- Architecture: `docs-public/docs_src/dev-notes/package-architecture.md`
