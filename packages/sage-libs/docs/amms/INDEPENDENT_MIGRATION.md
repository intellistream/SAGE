# AMMS Independent Repository Migration (2026-01-09)

## ✅ COMPLETED

**Repository**: https://github.com/intellistream/sage-amms\
**Status**: Migration completed on January 9, 2026

## Summary

AMM (Approximate Matrix Multiplication) implementations have been successfully migrated to an
independent repository and published as `isage-amms`.

- **SAGE keeps**: Lightweight Python interface/registry
  (`packages/sage-libs/src/sage/libs/amms/interface`)
- **Migrated to sage-amms**: All C++ sources, bindings, and build scripts

## Installation

```bash
# Install the independent package
pip install isage-amms

# Use through SAGE interface
from sage.libs.amms import create
amm = create("countsketch", sketch_size=1000)
```

## Repository Details

- **URL**: https://github.com/intellistream/sage-amms
- **PyPI**: https://pypi.org/project/isage-amms/ (pending first publish)
- **License**: MIT
- **First Commit**: a747bcd (2026-01-09)

## What was migrated

- ✅ C++ implementations (`implementations/include`, `implementations/src`)
- ✅ CMake build system
- ✅ pybind11 bindings
- ✅ pyproject.toml and setup.py
- ✅ LICENSE (MIT), README.md, .gitignore

## What remains in SAGE

- ✅ Python interface layer (`sage.libs.amms.interface`)
- ✅ Factory pattern (`create`, `register`, `registered`)
- ✅ Base classes (`AmmIndex`, `AmmIndexMeta`)
- ✅ Documentation

## Compatibility Policy

SAGE retains the Python interface so existing code continues to work:

```python
from sage.libs.amms import create  # ✅ Still works
```

If `isage-amms` is not installed:

- `registered()` returns empty list
- `create(...)` raises `KeyError` with installation hint
- No silent fallbacks

## Next Steps

- [ ] Publish `isage-amms` to PyPI via sage-pypi-publisher
- [ ] Set up CI/CD in sage-amms repo for CPU/CUDA wheels
- [ ] Update SAGE documentation to point to sage-amms repo
