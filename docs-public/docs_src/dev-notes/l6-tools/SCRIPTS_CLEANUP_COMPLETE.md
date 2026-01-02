# tools/scripts Directory Cleanup Complete

**Date**: 2025-11-21\
**Issue**: #[issue-number] - 根目录的scripts和tools尽量清理删除或者合并\
**Status**: ✅ Complete

## Summary

The `tools/scripts/` directory has been completely removed as part of the ongoing tools directory
cleanup initiative (following the 2025-10-27 cleanup documented in TOOLS_CLEANUP_SUMMARY.md).

## What Was Removed

### Directory: `tools/scripts/`

- **Content**: Single script `verify_dependency_separation.sh` (97 lines)
- **Purpose**: Validated SAGE package dependency separation rules in pyproject.toml files
- **Usage**: Not referenced in CI/CD, documentation, or other scripts (orphaned)

## Migration

The functionality has been migrated to the sage-dev CLI tools:

### New Implementation

- **File**: `packages/sage-tools/src/sage/tools/dev/tools/package_dependency_validator.py`
- **Class**: `PackageDependencyValidator`
- **Command**: `sage-dev quality dependencies`

### Validation Rules (Preserved)

1. Non-meta packages should NOT have `isage-*` dependencies in `[project.dependencies]`
   - Exception: `sage-tools` is allowed to depend on `isage-common` (treated as warning)
1. Packages should use `sage-deps` for internal SAGE dependencies (except L1 packages and
   meta-package)
1. The `sage` meta-package extras should reference packages using `[sage-deps]` notation

### Usage

```bash
# Old way (removed)
./tools/scripts/verify_dependency_separation.sh

# New way
sage-dev quality dependencies

# Or as part of full quality check
sage-dev quality check
```

## Current State of tools/ Directory

After this cleanup, the `tools/` directory structure is:

```
tools/
├── __init__.py                     # Python package marker
├── lib/                            # Shell function library
├── install/                        # Installation scripts
├── conda/                          # Conda management
├── git-tools/                      # Git integration tools
├── maintenance/                    # Maintenance scripts
├── cleanup/                        # Cleanup utilities
├── config/                         # Configuration files
├── dev.sh                          # Dev environment wrapper
├── fix-code-quality.sh            # Quality fix wrapper
├── mypy-wrapper.sh                # Type check wrapper
├── pre-commit-config.yaml         # Pre-commit hooks config
├── pytest.ini                      # Pytest configuration
├── ruff.toml                       # Ruff linter config
├── security-quick-reference.sh    # Security reference
├── sync_pytest_config.py          # Pytest config sync
└── verify-precommit.sh            # Pre-commit verification
```

**Note**: No `scripts/` subdirectory remains.

## Impact

### Positive

✅ Completes the tools cleanup initiative\
✅ Consolidates all Python development tools under `sage-dev` CLI\
✅ Better integration with existing quality check infrastructure\
✅ Consistent user experience (Rich UI, error handling)\
✅ Easier to maintain (Python vs Shell)

### No Breaking Changes

- Script was not used in CI/CD pipelines
- No external documentation referenced it
- Functionality preserved and enhanced in sage-dev

## Testing

The new validator was tested and correctly identifies the same issues:

```bash
$ sage-dev quality dependencies
```

**Results**:

- ⚠️ sage-tools: Contains isage-common dependency (WARNING - allowed)
- ❌ sage-llm-gateway: Missing sage-deps configuration (ERROR)

## Related Documentation

- `docs/dev-notes/l6-tools/TOOLS_CLEANUP_SUMMARY.md` - Previous cleanup (2025-10-27)
- `docs/dev-notes/l6-tools/TOOLS_MIGRATION_ANALYSIS.md` - Migration strategy
- `DEVELOPER.md` - Developer guide (updated with new command usage)

## Follow-up Tasks

- [ ] Update CI/CD to use `sage-dev quality dependencies` if needed
- [ ] Fix the identified issues in sage-llm-gateway (add sage-deps)
- [ ] Update developer onboarding documentation

______________________________________________________________________

**Completion Date**: 2025-11-21\
**Final Status**: ✅ tools/scripts/ directory removed, functionality migrated to sage-dev
