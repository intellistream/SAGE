# Building and Publishing isage-amms to PyPI

> **⚠️ DEPRECATED**: The `sage-dev package pypi` command has been removed. Please use the standalone
> [sage-pypi-publisher](https://github.com/intellistream/sage-pypi-publisher) tool instead.
>
> **Migration**:
>
> ```bash
> git clone https://github.com/intellistream/sage-pypi-publisher.git
> cd sage-pypi-publisher
> ./publish.sh <package-name> --auto-bump patch
> ```

## Overview

This document provides instructions for building and publishing the `isage-amms` package to PyPI.
**Building this package requires a high-memory machine (64GB+ RAM recommended)** due to C++
compilation requirements.

## Prerequisites

### System Requirements

- **Memory**: 64GB+ RAM recommended (minimum 32GB with swap)
- **CPU**: Multi-core processor (8+ cores recommended)
- **OS**: Linux (Ubuntu 22.04+ recommended)
- **Disk**: 10GB+ free space

### Software Requirements

```bash
# Compiler and build tools
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libopenblas-dev \
    liblapack-dev \
    g++-11 \
    gcc-11

# Python development
sudo apt-get install -y python3-dev python3-pip

# Optional: CUDA for GPU support
# Install CUDA Toolkit 11.8+ from NVIDIA
```

### Python Requirements

```bash
pip install --upgrade pip setuptools wheel build twine
pip install torch>=2.0.0  # CPU or CUDA version
pip install pybind11>=2.10.0
```

## Package Structure

```
amms/
├── pyproject.toml          # Package metadata and dependencies
├── setup.py                # Build script with CMake integration
├── MANIFEST.in             # Files to include in distribution
├── publish_to_pypi.sh      # Automated build and publish script
├── interface/              # Python interface layer
├── wrappers/               # Python wrappers (to be implemented)
└── implementations/        # C++ source code
    ├── CMakeLists.txt      # CMake build configuration
    ├── include/            # C++ headers
    ├── src/                # C++ implementation
    └── cmake/              # CMake modules
```

## Building the Package

### Method 1: Using the Automated Script (Recommended)

```bash
cd packages/sage-libs/src/sage/libs/amms

# Dry-run build (no upload)
./publish_to_pypi.sh

# Build only
./publish_to_pypi.sh --build-only

# Low-memory build (slower but uses less RAM)
./publish_to_pypi.sh --build-only --low-memory

# CUDA-enabled build
./publish_to_pypi.sh --build-only --cuda

# Combined options
./publish_to_pypi.sh --build-only --cuda --low-memory
```

**Script Options**:

- `--no-dry-run`: Actually upload to PyPI (default is dry-run)
- `--test-pypi`: Upload to TestPyPI instead of PyPI
- `--build-only`: Only build, don't upload
- `--cuda`: Enable CUDA support
- `--low-memory`: Use low-memory build mode (reduces RAM usage)

### Method 2: Manual Build

```bash
cd packages/sage-libs/src/sage/libs/amms

# Clean previous builds
rm -rf dist/ build/ *.egg-info implementations/build/

# For low-memory builds, set environment variable
export AMMS_LOW_MEMORY_BUILD=1

# For CUDA builds
export AMMS_ENABLE_CUDA=1
export CUDA_HOME=/usr/local/cuda

# Build source distribution and wheel
python3 -m build --sdist --wheel .
```

### Build Output

After building, you'll find:

- `dist/isage-amms-<version>.tar.gz` - Source distribution
- `dist/isage_amms-<version>-<platform>.whl` - Wheel distribution

## Testing the Build

### Local Installation

```bash
# Install from local build
pip install dist/isage_amms-*.whl

# Test import
python3 -c "from sage.libs.amms import create, registered; print(registered())"
```

### Test on TestPyPI

```bash
# Upload to TestPyPI
./publish_to_pypi.sh --test-pypi --no-dry-run

# Install from TestPyPI
pip install -i https://test.pypi.org/simple/ isage-amms

# Test
python3 -c "from sage.libs.amms import create; print('OK')"
```

## Publishing to PyPI

### Configure PyPI Credentials

Create or edit `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...  # Your PyPI token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgENdGVzdC5weXBp...  # Your TestPyPI token
```

**Security Note**: Keep your PyPI tokens secure and never commit them to Git.

### Upload to TestPyPI (Recommended First)

```bash
./publish_to_pypi.sh --test-pypi --no-dry-run
```

### Upload to Production PyPI

```bash
./publish_to_pypi.sh --no-dry-run
```

## Using sage-dev CLI (Alternative)

You can also use the SAGE development CLI:

```bash
# From SAGE root directory
cd /path/to/SAGE

# Build and publish to TestPyPI
sage-dev package pypi build sage-libs-amms --upload --test-pypi --no-dry-run

# Build and publish to PyPI
sage-dev package pypi build sage-libs-amms --upload --no-dry-run
```

**Note**: The sage-dev CLI requires the package to be properly integrated into the SAGE build
system.

## Troubleshooting

### Out of Memory During Compilation

**Problem**: Compiler runs out of memory

**Solutions**:

1. Use low-memory build mode:

   ```bash
   ./publish_to_pypi.sh --build-only --low-memory
   ```

1. Add swap space:

   ```bash
   sudo fallocate -l 32G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

1. Limit parallel jobs:

   ```bash
   export CMAKE_BUILD_PARALLEL_LEVEL=2
   ```

1. Build on a cloud instance with more RAM (e.g., AWS c6a.8xlarge with 64GB)

### PyTorch Not Found

**Problem**: CMake cannot find PyTorch

**Solution**:

```bash
pip install torch>=2.0.0
python3 -c "import torch; print(torch.utils.cmake_prefix_path)"
```

### CUDA Build Fails

**Problem**: CUDA compilation errors

**Solutions**:

1. Ensure CUDA is properly installed:

   ```bash
   nvcc --version
   ```

1. Set CUDA_HOME:

   ```bash
   export CUDA_HOME=/usr/local/cuda
   export PATH=$CUDA_HOME/bin:$PATH
   export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
   ```

1. CPU-only build:

   ```bash
   ./publish_to_pypi.sh --build-only  # Omit --cuda flag
   ```

### Upload Fails

**Problem**: Twine upload fails

**Solutions**:

1. Check PyPI credentials in `~/.pypirc`
1. Verify package version is not already uploaded:
   ```bash
   # Update version in pyproject.toml before building
   ```
1. Check network connectivity
1. Use TestPyPI first to verify the process

## Memory Optimization Tips

The C++ compilation is very memory-intensive. Here are optimization strategies:

### 1. Unity Build (Enabled by Default in Low-Memory Mode)

CMake combines multiple source files into single compilation units:

```cmake
set(CMAKE_UNITY_BUILD ON)
set(CMAKE_UNITY_BUILD_BATCH_SIZE 2)
```

### 2. Optimization Level

Low-memory mode uses `-O0` (no optimization) to reduce memory:

```cmake
set(CMAKE_CXX_FLAGS "-O0 -g0 -fno-var-tracking")
```

### 3. Parallel Jobs

Limit concurrent compilation jobs:

```bash
export CMAKE_BUILD_PARALLEL_LEVEL=2
```

### 4. Swap Space

Add swap to handle temporary memory spikes:

```bash
sudo fallocate -l 32G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## CI/CD Integration

For automated builds in CI/CD:

```yaml
# .github/workflows/build-amms.yml
name: Build and Publish AMMS

on:
  push:
    tags:
      - 'amms-v*'

jobs:
  build:
    runs-on: ubuntu-latest
    # Use runner with sufficient memory
    container:
      image: ubuntu:22.04
      options: --memory=64g

    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: |
          apt-get update
          apt-get install -y build-essential cmake python3-dev

      - name: Build package
        run: |
          cd packages/sage-libs/src/sage/libs/amms
          ./publish_to_pypi.sh --build-only --low-memory

      - name: Upload to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: |
          cd packages/sage-libs/src/sage/libs/amms
          python3 -m twine upload dist/*
```

## Version Management

Update version in `pyproject.toml`:

```toml
[project]
name = "isage-amms"
version = "0.1.0"  # Update this before each release
```

Follow semantic versioning:

- Major: Breaking API changes
- Minor: New features, backward compatible
- Patch: Bug fixes

## Post-Release

After successful publication:

1. **Verify installation**:

   ```bash
   pip install isage-amms
   python3 -c "from sage.libs.amms import create; print('OK')"
   ```

1. **Update documentation**:

   - Update README with installation instructions
   - Add release notes to CHANGELOG.md

1. **Tag the release**:

   ```bash
   git tag amms-v0.1.0
   git push origin amms-v0.1.0
   ```

1. **Create GitHub release** with build artifacts and notes

## Support

For issues or questions:

- Check existing GitHub issues
- Create new issue with `amms` tag
- Email: shuhao_zhang@hust.edu.cn

## License

Apache License 2.0 - See LICENSE file for details
