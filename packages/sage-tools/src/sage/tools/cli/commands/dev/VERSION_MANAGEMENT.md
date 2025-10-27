# sage-dev Version Management

A comprehensive command-line tool for managing version.py files across all SAGE subpackages.

## Overview

The `sage-dev version` command provides a unified interface to manage version information across all
SAGE packages. It automatically discovers all `_version.py` files in the packages directory and
provides various operations to update and synchronize versions.

## Features

- **Auto-discovery**: Automatically finds all `_version.py` files in the packages directory
- **Version listing**: Display current versions of all packages in a table format
- **Version setting**: Set specific versions for one or all packages
- **Version bumping**: Increment versions by major, minor, patch, or build numbers
- **Version syncing**: Synchronize all package versions to match a reference package
- **Dry-run mode**: Preview changes before applying them
- **Rich output**: Beautiful formatted output with colors and tables

## Usage

### List all package versions

```bash
sage-dev version list
```

This command scans the packages directory and displays all package versions in a formatted table.

### Set a specific version

```bash
# Set version for all packages
sage-dev version set 0.2.0.0

# Set version for specific packages
sage-dev version set 0.2.0.0 --package sage-kernel --package sage-libs

# Preview changes without applying
sage-dev version set 0.2.0.0 --dry-run
```

### Bump version numbers

```bash
# Bump minor version for all packages (0.1.3.1 -> 0.2.0.0)
sage-dev version bump minor

# Bump patch version for specific package (0.1.3.1 -> 0.1.4.0)
sage-dev version bump patch --package sage-kernel

# Bump build version (0.1.3.1 -> 0.1.3.2)
sage-dev version bump build

# Preview changes
sage-dev version bump major --dry-run
```

Supported increment types:

- `major`: 0.1.3.1 → 1.0.0.0
- `minor`: 0.1.3.1 → 0.2.0.0
- `patch`: 0.1.3.1 → 0.1.4.0
- `build`: 0.1.3.1 → 0.1.3.2

### Sync all versions to a reference package

```bash
# Sync all packages to match the 'sage' package version
sage-dev version sync --source sage

# Sync to a different package
sage-dev version sync --source sage-kernel

# Preview sync changes
sage-dev version sync --source sage --dry-run
```

## Command Options

### Global Options

- `--root, -r`: Specify the project root directory (default: current directory)
- `--dry-run`: Preview mode - show what would be changed without making actual modifications

### Package Selection

- `--package, -p`: Specify which packages to update (can be used multiple times)
  ```bash
  sage-dev version set 1.0.0 --package sage-kernel --package sage-libs
  ```

## Examples

### Development Workflow

1. **Check current versions**:

   ```bash
   sage-dev version list
   ```

1. **Prepare for a minor release**:

   ```bash
   # Preview changes first
   sage-dev version bump minor --dry-run

   # Apply changes
   sage-dev version bump minor
   ```

1. **Fix a specific package**:

   ```bash
   sage-dev version bump patch --package sage-kernel
   ```

1. **Ensure version consistency**:

   ```bash
   sage-dev version sync --source sage
   ```

### Release Management

1. **Set release version**:

   ```bash
   sage-dev version set 1.0.0
   ```

1. **Verify all packages have the same version**:

   ```bash
   sage-dev version list
   ```

## Package Discovery

The tool automatically discovers packages by scanning the `packages/` directory and looking for
`_version.py` files in the following locations:

- `packages/{package-name}/src/sage/_version.py`
- `packages/{package-name}/src/sage/{module-name}/_version.py`

For example:

- `packages/sage/src/sage/_version.py`
- `packages/sage-kernel/src/sage/kernel/_version.py`
- `packages/sage-common/src/sage/common/_version.py`

## Version File Format

The tool expects `_version.py` files to contain:

```python
"""Version information for package."""

__version__ = "0.1.3.1"
__author__ = "IntelliStream Team"
__email__ = "shuhao_zhang@hust.edu.cn"
```

## Error Handling

- **File not found**: If no version files are found, the command will display a warning
- **Parse errors**: If a version file cannot be parsed, it will show an error message
- **Invalid package names**: If specified packages don't exist, available packages will be listed
- **Permission errors**: File permission issues will be reported clearly

## Integration

This tool is integrated into the main sage-dev CLI:

```bash
sage-dev version --help
```

It supports all the rich formatting and user experience standards of the sage-development toolkit.
