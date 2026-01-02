# AMMS - Unified Approximate Matrix Multiplication

**Status**: 🚀 Active Development (Refactored from libamm)\
**PyPI Package**: `isage-amms`

This directory consolidates all AMM (Approximate Matrix Multiplication) algorithm code into a single
unified location.

## Quick Start

### Installation from PyPI

```bash
pip install isage-amms
```

### Installation from Source

**Note**: Building from source requires a high-memory machine (64GB+ RAM recommended).

```bash
# Clone and navigate to amms directory
cd packages/sage-libs/src/sage/libs/amms

# Quick build (on high-memory machine)
./quick_build.sh

# Install
pip install dist/isage_amms-*.whl
```

### Usage

```python
from sage.libs.amms import create, registered

# Check available algorithms
print(registered())

# Create an AMM algorithm instance (once implementations are registered)
# amm = create("countsketch", sketch_size=1000)
# result = amm.multiply(matrix_a, matrix_b)
```

## Overview

AMMS provides a unified interface for various approximate matrix multiplication algorithms, similar
to how ANNS provides a unified interface for approximate nearest neighbor search algorithms.

## Structure

```
amms/
├── interface/          # Abstract interfaces
│   ├── base.py         # AmmIndex, AmmIndexMeta
│   ├── factory.py      # create(), register(), registered()
│   └── registry.py     # Algorithm registry
│
├── wrappers/           # Python wrappers for AMM algorithms
│   └── pyamm/          # PyAMM wrapper (from libamm)
│
├── implementations/    # C++ source code
│   ├── include/        # C++ headers
│   │   ├── CPPAlgos/   # Core AMM algorithm implementations
│   │   ├── MatrixLoader/
│   │   ├── Utils/
│   │   └── ...
│   ├── src/            # C++ implementation files
│   │   ├── CPPAlgos/
│   │   ├── MatrixLoader/
│   │   └── ...
│   └── bindings/       # pybind11 bindings
│
└── benchmarks/         # Benchmark scripts (moved to sage-benchmark)
```

## Algorithms Included

LibAMM provides implementations of various AMM algorithms:

### Sketching-based Algorithms

- **CountSketch**: Count-Min Sketch based AMM
- **FastJLT**: Fast Johnson-Lindenstrauss Transform
- **RIP**: Random Index Projection
- **TugOfWar**: Tug-of-war sketch

### Sampling-based Algorithms

- **CRS**: Coordinate-wise Random Sampling
- **CRSV2**: Improved CRS
- **BCRS**: Block-wise CRS
- **EWS**: Entry-wise Sampling

### Quantization-based Algorithms

- **ProductQuantization**: Product quantization for AMM
- **VectorQuantization**: Vector quantization
- **INT8**: 8-bit integer quantization

### Advanced Algorithms

- **CoOccurringFD**: Co-occurring Feature Detection
- **BetaCoOFD**: Beta Co-occurring Feature Detection
- **BlockLRA**: Block Low-Rank Approximation
- **CLMM**: Clustered Low-rank Matrix Multiplication
- **SMPCA**: Symmetric Matrix PCA
- **WeightedCR**: Weighted Cross-Ranking

## Installation

AMMS algorithms are built as part of sage-libs. The C++ implementations require:

- **Compiler**: GCC/G++ 11+ (Ubuntu 22.04+ default)
- **CMake**: 3.14+
- **PyTorch**: 2.0.0+
- **Python**: 3.8-3.12 (3.11 recommended)
- **Memory**: 64GB+ RAM recommended for building from source

### Install from PyPI (Recommended)

```bash
pip install isage-amms
```

### Build from Source (High-Memory Machine Required)

**Important**: Building requires 64GB+ RAM. See [BUILD_PUBLISH.md](BUILD_PUBLISH.md) for detailed
instructions.

```bash
# Navigate to amms directory
cd packages/sage-libs/src/sage/libs/amms

# Quick build
./quick_build.sh

# Or use the full build script with options
./publish_to_pypi.sh --build-only --low-memory

# Install locally
pip install dist/isage_amms-*.whl
```

### Build Options

The build system supports various options:

```bash
# Low-memory build (slower but uses less RAM)
export AMMS_LOW_MEMORY_BUILD=1

# Enable CUDA support
export AMMS_ENABLE_CUDA=1
export CUDA_HOME=/usr/local/cuda

# Limit parallel jobs
export CMAKE_BUILD_PARALLEL_LEVEL=2
```

## Build and Publish to PyPI

For maintainers who want to build and publish to PyPI:

```bash
# Build only (dry-run, no upload)
./publish_to_pypi.sh

# Build and upload to TestPyPI
./publish_to_pypi.sh --test-pypi --no-dry-run

# Build and upload to PyPI (production)
./publish_to_pypi.sh --no-dry-run

# With CUDA and low-memory options
./publish_to_pypi.sh --cuda --low-memory --no-dry-run
```

See [BUILD_PUBLISH.md](BUILD_PUBLISH.md) for comprehensive build and publish documentation.

## Usage

### Using the Unified Interface

```python
from sage.libs.amms import create_amm_index

# Create an AMM index using the factory
amm = create_amm_index("countsketch", config={
    "sketch_size": 1000,
    "hash_functions": 5
})

# Perform approximate matrix multiplication
result = amm.multiply(matrix_a, matrix_b)
```

### Direct Algorithm Usage

```python
from sage.libs.amms.wrappers.pyamm import PyAMM

# Create a specific AMM algorithm instance
amm = PyAMM.CountSketch(sketch_size=1000)

# Use the algorithm
result = amm.multiply(matrix_a, matrix_b)
```

## Benchmarking

For benchmarking AMM algorithms, see the `sage-benchmark` package:

```bash
# Run AMM benchmarks
sage-dev benchmark amm --algorithms countsketch,fastjlt --datasets dataset1
```

See `packages/sage-benchmark/src/sage/benchmark/benchmark_libamm/README.md` for details.

## Migration from libamm

This module is refactored from the original libamm submodule:

- **Algorithm implementations**: Moved from `libamm/include/CPPAlgos` and `libamm/src/CPPAlgos` to
  `amms/implementations/`
- **Benchmarking code**: Moved from `libamm/benchmark/` to `sage-benchmark/benchmark_libamm/`
- **Python bindings**: Refactored into `amms/wrappers/pyamm/`
- **Interface layer**: New unified interface similar to ANNS

## Architecture Alignment

AMMS follows SAGE's architecture principles:

- **Layer 3 (L3-libs)**: Algorithm implementations and interfaces
- **Separation of concerns**: Core algorithms (amms/) vs benchmarking (benchmark_libamm/)
- **Unified interfaces**: Factory pattern for algorithm creation
- **Modular design**: Independent wrappers for different algorithm families

## References

- Original LibAMM paper and documentation
- PyTorch integration guide
- AMM algorithm theory and applications

## Contributing

When adding new AMM algorithms:

1. Add C++ implementation to `implementations/include/CPPAlgos/` and `implementations/src/CPPAlgos/`
1. Create Python wrapper in `wrappers/`
1. Register algorithm in `interface/registry.py`
1. Add tests in `sage-libs/tests/`
1. Add benchmark configuration in `sage-benchmark/benchmark_libamm/`

See `CONTRIBUTING.md` at project root for detailed guidelines.
