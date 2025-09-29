# SAGE Maintenance Tools

This directory contains various maintenance and utility scripts for the SAGE project.

## Scripts

### Submodule Management

- **`submodule_manager.sh`** - General submodule management utilities
- **`submodule_sync.sh`** - Synchronize submodules across different environments
- **`resolve_submodule_conflict.sh`** - Automatically resolve submodule conflicts during PR merges
- **`SUBMODULE_CONFLICT_RESOLUTION.md`** - Comprehensive guide for resolving submodule conflicts

### System Maintenance

- **`quick_cleanup.sh`** - Clean up temporary files and build artifacts
- **`sage-jobmanager.sh`** - Job management utilities for SAGE services

## Usage

### Resolving Submodule Conflicts

When encountering submodule conflicts during PR merges (especially with `sage_db`):

```bash
# Quick resolution using our script
./tools/maintenance/resolve_submodule_conflict.sh

# Or manual resolution
git checkout --ours packages/sage-middleware/src/sage/middleware/components/sage_db
git submodule update --init --recursive packages/sage-middleware/src/sage/middleware/components/sage_db
git add packages/sage-middleware/src/sage/middleware/components/sage_db
git commit
```

For detailed instructions, see `SUBMODULE_CONFLICT_RESOLUTION.md`.

### General Maintenance

```bash
# Clean up build artifacts
./tools/maintenance/quick_cleanup.sh

# Sync submodules
./tools/maintenance/submodule_sync.sh
```

## Best Practices

1. Always run maintenance scripts from the project root directory
2. Check script permissions before execution: `chmod +x script_name.sh`
3. Review the documentation before using submodule-related tools
4. Test scripts in a development environment before using in production

## Contributing

When adding new maintenance tools:

1. Place them in this directory
2. Update this README with usage instructions
3. Ensure scripts have proper error handling
4. Add appropriate documentation