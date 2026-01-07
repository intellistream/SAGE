# ANNS Algorithms Migration to Independent Repository

## Overview

This document describes the migration of ANNS (Approximate Nearest Neighbor Search) algorithms from
sage-libs to an independent repository `sage-anns`, following the same pattern used for LibAMM.

## Migration Date

January 8, 2026

## Rationale

The ANNS implementations were originally embedded in `sage-libs/anns/implementations/` with:

1. **C++ algorithm implementations** (FAISS, DiskANN, CANDY, PUCK, SPTAG, etc.)
1. **Python wrappers** (interface layer)
1. **Build configuration** (CMakeLists.txt, build scripts)

This structure had several issues:

- **Large repository size**: C++ source code and third-party libraries increased repo size
- **Complex build dependencies**: Required CMake, C++ compilers, and third-party libraries
- **Version management**: Difficult to version ANNS algorithms independently
- **Distribution**: Users who don't need C++ extensions still download the code

## Migration Strategy

### Before (Original Structure)

```
packages/sage-libs/src/sage/libs/anns/
├── implementations/        # C++ source code (TO BE MOVED)
│   ├── FAISS/
│   ├── diskann-ms/
│   ├── candy/
│   ├── puck/
│   ├── SPTAG/
│   ├── CMakeLists.txt
│   └── build_all.sh
├── interface/              # Python interface (KEEP)
│   ├── base.py
│   ├── factory.py
│   └── registry.py
└── wrappers/               # Python wrappers (KEEP)
    └── ...
```

### After (Independent Repository)

**New Repository**: `https://github.com/intellistream/sage-anns`

```
sage-anns/                  # Independent repository
├── implementations/        # MOVED from sage-libs
│   ├── faiss/
│   ├── diskann-ms/
│   ├── candy/
│   ├── puck/
│   ├── SPTAG/
│   └── CMakeLists.txt
├── python/
│   └── sage_anns/         # Python bindings
│       ├── __init__.py
│       └── factory.py
├── CMakeLists.txt
├── pyproject.toml
├── README.md
└── build_all.sh
```

**SAGE repo** (sage-libs):

```
packages/sage-libs/src/sage/libs/anns/
├── interface/              # KEEP: Unified interface
│   ├── base.py
│   ├── factory.py
│   └── registry.py
└── wrappers/               # KEEP: Python wrappers
    └── ...
```

## Key Changes

### 1. C++ Implementations → Independent Repository

**Status**: ✅ **Completed** - Repository created and code migrated

- **Repository**: https://github.com/intellistream/sage-anns
- **PyPI Package**: https://pypi.org/project/isage-anns/
- **Latest Version**: v0.1.1 (Published using sage-pypi-publisher)
- **Installation**: `pip install isage-anns`

**What moved**:

- All C++ source code from `implementations/`
- Third-party libraries (FAISS, DiskANN, etc.)
- Build scripts and CMakeLists.txt
- Python bindings for compiled extensions

**What stays in sage-libs**:

- Python interface layer (`interface/`)
- Python wrappers that don't require C++ compilation
- Factory pattern and registry

### 2. Package Distribution

**PyPI Package**: `isage-anns` ✅ **Published**

- **Package Name**: isage-anns
- **PyPI URL**: https://pypi.org/project/isage-anns/
- **Latest Version**: 0.1.1
- **Published Date**: January 8, 2026
- **Publisher**: sage-pypi-publisher (--mode public)

**Installation**:

```bash
# Users install separately (recommended)
pip install isage-anns
```

**sage-libs dependency** (in `pyproject.toml`):

```toml
dependencies = [
    # ANNS algorithms (独立仓库，可选依赖)
    # Note: Install separately if needed
    # Repository: https://github.com/intellistream/sage-anns
    # PyPI: https://pypi.org/project/isage-anns/
    # "isage-anns>=0.1.1",  # Optional dependency
]
```

### 3. Import Changes

**Before** (embedded):

```python
from sage.libs.anns.implementations.faiss import FaissIndex
```

**After** (independent package):

```python
# Option 1: Direct import from isage-anns
from sage_anns import create_index
index = create_index("faiss_hnsw", dimension=128)

# Option 2: Through SAGE interface (recommended)
from sage.libs.anns import create_index
index = create_index("faiss_hnsw", dimension=128)
```

The SAGE interface will automatically detect and use `isage-anns` if installed.

## Migration Steps

### Phase 1: Preparation ✅ DONE

- [x] Create `sage-anns` repository
- [x] Set up project structure (pyproject.toml, CMakeLists.txt)
- [x] Add README and documentation
- [x] Update sage-libs pyproject.toml

### Phase 2: Code Migration (TODO)

- [ ] Copy C++ implementations to sage-anns repo
- [ ] Update CMakeLists.txt in sage-anns
- [ ] Configure Python bindings
- [ ] Add tests
- [ ] Build and test locally

### Phase 3: Testing & Publishing (TODO)

- [ ] Build wheels for multiple platforms
- [ ] Test installation: `pip install isage-anns`
- [ ] Publish to PyPI
- [ ] Update sage-libs to depend on isage-anns

### Phase 4: Cleanup (TODO)

- [ ] Remove `implementations/` from sage-libs
- [ ] Update sage-libs CMakeLists.txt
- [ ] Remove C++ build dependencies from sage-libs
- [ ] Update documentation

## Build System Changes

### sage-anns (Independent)

```toml
[build-system]
requires = [
    "scikit-build-core>=0.8.0",
    "pybind11>=2.10.0",
]
build-backend = "scikit_build_core.build"
```

Builds self-contained wheels with compiled extensions.

### sage-libs (After Migration)

```toml
[build-system]
requires = [
    "setuptools>=64",
    # No longer needs CMake/pybind11 for ANNS
]
build-backend = "setuptools.build_meta"
```

Pure Python package that optionally uses `isage-anns`.

## Compatibility

**Backward Compatibility**:

The SAGE interface layer maintains backward compatibility:

```python
# This will work regardless of where ANNS implementations come from
from sage.libs.anns import create_index
index = create_index("faiss_hnsw", dimension=128)
```

**Graceful Degradation**:

If `isage-anns` is not installed, SAGE will:

- Provide helpful error messages
- Suggest installation: `pip install isage-anns`
- Continue working with other features

## Benefits

1. **Smaller sage-libs package**: No C++ code, faster installation
1. **Independent versioning**: ANNS can be updated without SAGE release
1. **Optional dependency**: Users choose if they need ANNS algorithms
1. **Easier CI/CD**: Separate build pipelines for Python and C++
1. **Better modularity**: Clear separation of concerns

## Repository Links

- **SAGE ANNS**: https://github.com/intellistream/sage-anns
- **PyPI Package**: https://pypi.org/project/isage-anns/ ✅ Published v0.1.1
- **SAGE Main**: https://github.com/intellistream/SAGE

## Related Migrations

- **LibAMM**: Similar migration completed on 2026-01-02
- **See**: `packages/sage-libs/docs/amms/MIGRATION.md`

## Questions & Issues

- **Issues**: https://github.com/intellistream/sage-anns/issues
- **Discussion**: https://github.com/intellistream/SAGE/discussions
