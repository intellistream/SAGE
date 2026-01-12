# AMMS - Approximate Matrix Multiplication (Interface Only)

> **Status**: ✅ Implementations externalized to independent package `isage-amms`

**PyPI Package**: `isage-amms`\
**Repository**: https://github.com/intellistream/sage-amms (planned)

This directory provides **interface/registry layer only**. All C++ implementations and Python
wrappers have been moved to the external `isage-amms` package.

## Installation

```bash
# Install interface + implementations
pip install isage-amms

# Or via extras (recommended for development)
pip install -e packages/sage-libs[amms]
```

## Usage

```python
from sage.libs.amms import create, registered

# Check available algorithms (requires isage-amms)
print(registered())

# Create an AMM algorithm instance
amm = create("countsketch", sketch_size=1000)
result = amm.multiply(matrix_a, matrix_b)
```

## What's in This Directory

```
amms/
├── __init__.py         # Interface exports + deprecation warning
├── README.md           # This file
└── interface/          # Abstract interfaces
    ├── base.py         # AmmIndex, AmmIndexMeta, StreamingAmmIndex
    ├── factory.py      # create(), register(), registered()
    └── registry.py     # Algorithm registry
```

**Removed** (now in `isage-amms`):

- `wrappers/` - Python wrappers
- `implementations/` - C++ source code and bindings
- Build files (pyproject.toml, setup.py, CMakeLists.txt, etc.)

## Algorithms Available (in isage-amms)

### Sketching-based

- CountSketch, FastJLT, RIP, TugOfWar

### Sampling-based

- CRS, CRSV2, BCRS, EWS

### Quantization-based

- ProductQuantization, VectorQuantization, INT8

### Advanced

- CoOccurringFD, BetaCoOFD, BlockLRA, CLMM, SMPCA, WeightedCR

## External Package Details

For installation, build instructions, and detailed documentation, see:

- **Repository**: https://github.com/intellistream/sage-amms (planned)
- **PyPI**: https://pypi.org/project/isage-amms/

## References

- Interface documentation: `interface/base.py`, `interface/factory.py`
- Externalization status: `packages/sage-libs/EXTERNALIZATION_STATUS.md`
- Migration guide: `packages/sage-libs/docs/MIGRATION_EXTERNAL_LIBS.md`
