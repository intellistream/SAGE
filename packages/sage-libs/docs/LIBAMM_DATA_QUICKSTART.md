# SAGE LibAMM Data Setup - Quick Start Guide

## 🚀 For New Users (First Time Setup)

```bash
# 1. Clone SAGE
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 2. Initialize submodules (includes LibAMM and sageData)
git submodule update --init --recursive

# 3. Pull LFS data files (only when needed)
cd packages/sage-benchmark/src/sage/data
git lfs pull  # Downloads ~387MB of data

# 4. Setup LibAMM data links
cd ../../../../sage-libs/src/sage/libs/libamm
bash tools/setup_data.sh

# Done! ✅
```

## 🔄 For Existing Users (After Update)

```bash
cd /path/to/SAGE

# 1. Update submodules
git submodule update --remote --merge

# 2. Pull new LFS files if needed
cd packages/sage-benchmark/src/sage/data
git lfs pull

# 3. Re-run setup
cd ../../../../sage-libs/src/sage/libs/libamm
bash tools/setup_data.sh
```

## 📦 What Gets Downloaded?

With `git lfs pull`:

- **Models** (~33MB): PyTorch models for QCD downstream tasks
- **Test Data** (~18MB): VQ test codebooks
- **Datasets** (~336MB): Benchmark datasets (MNIST, SIFT, QCD, etc.)

**Total:** ~387MB (vs 644MB before cleanup)

## ⚡ Skip Data Download (CI/Fast Clone)

```bash
# Clone without LFS data
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/intellistream/SAGE.git
GIT_LFS_SKIP_SMUDGE=1 git submodule update --init --recursive

# Download specific datasets only when needed
cd packages/sage-benchmark/src/sage/data
git lfs pull --include="libamm-benchmark/datasets/MNIST/*"
```

## 🔧 Troubleshooting

### "Data not found" errors

```bash
# Check sageData exists
ls packages/sage-benchmark/src/sage/data/libamm-benchmark/

# If empty, pull LFS files
cd packages/sage-benchmark/src/sage/data
git lfs pull

# Re-create symlinks
cd ../../../../sage-libs/src/sage/libs/libamm
bash tools/setup_data.sh
```

### LFS files are pointers (133 bytes)

```bash
cd packages/sage-benchmark/src/sage/data
git lfs pull  # Download actual files
```

### Symlinks broken

```bash
cd packages/sage-libs/src/sage/libs/libamm
rm -rf benchmark/models benchmark/datasets test/torchscripts/VQ/data
bash tools/setup_data.sh
```

## 🏗️ Architecture Overview

```
Before (❌ Bad):
  LibAMM Git repo: 644MB (with data in history)
  Clone time: ~2 minutes

After (✅ Good):
  LibAMM Git repo: 10MB (code only)
  sageData Git repo: ~2MB (LFS pointers)
  LFS storage: 387MB (download on-demand)
  Clone time: ~10 seconds (without data)
             ~30 seconds (with data)
```

## 📚 More Info

- Full documentation: `packages/sage-libs/src/sage/libs/libamm/tools/DATA_MANAGEMENT.md`
- Python API: `tools/data_manager.py`
- Setup script: `tools/setup_data.sh`

## 💡 Best Practices

1. **Development**: Pull all LFS data locally
1. **CI/CD**: Skip LFS or pull only needed files
1. **Production**: Mount data from external storage, set `SAGE_DATA_ROOT`
1. **Sharing**: Share LFS data separately, not in Git clones
