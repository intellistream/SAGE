# AMMS Build and Publish Checklist

## Pre-Build Checklist

### Environment Setup

- [ ] Machine has 64GB+ RAM (or 32GB+ with swap)
- [ ] Linux OS (Ubuntu 22.04+ recommended)
- [ ] Python 3.8-3.12 installed
- [ ] Git installed

### Software Dependencies

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y build-essential cmake pkg-config \
    libopenblas-dev liblapack-dev g++-11 gcc-11 python3-dev

# Install Python dependencies
pip install --upgrade pip setuptools wheel build twine
pip install torch>=2.0.0 pybind11>=2.10.0
```

- [ ] Compiler installed (GCC 11+)
- [ ] CMake installed (3.14+)
- [ ] Python dependencies installed
- [ ] PyTorch installed

### PyPI Credentials (for publishing)

- [ ] PyPI account created
- [ ] TestPyPI account created
- [ ] API tokens generated
- [ ] `~/.pypirc` configured

## Build Process

### 1. Get the Code

```bash
# Clone the repository
git clone https://github.com/intellistream/SAGE.git
cd SAGE
git checkout feature/intent-refactor  # Or main branch

# Navigate to amms directory
cd packages/sage-libs/src/sage/libs/amms
```

- [ ] Code cloned
- [ ] In correct directory

### 2. Clean Previous Builds

```bash
./clean.sh
```

- [ ] Cleaned

### 3. Build the Package

**Option A: Quick Build (Recommended)**

```bash
./quick_build.sh
```

**Option B: Build with Options**

```bash
# Dry-run (no upload)
./publish_to_pypi.sh

# Build only
./publish_to_pypi.sh --build-only

# Low-memory mode
./publish_to_pypi.sh --build-only --low-memory

# CUDA support
./publish_to_pypi.sh --build-only --cuda
```

- [ ] Build started
- [ ] Build completed successfully
- [ ] Packages found in `dist/`

### 4. Verify Build

```bash
# List built packages
ls -lh dist/

# Install locally
pip install dist/isage_amms-*.whl

# Test import
python3 -c "from sage.libs.amms import create, registered; print('OK')"
```

- [ ] Packages exist
- [ ] Local installation successful
- [ ] Import test passed

## Testing (Optional but Recommended)

### Test on TestPyPI

```bash
# Upload to TestPyPI
./publish_to_pypi.sh --test-pypi --no-dry-run

# Install from TestPyPI (in a clean environment)
pip install -i https://test.pypi.org/simple/ isage-amms

# Test
python3 -c "from sage.libs.amms import create; print('OK')"
```

- [ ] Uploaded to TestPyPI
- [ ] Installed from TestPyPI
- [ ] Import test passed

## Publishing to PyPI

### Pre-Publish Checks

- [ ] Version number updated in `pyproject.toml`
- [ ] CHANGELOG updated with release notes
- [ ] All tests passed
- [ ] Documentation updated
- [ ] PyPI credentials configured

### Publish

```bash
# Upload to PyPI
./publish_to_pypi.sh --no-dry-run
```

- [ ] Uploaded to PyPI
- [ ] No errors during upload

### Post-Publish Verification

```bash
# Wait a few minutes for PyPI to process

# Install from PyPI
pip install isage-amms

# Verify version
python3 -c "import sage.libs.amms; print(sage.libs.amms.__version__)"

# Test functionality
python3 -c "from sage.libs.amms import create, registered; print(registered())"
```

- [ ] Package available on PyPI
- [ ] Installation successful
- [ ] Version correct
- [ ] Functionality verified

## Post-Release Tasks

### Git Tagging

```bash
cd /path/to/SAGE
git tag amms-v0.1.0  # Update version
git push origin amms-v0.1.0
```

- [ ] Git tag created
- [ ] Tag pushed to remote

### GitHub Release

1. Go to https://github.com/intellistream/SAGE/releases
1. Click "Draft a new release"
1. Select the tag `amms-v0.1.0`
1. Add release notes
1. Attach build artifacts (optional)
1. Publish release

- [ ] GitHub release created

### Documentation Updates

- [ ] Update main README with new version
- [ ] Update installation instructions
- [ ] Announce release (if applicable)

## Troubleshooting

### Build Issues

| Problem           | Solution                                          |
| ----------------- | ------------------------------------------------- |
| Out of memory     | Use `--low-memory` flag or add swap               |
| PyTorch not found | `pip install torch>=2.0.0`                        |
| CUDA build fails  | Check CUDA installation or build without `--cuda` |
| CMake errors      | Check CMake version (3.14+)                       |

### Upload Issues

| Problem        | Solution                           |
| -------------- | ---------------------------------- |
| Upload fails   | Check `~/.pypirc` credentials      |
| Version exists | Update version in `pyproject.toml` |
| Network error  | Check internet connection          |

## Time Estimates

| Task                    | Time (with 64GB RAM) | Time (with low-memory) |
| ----------------------- | -------------------- | ---------------------- |
| Dependency installation | 5-10 minutes         | 5-10 minutes           |
| Clean build             | 20-40 minutes        | 60-90 minutes          |
| Local testing           | 5 minutes            | 5 minutes              |
| Upload to PyPI          | 2-5 minutes          | 2-5 minutes            |
| **Total**               | **30-60 minutes**    | **70-110 minutes**     |

## Quick Command Reference

```bash
# Clean
./clean.sh

# Build only
./quick_build.sh

# Build and test on TestPyPI
./publish_to_pypi.sh --test-pypi --no-dry-run

# Build and publish to PyPI
./publish_to_pypi.sh --no-dry-run

# Build with low memory
./publish_to_pypi.sh --build-only --low-memory

# Build with CUDA
./publish_to_pypi.sh --build-only --cuda
```

## Support

- Documentation: See [BUILD_PUBLISH.md](BUILD_PUBLISH.md)
- Issues: https://github.com/intellistream/SAGE/issues
- Email: shuhao_zhang@hust.edu.cn
