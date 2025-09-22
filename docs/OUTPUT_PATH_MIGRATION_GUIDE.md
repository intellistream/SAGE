# SAGE Output Path Migration Guide

## Overview

SAGE is consolidating all path management into a single module: `packages/sage-common/src/sage/common/config/output_paths.py`. This guide helps migrate from the deprecated modules.

## Migration Map

### From `sage_home.py` → `output_paths.py`

| Old Function | New Function | Notes |
|--------------|--------------|-------|
| `find_sage_project_root()` | `get_sage_paths().project_root` | Property access |
| `get_appropriate_sage_dir()` | `get_sage_paths().sage_dir` | Intelligent env detection |
| `ensure_sage_directories()` | `get_sage_paths()` | Auto-creates directories |

### From `paths.py` → `output_paths.py`

| Old Function | New Function | Notes |
|--------------|--------------|-------|
| `get_logs_dir()` | `get_logs_dir()` | Direct migration |
| `get_output_dir()` | `get_output_dir()` | Direct migration |
| `get_temp_dir()` | `get_temp_dir()` | Direct migration |

## Quick Migration Examples

### Example 1: Basic Path Access

**Before:**
```python
from sage.tools.dev.utils.sage_home import get_appropriate_sage_dir
from sage.common.config.paths import get_logs_dir

sage_dir = get_appropriate_sage_dir()
logs_dir = get_logs_dir()
```

**After:**
```python
from sage.common.config.output_paths import get_sage_paths

paths = get_sage_paths()
sage_dir = paths.sage_dir
logs_dir = paths.logs_dir
```

### Example 2: Environment Setup

**Before:**
```python
from sage.tools.dev.utils.sage_home import ensure_sage_directories
from sage.common.config.paths import setup_environment_variables

ensure_sage_directories()
setup_environment_variables()
```

**After:**
```python
from sage.common.config.output_paths import initialize_sage_paths

paths = initialize_sage_paths()  # Creates dirs and sets env vars
```

### Example 3: Ray Integration

**Before:**
```python
import os
import ray
from sage.tools.dev.utils.sage_home import get_appropriate_sage_dir

temp_dir = get_appropriate_sage_dir() / "temp" / "ray"
os.environ["RAY_TMPDIR"] = str(temp_dir)
ray.init()
```

**After:**
```python
import ray
from sage.common.config.output_paths import get_sage_paths

paths = get_sage_paths()
ray.init(_temp_dir=str(paths.get_ray_temp_dir()))
```

## New Features in `output_paths.py`

### 1. Intelligent Environment Detection

Automatically detects whether running in:
- Development environment (uses `project_root/.sage/`)
- Pip-installed environment (uses `~/.sage/`)

### 2. Unified Ray Integration

```python
paths = get_sage_paths()
ray_temp = paths.get_ray_temp_dir()  # Always appropriate location
```

### 3. Environment Variable Management

```python
paths = get_sage_paths()
env_vars = paths.setup_environment_variables()
# Sets: SAGE_OUTPUT_DIR, RAY_TMPDIR, etc.
```

### 4. All Directory Types

```python
paths = get_sage_paths()
# All directories available as properties:
paths.sage_dir       # Main .sage directory
paths.logs_dir       # Logs
paths.output_dir     # Outputs
paths.temp_dir       # Temporary files
paths.cache_dir      # Cache
paths.reports_dir    # Reports
paths.coverage_dir   # Coverage reports
paths.benchmarks_dir # Benchmarks
```

## Convenience Functions

For backward compatibility, convenience functions are available:

```python
from sage.common.config.output_paths import (
    get_logs_dir,
    get_output_dir,
    get_temp_dir,
    get_cache_dir,
    setup_sage_environment,
    initialize_sage_paths
)
```

## Deprecation Warnings

The old modules will show deprecation warnings:

```
DeprecationWarning: find_sage_project_root is deprecated. 
Use get_sage_paths().project_root instead.
```

To suppress during migration:
```python
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="sage.tools.dev.utils.sage_home")
```

## File-by-File Migration Checklist

### 1. Update Imports
- [ ] Replace `from sage.tools.dev.utils.sage_home import ...`
- [ ] Replace `from sage.common.config.paths import ...`
- [ ] Add `from sage.common.config.output_paths import get_sage_paths`

### 2. Update Function Calls
- [ ] Replace direct function calls with property access
- [ ] Use `initialize_sage_paths()` for setup
- [ ] Update Ray initialization

### 3. Test
- [ ] Run existing tests
- [ ] Verify paths are correct in both dev and pip environments
- [ ] Check Ray temp directory location

## Rollback Plan

If issues arise, the old modules remain functional with deprecation warnings. Simply revert imports:

```python
# Temporary rollback
from sage.tools.dev.utils.sage_home import get_appropriate_sage_dir  # Works but deprecated
```

## Benefits After Migration

1. **Single Source of Truth**: All path logic in one place
2. **Environment Aware**: Automatic dev/pip detection
3. **Ray Integration**: Proper temp directory management
4. **Better Testing**: Consistent paths across test environments
5. **Maintenance**: Easier to update and debug path issues

## Need Help?

- Check existing usages in the codebase for examples
- Run tests to verify migration
- The old functions still work (with warnings) during transition