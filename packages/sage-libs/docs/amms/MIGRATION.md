# LibAMM Refactoring Migration Guide

## Overview

This document describes the refactoring of LibAMM from a monolithic submodule into SAGE's layered
architecture, following the same pattern used for ANNS algorithms.

## Migration Date

January 2, 2026

## Rationale

The original LibAMM was structured as a single submodule containing both:

1. **Core AMM algorithms** (C++ implementations in CPPAlgos/)
1. **Benchmarking code** (benchmark/)

This violated SAGE's architectural principle of layer separation:

- **L3 (sage-libs)**: Should contain reusable algorithm implementations
- **L5 (sage-benchmark)**: Should contain benchmarking and evaluation code

The refactoring aligns LibAMM with SAGE's architecture, similar to the ANNS structure.

## Migration Structure

### Before (Original LibAMM)

```
packages/sage-libs/src/sage/libs/libamm/  (submodule)
├── include/CPPAlgos/          # Algorithm headers
├── src/CPPAlgos/              # Algorithm implementations
├── benchmark/                 # Benchmark code
├── CMakeLists.txt
├── setup.py
└── README.md
```

### After (Refactored)

```
packages/sage-libs/src/sage/libs/amms/
├── interface/                 # Unified AMM interface (NEW)
│   ├── base.py               # AmmIndex, AmmIndexMeta
│   ├── factory.py            # create(), register()
│   └── registry.py           # Algorithm registry
│
├── wrappers/                  # Python wrappers (NEW)
│   └── pyamm/                # PyAMM wrapper
│
├── implementations/           # C++ source code (MIGRATED)
│   ├── include/              # From libamm/include/
│   ├── src/                  # From libamm/src/
│   ├── cmake/                # From libamm/cmake/
│   └── CMakeLists.txt        # From libamm/CMakeLists.txt
│
└── README.md                  # Updated documentation

packages/sage-benchmark/src/sage/benchmark/benchmark_libamm/
├── scripts/                   # From libamm/benchmark/scripts/
├── src/                       # From libamm/benchmark/src/
├── perfLists/                 # From libamm/benchmark/perfLists/
├── config.csv                 # From libamm/benchmark/config.csv
└── README.md                  # Updated documentation
```

## Key Changes

### 1. Algorithm Implementations

**Moved from**: `sage-libs/libamm/include/CPPAlgos/` and `sage-libs/libamm/src/CPPAlgos/`\
**Moved to**: `sage-libs/amms/implementations/`

All C++ algorithm implementations remain intact but are now organized under a cleaner structure.

### 2. Interface Layer (NEW)

**Created**: `sage-libs/amms/interface/`

A new unified interface layer modeled after ANNS:

- `AmmIndex`: Abstract base class for all AMM algorithms
- `AmmIndexMeta`: Metadata describing algorithm capabilities
- `StreamingAmmIndex`: Extended interface for streaming algorithms
- Factory pattern for algorithm instantiation
- Registry for algorithm discovery

### 3. Benchmark Code

**Moved from**: `sage-libs/libamm/benchmark/`\
**Moved to**: `sage-benchmark/benchmark_libamm/`

Benchmark code is now properly separated at L5, following SAGE's architecture.

### 4. Build System

The build system is updated to:

- Build AMM algorithms as part of sage-libs
- Build benchmarks as part of sage-benchmark
- Maintain proper layer dependencies (L5 depends on L3, not vice versa)

## Usage Changes

### Before (Direct PyAMM usage)

```python
import PyAMM

# Direct usage of PyAMM
amm = PyAMM.CountSketch(sketch_size=1000)
result = amm.multiply(matrix_a, matrix_b)
```

### After (Unified Interface)

```python
from sage.libs.amms import create

# Use unified interface
amm = create("countsketch", sketch_size=1000)
result = amm.multiply(matrix_a, matrix_b)

# Or direct usage still works
from sage.libs.amms.wrappers.pyamm import PyAMM
amm = PyAMM.CountSketch(sketch_size=1000)
result = amm.multiply(matrix_a, matrix_b)
```

## Benefits

1. **Architectural Compliance**: Follows SAGE's L1-L6 architecture
1. **Separation of Concerns**: Algorithms (L3) separate from benchmarks (L5)
1. **Reusability**: Unified interface makes algorithms easier to use
1. **Consistency**: Similar structure to ANNS for easier navigation
1. **Extensibility**: Factory pattern simplifies adding new algorithms
1. **Maintainability**: Clearer organization reduces cognitive load

## Compatibility

### Backward Compatibility

The original LibAMM submodule remains in place temporarily for:

- Git history preservation
- Gradual migration of dependent code
- Verification that all functionality is preserved

### Migration Path

1. **Phase 1** (Current): New structure created, core files copied
1. **Phase 2**: Update build system and imports
1. **Phase 3**: Migrate all references to new structure
1. **Phase 4**: Update documentation and examples
1. **Phase 5**: Mark old libamm as deprecated
1. **Phase 6**: Remove old libamm submodule (after verification period)

## Testing

Ensure all tests pass after migration:

```bash
# Test algorithm implementations
sage-dev project test --package sage-libs --filter amms

# Test benchmarks
sage-dev project test --package sage-benchmark --filter benchmark_libamm

# Run benchmark smoke tests
python packages/sage-benchmark/src/sage/benchmark/benchmark_libamm/pythonTest.py
```

## Related Documentation

- Architecture: `docs-public/docs_src/dev-notes/package-architecture.md`
- ANNS Structure: `packages/sage-libs/src/sage/libs/anns/README.md`
- Benchmark Guidelines: `packages/sage-benchmark/README.md`

## Questions and Issues

For questions about this migration, please:

1. Check this document and related READMEs
1. Review the ANNS structure for similar patterns
1. Consult the SAGE architecture documentation
1. Open an issue on GitHub with tag `refactor/libamm`

## Contributors

Migration led by: IntelliStream Team\
Date: January 2026\
Based on: ANNS refactoring pattern
