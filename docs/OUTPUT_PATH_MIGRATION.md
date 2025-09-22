# SAGE Output Path Migration Guide

## Overview

SAGE has been updated to use a unified output directory system. All intermediate results, logs, outputs, and temporary files now use the `.sage` directory for consistent organization.

## Changes Made

### 1. Centralized Output Configuration

- Created `sage.common.config.output_paths` module for unified path management
- All output paths now default to `.sage` subdirectories:
  - Logs: `.sage/logs/`
  - Output files: `.sage/output/`
  - Temp files: `.sage/temp/`
  - Cache: `.sage/cache/`
  - Reports: `.sage/reports/`
  - Coverage: `.sage/coverage/`
  - Test logs: `.sage/test_logs/`
  - Experiments: `.sage/experiments/`
  - Issues tooling: `.sage/issues/`

### 2. Updated Components

#### FileSink and MemWriteSink
- Now use `.sage/output/` for relative paths instead of `./output/`
- Absolute paths continue to work as before

#### Issues Tooling
- Workspace: `.sage/issues/workspace/`
- Output: `.sage/issues/output/`
- Metadata: `.sage/issues/metadata/`

#### Experiments
- Results now saved to `.sage/experiments/`
- Evaluation results use `.sage/experiments/`

#### Job Manager
- Uses unified `.sage/logs/jobmanager/` directory
- Session-based subdirectories maintained

#### Logging System
- Added `get_default_log_base_folder()` helper function
- Examples updated to use `.sage/logs/` by default

### 3. Migration Script

A migration script has been created at `tools/migrate_outputs.py` to help move existing files:

```bash
# Dry run to see what would be migrated
python tools/migrate_outputs.py --dry-run

# Perform the migration
python tools/migrate_outputs.py

# Force migration (overwrite existing files)
python tools/migrate_outputs.py --force
```

## Usage

### For Application Developers

Use the new configuration system for consistent paths:

```python
from sage.common.config.output_paths import get_output_file, get_log_file

# Get output file path
output_path = get_output_file("my_results.json")

# Get log file path  
log_path = get_log_file("app.log", "myapp")

# Get output file in subdirectory
report_path = get_output_file("report.pdf", "reports")
```

### For Configuration Files

Relative paths in config files will automatically use `.sage/output/`:

```yaml
sink:
  platform: "local"
  file_path: "output.txt"  # Will be saved to .sage/output/output.txt
```

### For Logging

Use the helper function for consistent log directories:

```python
from sage.common.utils.logging.custom_logger import CustomLogger, get_default_log_base_folder

logger = CustomLogger([
    ("console", "INFO"),
    ("app.log", "DEBUG"),
    ("error.log", "ERROR"),
], name="MyApp", log_base_folder=get_default_log_base_folder())
```

## Backward Compatibility

- Absolute paths continue to work unchanged
- The migration script creates symlinks for backward compatibility
- Existing configurations using relative paths will automatically use the new directories

## Benefits

1. **Centralized Management**: All outputs in one location
2. **Consistent Organization**: Standard subdirectory structure
3. **Easy Cleanup**: Single directory to manage
4. **Symbolic Link Support**: `.sage` links to `~/.sage` for global access
5. **Cross-Component Consistency**: All SAGE components use the same system

## Troubleshooting

### Missing Output Files

If you can't find output files after the update:

1. Check `.sage/output/` for general outputs
2. Check `.sage/logs/` for log files  
3. Run the migration script to move old files
4. Check if any absolute paths in your config bypass the new system

### Permission Issues

Ensure the `.sage` directory and its parent are writable:

```bash
ls -la ~/.sage
ls -la .sage
```

### Configuration Issues

If you get import errors, ensure the sage-common package is properly installed:

```bash
pip install -e packages/sage-common/
```