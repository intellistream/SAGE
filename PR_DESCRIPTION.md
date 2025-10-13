# Pull Request: Complete Package Build Configuration - BREAKING CHANGE

## ⚠️ BREAKING CHANGE

This PR adds 3 previously missing packages to the build/test/deployment pipeline. This is a **breaking change** because:
- The dependency structure has been restructured 
- `sage-tools` now depends on ALL other SAGE packages
- Installation order is critical and enforced with `--no-deps` flag
- Existing development environments may need reinstallation

## 🐛 Problem

CI/CD "deployment readiness check" failed with:
```
ERROR: Could not find a version that satisfies the requirement isage-studio>=0.1.0
```

**Root Cause Analysis:**
1. SAGE has 9 packages but only 6 were configured in build/test scripts
2. Missing packages: `sage-apps`, `sage-benchmark`, `sage-studio`
3. Dependency structure was unclear, causing circular dependencies
4. Installation script didn't enforce dependency order

## 🔧 Solution

### 1. Add Missing Packages to Build Pipeline

Updated all build/test/validation scripts:
- `packages/sage-tools/src/sage/tools/cli/commands/pypi.py` - publish order
- `packages/sage-tools/tests/pypi/validate_pip_install_complete.py` - validation
- `.github/workflows/dev-ci.yml` - CI test arrays

### 2. Restructure Dependency Hierarchy

**New Dependency Order:**
```
sage-common (base)
  ↓
sage-kernel (depends on common)
  ↓
sage-middleware, sage-libs, sage-apps, sage-benchmark, sage-studio
  ↓
sage-tools (depends on ALL above packages - dev tools)
  ↓
sage (meta-package, depends on tools for transitive dependencies)
```

**Key Changes:**
- `sage-tools` is now a **comprehensive dev tool package** depending on all others
- Removed circular dependency: `sage-middleware` no longer depends on `sage-tools`
- `sage-tools/cli/commands/chat.py`: Removed try-except imports (direct imports)
- `sage/pyproject.toml`: Simplified to mainly depend on `sage-tools`

### 3. Fix Installation Script with `--no-deps` 

**Critical Fix in `tools/install/installation_table/core_installer.sh`:**

Added `--no-deps` flag to all `pip install` commands to prevent PyPI lookups:

```bash
# Before (BROKEN):
pip install -e packages/sage-tools

# After (WORKS):
pip install -e packages/sage-tools --no-deps
```

**Why this is necessary:**
- When installing editable packages, pip checks `pyproject.toml` dependencies
- Without `--no-deps`, pip tries to download missing dependencies from PyPI
- With `--no-deps`, we manually control installation order
- Local packages are already installed in correct dependency sequence

**Enhanced 3-Step Installation Process:**
1. **Step 1/3**: Install base packages (`sage-common`, `sage-kernel`) with `--no-deps`
2. **Step 2/3**: Install mid-level packages (`middleware`, `libs`, `apps`, `benchmark`, `studio`, `tools`) with `--no-deps`
3. **Step 3/3**: Install meta-package in two phases:
   - **3a**: Install `sage` meta-package with `--no-deps` (avoid re-installing local packages)
   - **3b**: Install external dependencies (numpy, etc.) with `--no-build-isolation`

This two-phase approach in step 3 ensures:
- All local SAGE packages remain as editable installations
- External dependencies (like numpy, pandas, etc.) are properly installed
- No redundant re-installation of local packages

## 📦 Files Modified

1. **`packages/sage-tools/pyproject.toml`**
   - Added dependencies on all 7 other SAGE packages
   - Removed try-except pattern dependencies

2. **`packages/sage-tools/src/sage/tools/cli/commands/chat.py`**
   - Removed conditional imports
   - Direct import: `from sage.middleware import ChatMiddleware`

3. **`packages/sage-middleware/pyproject.toml`**
   - Removed circular dependency on `sage-tools`

4. **`packages/sage/pyproject.toml`**
   - Simplified optional dependencies
   - Mainly depends on `sage-tools` for transitive access

5. **`tools/install/installation_table/core_installer.sh`**
   - Added `--no-deps` flag to all pip install commands for local packages
   - Updated to enhanced 3-step installation process
   - Step 3 split into 3a (install meta-package) and 3b (install external deps)
   - Enforces dependency order while ensuring external dependencies are installed

6. **`.github/workflows/dev-ci.yml`**
   - Added missing packages to test matrices
   - Added validation for all 9 packages

7. **`packages/sage-tools/src/sage/tools/cli/commands/pypi.py`**
   - Updated publish order with all 9 packages

8. **`packages/sage-tools/tests/pypi/validate_pip_install_complete.py`**
   - Updated validation to check all 9 packages

## ✅ Testing

- [x] Local installation successful with new script
- [x] All 9 packages install in correct order
- [x] No PyPI lookup attempts during installation
- [x] Import tests pass for all packages
- [ ] CI/CD passes (in progress)

## 🔄 Migration Guide

**For Existing Developers:**

If you encounter installation issues after pulling:

```bash
# 1. Clean existing installation
pip uninstall -y isage-common isage-kernel isage-middleware isage-libs \
                 isage-apps isage-benchmark isage-studio isage-tools isage

# 2. Re-run installation
./quickstart.sh
```

**Why reinstallation is needed:**
- Dependency structure has changed
- Old installations may have incorrect dependency resolution
- New `--no-deps` strategy requires clean slate

## 📊 Impact Analysis

**What Changed:**
- 9 packages now built/tested instead of 6 (+50% coverage)
- Installation order strictly enforced
- Dependency graph clarified and documented
- `sage-tools` role changed from "minimal utility" to "comprehensive dev package"

**What's Compatible:**
- API interfaces unchanged
- Import paths unchanged
- CLI commands unchanged
- Functionality unchanged

**What Breaks:**
- Existing development environments need reinstallation
- Custom installation scripts must use `--no-deps` pattern
- Dependency assumptions (tools is now top-level, not base-level)

## 🎯 Verification

Once CI passes, verify:
1. All 9 packages install successfully
2. Deployment readiness check finds all packages
3. No PyPI lookup errors
4. Import tests pass for all packages

---

**Branch**: `fix/ci-missing-packages`  
**Target**: `main-dev`  
**Type**: BREAKING CHANGE (dependency restructure)  
**Priority**: High (blocks CI/CD)

**Commits:**
- `fa7e6595`: Initial fix - add missing packages to build/test scripts
- `c9981e2e`: Remove isage-studio from sage-tools core dependencies
- `09b704f7`: Restructure dependencies - sage-tools as top-level dev package
- `53f01125`: Fix installer with --no-deps to avoid PyPI lookups
- `7f48c2d9`: Fix sage dev quality to skip submodules
- `bcd4086c`: Install external dependencies after local packages
