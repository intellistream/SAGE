# ANNS - Unified Approximate Nearest Neighbor Search

**Status**: 🚧 Under Construction (Migration from 3-layer structure)

This directory consolidates all ANNS-related code into a single unified location.

## Structure

```
anns_new/
├── interface/          # Abstract interfaces (formerly sage-libs/ann)
│   ├── base.py         # AnnIndex, AnnIndexMeta
│   ├── factory.py      # create(), register(), registered()
│   └── registry.py     # Algorithm registry
│
├── wrappers/           # Python wrappers (formerly sage-libs/anns/*)
│   ├── faiss/          # FAISS family (HNSW, IVFPQ, NSW, etc.)
│   ├── vsag/           # VSAG HNSW
│   ├── diskann/        # DiskANN, IPDiskANN
│   ├── candy/          # CANDY family (LSHAPG, MNRU, SPTAG)
│   ├── cufe/           # CUFE
│   ├── gti/            # GTI
│   ├── puck/           # PUCK
│   └── plsh/           # PLSH
│
├── implementations/    # C++ source code (formerly benchmark_anns/algorithms_impl)
│   ├── candy/          # CANDY C++ implementation
│   ├── diskann-ms/     # DiskANN submodule
│   ├── faiss/          # FAISS submodule
│   ├── vsag/           # VSAG submodule
│   ├── gti/            # GTI implementation
│   ├── puck/           # PUCK implementation
│   ├── SPTAG/          # SPTAG submodule
│   ├── include/        # Shared C++ headers
│   └── bindings/       # pybind11 bindings
│
└── benchmarks/         # Benchmark scripts (from benchmark_anns)
    ├── run_benchmark.py
    ├── prepare_dataset.py
    └── compute_gt.py
```

## Migration Status

- [x] Phase 1: Create new directory structure
- [x] Phase 2: Move interface layer (ann/ -> anns_new/interface/)
- [x] Phase 3: Reorganize wrappers (anns/\* -> anns_new/wrappers/<family>/)
- [x] Phase 4: Move C++ implementations (algorithms_impl/ -> anns_new/implementations/)
- [ ] Phase 5: Update all import paths (if any exist)
- [ ] Phase 6: Rename anns_new -> anns, remove old ann/ and anns/
- [ ] Phase 7: Testing and validation

## Usage (After Migration)

```python
# Factory pattern
from sage.libs.anns import create, register, registered

# Create an index
index = create("faiss_HNSW", dimension=128)

# Check available algorithms
algos = registered()

# Direct import (if needed)
from sage.libs.anns.wrappers.faiss import FaissHNSWIndex
```

## Design Principles

1. **Single source of truth**: All ANNS core code (interface, wrappers, C++ impl) in one place
1. **Clear separation**: interface/ → wrappers/ → implementations/
1. **Family grouping**: Wrappers organized by algorithm family (not flat)
1. **Benchmarks stay in benchmark_anns**: sage-benchmark package owns benchmarking logic
1. **No cross-layer dependencies**: L3 (libs) should not depend on L5 (benchmark)

## Old Structure (Deprecated)

```
❌ packages/sage-libs/src/sage/libs/ann/          # Interfaces only
❌ packages/sage-libs/src/sage/libs/anns/         # Flat wrapper list
❌ packages/sage-benchmark/.../algorithms_impl/   # C++ code in wrong layer

✅ packages/sage-benchmark/.../benchmark_anns/      # Benchmarks stay here (correct)
```

## References

- **Refactor Plan**: `docs-public/docs_src/dev-notes/cross-layer/ANNS_REFACTOR_PLAN.md`
- **Package Architecture**: `docs-public/docs_src/dev-notes/package-architecture.md`
