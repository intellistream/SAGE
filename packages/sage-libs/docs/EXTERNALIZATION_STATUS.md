# sage-libs Externalization Status

**Date**: 2026-01-09\
**Status**: ✅ ANNS and AMMS implementations successfully externalized

## Summary

`sage-libs` has been refactored to serve as an **interface/registry layer only**. Heavy
implementations have been moved to independent PyPI packages.

## Completed Migrations

### ✅ ANNS (Approximate Nearest Neighbor Search)

- **External package**: `isage-anns`
- **Repository**: https://github.com/intellistream/sage-anns
- **What was removed**:
  - `anns/wrappers/` - all algorithm wrappers (FAISS, DiskANN, CANDY, etc.)
  - `anns/implementations/` - C++ source code and bindings
- **What remains**:
  - `anns/interface/` - base classes, factory, registry
  - `anns/interface/implementations/dummy.py` - lightweight dummy implementation for testing
- **Installation**: `pip install -e packages/sage-libs[anns]`

### ✅ AMMS (Approximate Matrix Multiplication)

- **External package**: `isage-amms`
- **Repository**: https://github.com/intellistream/sage-amms (planned)
- **What was removed**:
  - `amms/wrappers/` - Python wrappers for AMM algorithms
  - `amms/implementations/` - C++ source code
  - `amms/{LICENSE,MANIFEST.in,pyproject.toml,setup.py,clean.sh,.gitignore}` - standalone build
    files
- **What remains**:
  - `amms/interface/` - base classes, factory, registry
- **Installation**: `pip install -e packages/sage-libs[amms]`

## Current Structure

```
packages/sage-libs/src/sage/libs/
├── anns/
│   ├── __init__.py          # Interface exports + deprecation warning
│   ├── README.md            # Externalization status
│   └── interface/           # Base classes, factory, registry
│       ├── base.py
│       ├── factory.py
│       └── implementations/dummy.py  # Lightweight test impl
│
├── amms/
│   ├── __init__.py          # Interface exports + deprecation warning
│   ├── README.md            # Externalization status
│   └── interface/           # Base classes, factory, registry
│
├── agentic/                 # To be externalized (planned)
├── rag/                     # To be externalized (planned)
├── privacy/                 # To be externalized (planned)
├── foundation/              # Pure Python utilities (stays)
├── integrations/            # Thin adapters (stays)
└── finetune/                # Training utilities (stays)
```

## Installation

### Basic (interface only)

```bash
pip install isage-libs
```

### With optional implementations

```bash
# ANNS algorithms
pip install isage-libs[anns]

# AMM algorithms
pip install isage-libs[amms]

# All optional packages
pip install isage-libs[all]
```

### Development mode

```bash
pip install -e packages/sage-libs[anns,amms]
```

## Migration Impact

### ✅ Backward Compatibility

- Import paths remain unchanged: `from sage.libs.anns import create`
- Factory pattern remains stable
- Deprecation warnings guide users to install external packages

### ⚠️ Breaking Changes

- Direct imports from `sage.libs.anns.wrappers.*` will fail (these modules no longer exist)
- Direct imports from `sage.libs.amms.wrappers.*` will fail (these modules no longer exist)
- Users must install external packages to use concrete algorithms

### 📝 Documentation Updates Needed

- `docs/amms/*.md` - references to `implementations/` and `wrappers/` (historical docs)
- `docs/anns/*.md` - migration guides (historical)
- Tests: `tests/lib/test_libamm.py` - updated to reference external package

## Next Steps (Planned)

### 🚧 Agentic Module

- Target package: `isage-agentic`
- Keep: protocols, registries, intent classification
- Move: heavy planners, workflow engines, bot implementations

### 🚧 RAG Toolkit

- Target package: `isage-rag`
- Keep: protocols, light pipelines
- Move: retrievers, chunkers, rerankers, heavy processing

### 🚧 Privacy Module

- Target package: `isage-privacy`
- Keep: protocols, shared utilities
- Move: unlearning algorithms, privacy-preserving implementations

## Testing

```bash
# Test interface layer (no external deps needed)
pytest packages/sage-libs/tests/

# Test with external implementations (requires isage-anns, isage-amms)
pip install isage-anns isage-amms
pytest packages/sage-libs/tests/
```

## References

- Migration guide: `packages/sage-libs/docs/MIGRATION_EXTERNAL_LIBS.md`
- ANNS README: `packages/sage-libs/src/sage/libs/anns/README.md`
- AMMS README: `packages/sage-libs/src/sage/libs/amms/README.md`
- Package architecture: `docs-public/docs_src/dev-notes/package-architecture.md`
- Dependency spec: `dependencies-spec.yaml`

______________________________________________________________________

**Principle**: Keep sage-libs as a lightweight interface layer. Heavy implementations belong in
independent packages with their own versioning, CI/CD, and release cycles.
