# Merge Strategy: main-dev → main

## Overview

This PR merges `main-dev` into `main`, bringing all the independent repository migrations and recent improvements to the main branch.

## Branch Status

### main branch (commit 2c5e5fbd)
- **Still contains**: `.gitmodules` with 3 submodules
  - `docs-public` → SAGE-Pub repository
  - `packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem` → NeuroMem
  - `packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner` → sageRefiner
- **Status**: Outdated, needs submodule-to-PyPI migration

### main-dev branch (commit 1d973b6e)
- **Removed**: `.gitmodules` file (no more submodules)
- **Uses**: Independent PyPI packages
  - `isage-neuromem` for NeuroMem functionality
  - `isage-refiner` for refiner functionality
  - `isage-vdb` for SageVDB
  - etc.
- **Status**: Up-to-date with all migrations completed

## Commits to be Merged

This merge brings **2 new commits** from main-dev to main:

1. **6436def4** - `feat(kernel): improve RayTask.put_packet with retry mechanism`
   - Kernel improvements for distributed execution
   - Note: This is a grafted commit that includes all submodule removal changes

2. **1d973b6e** - `fix(tests): resolve all pytest collection errors (#1410)`
   - Fixes test collection issues
   - Ensures CI/CD stability

## Submodule Removal Details

The grafted commit 6436def4 includes the removal of:
- `.gitmodules` file
- `docs-public/` directory (submodule → independent SAGE-Pub repo)
- `packages/sage-middleware/src/sage/middleware/components/sage_mem/neuromem/` (submodule → `isage-neuromem` PyPI package)
- `packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/` (submodule → `isage-refiner` PyPI package)

## Expected Changes After Merge

When main-dev is merged into main:

### Files to be Deleted
- `.gitmodules`
- All submodule directories (replaced by PyPI packages)

### Dependencies Updated
- Added: `isage-neuromem>=0.2.1.1`
- Added: `isage-refiner>=0.1.0`
- Added: `isage-vdb>=0.1.0`
- Removed: Git submodule references

### No Breaking Changes
- All functionality preserved through PyPI packages
- Installation process simplified (no submodule initialization needed)
- CI/CD updated to use pip packages

## Merge Process

### Option 1: GitHub PR (Recommended)
1. Change PR base branch from `main-dev` to `main`
2. GitHub will automatically calculate the diff
3. Review and approve
4. Merge using "Merge commit" or "Squash and merge"

### Option 2: Manual Merge (if needed)
```bash
git checkout main
git merge main-dev
# Git will handle submodule deletion automatically
git push origin main
```

## Post-Merge Actions

After merging to main:
1. Update any CI/CD workflows that reference `main` branch
2. Notify team members to:
   - Run `git submodule deinit -f .` to clean up submodule cache (if they had old checkouts)
   - Run `pip install -e packages/sage-middleware -e packages/sage-libs` to get new PyPI dependencies
3. Archive or deprecate any submodule-specific documentation

## Rollback Plan (if needed)

If issues arise after merge:
```bash
git revert <merge-commit-sha>
# or
git reset --hard 2c5e5fbd
git push origin main --force-with-lease
```

## Benefits of This Merge

1. **Simplified dependency management**: No more submodule initialization/updates
2. **Faster CI/CD**: Pip packages install faster than submodule cloning
3. **Better version control**: PyPI semantic versioning for independent components
4. **Cleaner repository**: No nested git repositories
5. **Easier for contributors**: Standard `pip install` workflow

## Related Documentation

- Submodule migration policy: (was in docs-public, now in SAGE-Pub repository)
- PyPI package documentation: Each package has its own README in the independent repositories
- Installation guide: Updated in main README.md after merge

---

**Note**: This document will be removed after successful merge completion.
