# Pull Request: Complete Package Build Configuration - BREAKING CHANGE

**Date**: 2024-08-15  
**Author**: SAGE Team  
**Summary**: PR 描述模板和规范说明


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
ModuleNotFoundError: No module named 'numpy'
ModuleNotFoundError: No module named '_sage_db'
```

**Root Cause Analysis:**
1. SAGE has 9 packages but only 6 were configured in build/test scripts
2. Missing packages: `sage-apps`, `sage-benchmark`, `sage-studio`
3. Dependency structure was unclear, causing circular dependencies
4. Installation script didn't enforce dependency order
5. External dependencies (numpy, etc.) not installed with `--no-deps`
6. C++ extensions (sage_db) couldn't be built due to chicken-and-egg problem

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
- `sage-tools/cli/commands/chat.py`: Uses **lazy import** for sage_db
- `sage/pyproject.toml`: Simplified to mainly depend on `sage-tools`

### 3. Fix Installation with `--no-deps` and External Dependencies

**Critical Fix in `tools/install/installation_table/core_installer.sh`:**

Added `--no-deps` flag to prevent PyPI lookups during local package installation:

```bash
# Step 1 & 2: Install local packages with --no-deps
pip install -e packages/sage-common --no-deps
pip install -e packages/sage-middleware --no-deps
# ... etc

# Step 3a: Install sage meta-package with --no-deps
pip install -e packages/sage[default] --no-deps

# Step 3b: Install external dependencies WITHOUT --no-deps
pip install packages/sage[default]  # Pip智能地只安装缺失的外部依赖
```

**Why this works:**
- `--no-deps` prevents pip from trying to download SAGE packages from PyPI
- We manually control local package installation order
- Final step without `--no-deps` lets pip install external dependencies
- Pip is smart: detects local packages already installed (editable mode), only installs missing external deps (numpy, pandas, typer, rich, etc.)

### 4. Enable CLI Startup Without C++ Extensions (Lazy Import)

**Problem:** Chicken-and-egg situation:
- Need `sage extensions install` command to build C++ extensions
- But `sage` CLI couldn't start without C++ extensions already built  
- `chat.py` had top-level import of `sage_db` which requires `_sage_db.so`

**Solution:** Implement lazy import pattern in `chat.py`:

```python
# Before: Top-level import (breaks CLI without C++)
from sage.middleware.components.sage_db.python.sage_db import SageDB

# After: Lazy import (CLI works without C++)
def _lazy_import_sage_db():
    global SageDB, SAGE_DB_AVAILABLE
    try:
        from sage.middleware.components.sage_db.python.sage_db import SageDB as _SageDB
        SageDB = _SageDB
        SAGE_DB_AVAILABLE = True
    except ImportError as e:
        SAGE_DB_AVAILABLE = False
        SAGE_DB_IMPORT_ERROR = e

# Import only when needed
def ensure_sage_db():
    _lazy_import_sage_db()
    if not SAGE_DB_AVAILABLE:
        show_error_and_exit()
```

**Benefits:**
- ✅ `sage` CLI starts without C++ extensions
- ✅ `sage extensions install all` works in fresh environments
- ✅ Matches local installation flow (install packages → build extensions)
- ✅ Clear error message when C++ extensions unavailable

## 📦 Files Modified

1. **`packages/sage-tools/pyproject.toml`**
   - Added dependencies on all 7 other SAGE packages
   - Comprehensive dev tool package

2. **`packages/sage-tools/src/sage/tools/cli/commands/chat.py`**
   - Implemented lazy import for sage_db
   - CLI can start without C++ extensions

3. **`packages/sage-middleware/pyproject.toml`**
   - Removed circular dependency on `sage-tools`

4. **`packages/sage/pyproject.toml`**
   - Simplified optional dependencies
   - Mainly depends on `sage-tools`

5. **`tools/install/installation_table/core_installer.sh`**
   - Step 1-2: Install local packages with `--no-deps`
   - Step 3a: Install sage meta-package with `--no-deps`
   - Step 3b: Install external dependencies without `--no-deps`

6. **`.github/workflows/dev-ci.yml`**
   - Added missing packages to test matrices

7. **`packages/sage-tools/src/sage/tools/cli/commands/pypi.py`**
   - Updated publish order with all 9 packages

8. **`packages/sage-tools/tests/pypi/validate_pip_install_complete.py`**
   - Validates all 9 packages

9. **Development documentation** (moved to `docs/dev-notes/`)
   - Organized root-level dev docs into proper structure

## ✅ Testing

- [x] Local installation successful
- [x] All 9 packages install in correct order
- [x] External dependencies (numpy, typer, rich) installed
- [x] `sage` CLI starts without C++ extensions
- [x] `sage extensions install all` works
- [ ] CI/CD passes (in progress)

## 🔄 Migration Guide

**For Existing Developers:**

If you encounter installation issues:

```bash
# 1. Clean existing installation
pip uninstall -y isage-common isage-kernel isage-middleware isage-libs \
                 isage-apps isage-benchmark isage-studio isage-tools isage

# 2. Re-run installation
./quickstart.sh
```

**Why reinstallation needed:**
- Dependency structure changed
- Installation order now critical
- New lazy import pattern for C++ extensions

## 📊 Impact Analysis

**What Changed:**
- 9 packages now built/tested (was 6, +50% coverage)
- Installation order strictly enforced
- Dependency graph clarified
- `sage-tools` role: minimal utility → comprehensive dev package
- CLI can start without C++ extensions (lazy import)

**What's Compatible:**
- API interfaces unchanged
- Import paths unchanged
- CLI commands unchanged
- Functionality unchanged

**What Breaks:**
- Existing dev environments need reinstallation
- Custom install scripts must use `--no-deps` pattern
- Dependency assumptions changed

## 🎯 Verification

Once CI passes:
1. All 9 packages install successfully
2. Deployment readiness check finds all packages
3. External dependencies present (numpy, typer, rich)
4. C++ extensions build via `sage extensions install`
5. Import tests pass

---

**Branch**: `fix/ci-missing-packages`  
**Target**: `main-dev`  
**Type**: BREAKING CHANGE (dependency restructure)  
**Priority**: High (blocks CI/CD)

**Commits:**
- `fa7e6595`: Initial fix - add missing packages
- `c9981e2e`: Remove isage-studio dependency
- `09b704f7`: Restructure dependencies - sage-tools as top-level
- `53f01125`: Add --no-deps to avoid PyPI lookups
- `bcd4086c`: Install external dependencies after local packages
- `aa4e4087`: Simplify external dependency installation
- `4ed4a57f`: Organize development documentation
- `d00c2a30`: Lazy import for sage_db to allow CLI startup without C++
