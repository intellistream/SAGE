# LibAMM Benchmarks#Benchmark

This directory contains performance benchmarks for LibAMM (Library for Approximate Matrix
Multiplication).User applications can be developed that uses the generated lib.

Benchmark module can be used as application template.

## Overview

These benchmarks evaluate LibAMM's performance on real-world datasets for various matrix
multiplication scenarios.

## Migration Notice

🔄 **This benchmark suite has been migrated from the LibAMM repository to the SAGE benchmark
package.**

- **Original location**: `intellistream/LibAMM/benchmark/`
- **New location**:
  `intellistream/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_libamm/`
- **Datasets location**: `intellistream/sageData/libamm-benchmark/datasets/`

## Structure

```
benchmark_libamm/
├── src/              # C++ benchmark source files
├── scripts/          # Helper scripts for running benchmarks
├── figures/          # Visualization outputs
├── perfLists/        # Performance configuration files
├── CMakeLists.txt    # Build configuration
└── config.csv        # Benchmark configuration
```

## Datasets

Benchmark datasets are managed in the **sageData** repository with Git LFS.

The datasets are located at: `../../data/libamm-benchmark/datasets/` (relative to this directory in
SAGE workspace).

For more information, see: https://github.com/intellistream/sageData

## Building

```bash
cd benchmark_libamm
mkdir build && cd build
cmake ..
cmake --build .
```

## Related

- LibAMM: https://github.com/intellistream/LibAMM
- sageData: https://github.com/intellistream/sageData
- SAGE: https://github.com/intellistream/SAGE
