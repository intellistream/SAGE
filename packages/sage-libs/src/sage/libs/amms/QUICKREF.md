# LibAMM to AMMS Refactoring - Quick Reference

## Summary

The LibAMM submodule has been refactored into SAGE's architecture following the ANNS pattern.

## Key Changes

### Directory Structure

| Component      | Before                               | After                                     |
| -------------- | ------------------------------------ | ----------------------------------------- |
| **Algorithms** | `sage-libs/libamm/include/CPPAlgos/` | `sage-libs/amms/implementations/include/` |
|                | `sage-libs/libamm/src/CPPAlgos/`     | `sage-libs/amms/implementations/src/`     |
| **Interface**  | _(none)_                             | `sage-libs/amms/interface/`               |
| **Wrappers**   | _(PyAMM bindings)_                   | `sage-libs/amms/wrappers/`                |
| **Benchmarks** | `sage-libs/libamm/benchmark/`        | `sage-benchmark/benchmark_libamm/`        |

### Import Changes

```python
# ❌ Old (deprecated)
import PyAMM
amm = PyAMM.CountSketch(sketch_size=1000)

# ✅ New (recommended)
from sage.libs.amms import create
amm = create("countsketch", sketch_size=1000)

# ✅ Also works
from sage.libs.amms.wrappers.pyamm import PyAMM
amm = PyAMM.CountSketch(sketch_size=1000)
```

## Files Created

### Core Structure

- `packages/sage-libs/src/sage/libs/amms/`
  - `__init__.py` - Main package exports
  - `README.md` - Package documentation
  - `MIGRATION.md` - Detailed migration guide
  - `interface/` - Unified AMM interface
    - `base.py` - AmmIndex, AmmIndexMeta, StreamingAmmIndex
    - `registry.py` - Algorithm registry
    - `factory.py` - Factory functions
  - `wrappers/` - Python wrappers (to be implemented)
  - `implementations/` - C++ source code (copied from libamm)

### Benchmark

- `packages/sage-benchmark/src/sage/benchmark/benchmark_libamm/`
  - Updated `README.md` with benchmark documentation
  - All benchmark scripts and data copied from libamm

### Documentation

- Updated `sage-libs/libamm/README.md` with deprecation notice
- Created `sage-libs/amms/MIGRATION.md` with full migration guide
- Created example: `examples/tutorials/L3-libs/amms_example.py`

### Package Updates

- Updated `sage-libs/src/sage/libs/__init__.py` to export `amms`

## Next Steps

### For Development (Phase 2)

1. **Update Build System**

   ```bash
   # Update CMakeLists.txt to build from new location
   # Update pyproject.toml dependencies
   ```

1. **Create Wrappers**

   ```bash
   # Implement Python wrappers in amms/wrappers/
   # Register algorithms in the registry
   ```

1. **Migrate Tests**

   ```bash
   # Create tests in sage-libs/tests/amms/
   # Update benchmark tests
   ```

### For Testing (Phase 3)

```bash
# Test algorithm implementations
sage-dev project test --package sage-libs --filter amms

# Test benchmarks
sage-dev project test --package sage-benchmark --filter benchmark_libamm

# Run example
python examples/tutorials/L3-libs/amms_example.py
```

### For Cleanup (Phase 4-6)

1. Mark libamm as officially deprecated
1. Update all import references
1. Remove libamm submodule after verification period

## Benefits

✅ **Architectural Compliance**: Follows SAGE's L1-L6 layered architecture\
✅ **Separation of Concerns**: Algorithms (L3) separate from benchmarks (L5)\
✅ **Unified Interface**: Factory pattern like ANNS\
✅ **Better Organization**: Clear directory structure\
✅ **Consistency**: Same pattern as ANNS and other algorithm libraries

## Related Files

- Migration guide: `packages/sage-libs/src/sage/libs/amms/MIGRATION.md`
- AMMS README: `packages/sage-libs/src/sage/libs/amms/README.md`
- Benchmark README: `packages/sage-benchmark/src/sage/benchmark/benchmark_libamm/README.md`
- ANNS structure (reference): `packages/sage-libs/src/sage/libs/anns/README.md`
- Architecture docs: `docs-public/docs_src/dev-notes/package-architecture.md`

## Status

**Completed**:

- ✅ Directory structure created
- ✅ Interface layer implemented
- ✅ Files copied from libamm
- ✅ Benchmarks migrated
- ✅ Documentation updated
- ✅ Deprecation notices added

**TODO**:

- ⏳ Update build system (CMakeLists.txt)
- ⏳ Implement algorithm wrappers
- ⏳ Register algorithms in factory
- ⏳ Write tests
- ⏳ Update import paths in existing code
- ⏳ Verify functionality

**Future**:

- 📅 Remove deprecated libamm submodule
- 📅 Complete integration with SAGE benchmarking infrastructure

______________________________________________________________________

**Date**: January 2, 2026\
**Team**: IntelliStream\
**Pattern**: Following ANNS refactoring
