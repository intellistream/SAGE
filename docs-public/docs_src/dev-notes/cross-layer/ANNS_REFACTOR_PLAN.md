# ANNS Architecture Refactor Plan

**Date**: 2025-12-28\
**Status**: 🚧 Planning\
**Issue**: ANNS-related code scattered across 3 locations with unclear separation

______________________________________________________________________

## 🚨 Current Problem

ANNS (Approximate Nearest Neighbor Search) related code is currently **scattered across three
locations**:

1. **`packages/sage-libs/src/sage/libs/ann/`** (L3)

   - Purpose: Unified ANN interface (abstract base classes)
   - Contains: `AnnIndex`, `AnnIndexMeta`, factory, registry
   - Size: ~5 files, interface-only

1. **`packages/sage-libs/src/sage/libs/anns/`** (L3)

   - Purpose: Python wrappers for various ANNS algorithms
   - Contains: 23 algorithm implementations (faiss_HNSW, vsag_hnsw, diskann, candy\_\*, cufe, gti,
     puck, etc.)
   - Size: 23 subdirectories, each with Python wrappers

1. **`packages/sage-benchmark/src/sage/benchmark/benchmark_anns/algorithms_impl/`** (L5)

   - Purpose: C++ source code implementations
   - Contains: candy/, diskann-ms/, faiss/, gti/, puck/, vsag/, SPTAG/, include/, bindings/
   - Size: Large C++ codebase with multiple ANNS libraries

### Why This Is Problematic

1. **Confusing naming**: `ann` (singular) vs `anns` (plural) - unclear distinction
1. **Scattered responsibilities**: Interface, wrappers, and implementations in 3 different packages
1. **Cross-layer dependencies**: L5 (benchmark) contains code that L3 (libs) depends on
1. **Duplicate structure**: benchmark_anns has algorithms_impl that mirrors sage-libs/anns
1. **Unclear ownership**: Who maintains what? Where to add new algorithms?

______________________________________________________________________

## ✅ Proposed Solution

### Unified Structure: `packages/sage-libs/src/sage/libs/anns/`

Consolidate everything ANNS-related into **ONE location** with clear subdirectories:

```
packages/sage-libs/src/sage/libs/anns/
├── __init__.py                    # Public API exports
├── README.md                      # Architecture overview
│
├── interface/                     # Abstract interfaces (formerly sage-libs/ann)
│   ├── __init__.py
│   ├── base.py                   # AnnIndex, AnnIndexMeta
│   ├── factory.py                # create(), register(), registered()
│   └── registry.py               # Algorithm registry
│
├── wrappers/                      # Python wrappers (formerly sage-libs/anns/*)
│   ├── __init__.py
│   ├── faiss/
│   │   ├── faiss_HNSW.py
│   │   ├── faiss_IVFPQ.py
│   │   ├── faiss_NSW.py
│   │   └── ...
│   ├── vsag/
│   │   └── vsag_hnsw.py
│   ├── diskann/
│   │   ├── diskann.py
│   │   └── ipdiskann.py
│   ├── candy/
│   │   ├── candy_lshapg.py
│   │   ├── candy_mnru.py
│   │   └── candy_sptag.py
│   ├── cufe/
│   ├── gti/
│   ├── puck/
│   └── plsh/
│
├── implementations/               # C++ source code (formerly benchmark_anns/algorithms_impl)
│   ├── README.md                 # Build instructions
│   ├── CMakeLists.txt
│   ├── build.sh
│   ├── candy/                    # C++ source
│   │   ├── AbstractIndex.cpp
│   │   ├── ...
│   ├── diskann-ms/               # Submodule or vendored
│   ├── faiss/                    # Submodule
│   ├── vsag/                     # Submodule
│   ├── gti/
│   ├── puck/
│   ├── SPTAG/
│   ├── include/                  # Shared headers
│   └── bindings/                 # pybind11 bindings
│       └── PyCANDY.cpp
│
└── benchmarks/                    # Benchmark scripts (from benchmark_anns)
    ├── __init__.py
    ├── run_benchmark.py
    ├── prepare_dataset.py
    ├── compute_gt.py
    └── tests/
```

### Key Benefits

1. **Single source of truth**: Everything ANNS in one place
1. **Clear separation**: interface/ → wrappers/ → implementations/ → benchmarks/
1. **Easy navigation**: Developers know exactly where to look
1. **Consistent ownership**: sage-libs package owns all ANNS code
1. **Proper layering**: L3 doesn't depend on L5 anymore

______________________________________________________________________

## 📋 Migration Steps

### Phase 1: Create New Structure (No Code Changes)

1. Create `/home/shuhao/SAGE/packages/sage-libs/src/sage/libs/anns_new/` (temporary)
1. Create subdirectories: `interface/`, `wrappers/`, `implementations/`, `benchmarks/`
1. Copy README and architecture docs

### Phase 2: Move Interface Layer

```bash
# Move sage-libs/ann → anns_new/interface
mv packages/sage-libs/src/sage/libs/ann/base.py packages/sage-libs/src/sage/libs/anns_new/interface/
mv packages/sage-libs/src/sage/libs/ann/factory.py packages/sage-libs/src/sage/libs/anns_new/interface/
```

**Files to update**:

- All imports: `from sage.libs.ann` → `from sage.libs.anns.interface`

### Phase 3: Reorganize Wrappers

```bash
# Group by algorithm family
mkdir -p packages/sage-libs/src/sage/libs/anns_new/wrappers/{faiss,vsag,diskann,candy,cufe,gti,puck,plsh}

# Move faiss wrappers
mv packages/sage-libs/src/sage/libs/anns/faiss_* packages/sage-libs/src/sage/libs/anns_new/wrappers/faiss/

# Move other wrappers similarly
```

**Files to update**:

- All imports: `from sage.libs.anns.faiss_HNSW` → `from sage.libs.anns.wrappers.faiss.faiss_HNSW`

### Phase 4: Move C++ Implementations

```bash
# Move from benchmark_anns to sage-libs
mv packages/sage-benchmark/src/sage/benchmark/benchmark_anns/algorithms_impl/* \
   packages/sage-libs/src/sage/libs/anns_new/implementations/
```

**Files to update**:

- CMakeLists.txt paths
- Build scripts
- Python bindings imports

### Phase 5: Move Benchmark Code

```bash
# Move benchmark scripts
mv packages/sage-benchmark/src/sage/benchmark/benchmark_anns/{run_benchmark.py,prepare_dataset.py,compute_gt.py} \
   packages/sage-libs/src/sage/libs/anns_new/benchmarks/
```

**Keep in benchmark_anns**:

- High-level benchmark orchestration
- Results visualization
- CI/CD integration scripts

### Phase 6: Update All Imports

Files likely to need updates:

```bash
# Find all imports
rg "from sage\.libs\.ann " --type py
rg "from sage\.libs\.anns\." --type py
rg "import sage\.libs\.ann" --type py
rg "benchmark_anns\.algorithms_impl" --type py
```

Update patterns:

- `sage.libs.ann` → `sage.libs.anns.interface`
- `sage.libs.anns.<algo>` → `sage.libs.anns.wrappers.<family>.<algo>`
- `benchmark_anns.algorithms_impl` → `sage.libs.anns.implementations`

### Phase 7: Rename and Cleanup

```bash
# Rename anns_new → anns
rm -rf packages/sage-libs/src/sage/libs/ann/  # Old interface
rm -rf packages/sage-libs/src/sage/libs/anns/  # Old wrappers
mv packages/sage-libs/src/sage/libs/anns_new packages/sage-libs/src/sage/libs/anns

# Clean up benchmark_anns
rm -rf packages/sage-benchmark/src/sage/benchmark/benchmark_anns/algorithms_impl/
```

### Phase 8: Testing

1. **Build tests**: Ensure C++ implementations compile
1. **Import tests**: Verify all imports work
1. **Unit tests**: Run existing algorithm tests
1. **Benchmark tests**: Verify benchmarks still run
1. **Integration tests**: Test with sage-db, sage-flow

______________________________________________________________________

## 🎯 Success Criteria

- [ ] All ANNS code in `packages/sage-libs/src/sage/libs/anns/`
- [ ] Clear 4-layer structure: interface → wrappers → implementations → benchmarks
- [ ] No cross-package dependencies for ANNS (L5 doesn't depend on L3 implementations)
- [ ] All existing tests pass
- [ ] Documentation updated
- [ ] No `sage.libs.ann` (singular) references remain

______________________________________________________________________

## ⚠️ Risks and Mitigation

| Risk                  | Impact | Mitigation                                     |
| --------------------- | ------ | ---------------------------------------------- |
| Break existing code   | High   | Phase-by-phase migration with tests            |
| C++ build issues      | Medium | Keep build scripts, update paths carefully     |
| Import path confusion | High   | Clear deprecation warnings, update all at once |
| Submodule conflicts   | Medium | Document submodule structure, test builds      |

______________________________________________________________________

## 📅 Timeline Estimate

- **Phase 1-2**: 1-2 hours (create structure, move interface)
- **Phase 3**: 2-3 hours (reorganize wrappers)
- **Phase 4**: 2-3 hours (move C++ implementations)
- **Phase 5**: 1 hour (move benchmarks)
- **Phase 6**: 3-4 hours (update all imports)
- **Phase 7**: 1 hour (rename and cleanup)
- **Phase 8**: 2-3 hours (testing)

**Total**: 12-17 hours

______________________________________________________________________

## 🔗 Related Documents

- **Current Structure**: `packages/sage-benchmark/src/sage/benchmark/benchmark_anns/STRUCTURE.md`
- **ANN Interface**: `packages/sage-libs/src/sage/libs/ann/README.md` (if exists)
- **Package Architecture**: `docs-public/docs_src/dev-notes/package-architecture.md`

______________________________________________________________________

## 💡 Future Enhancements (Post-Refactor)

1. **Unified documentation**: Single README explaining all ANNS algorithms
1. **Benchmark dashboard**: Visualize algorithm performance comparisons
1. **Auto-registration**: Wrappers auto-register with factory on import
1. **Type stubs**: Better IDE support for algorithm selection
1. **Performance profiles**: Pre-computed characteristics for each algorithm

______________________________________________________________________

**Status**: Ready for implementation\
**Owner**: SAGE Core Team\
**Priority**: Medium (improves maintainability, not urgent)
