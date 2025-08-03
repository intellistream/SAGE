# Root Directory Cleanup Plan

## Overview
After successfully implementing the monorepo architecture with independent packages, we need to clean up legacy files from the root directory that are no longer needed or need to be updated for the new structure.

## Files to Archive/Remove

### 1. Legacy Installation Scripts
- `install.py` - 302 lines, single package installer → **Archive**
- `build_modern_wheel.sh` - 272 lines, old wheel builder → **Archive** 
- `test_install_sandbox.sh` - 367 lines, legacy testing → **Archive**

**Reason**: These are replaced by `scripts/sage-package-manager.py` which handles all packages.

### 2. Outdated Configuration Files
- `MANIFEST.in` - Old package manifest → **Remove**
- `pyproject.toml` - Root level package config → **Remove**
- `pyproject.toml.backup` - Backup of old config → **Remove**

**Reason**: Each package now has its own pyproject.toml. Root level packaging is no longer used.

### 3. Legacy Test Files
- `cythonized_files.txt` - Old build artifact list → **Remove**
- `test_namespace_imports.py` - Ad-hoc test file → **Remove**

## Files to Update

### 1. One-Click Setup Script
- `one_click_setup_and_test.py` - Update to use new package manager

### 2. Test Configuration
- `pytest.ini` - Update test paths for package structure

## Files to Keep
- `README.md` - Main project documentation
- `LICENSE` - Legal requirement
- `CODE_MIGRATION_PLAN.md` - Documentation
- `INSTALL_GUIDE.md` - User documentation
- `.gitignore`, `.actrc`, `.env.test` - Development configuration

## New Root Structure Goal
```
/
├── README.md                    # Main project docs
├── LICENSE                      # Legal
├── INSTALL_GUIDE.md            # User installation guide
├── CODE_MIGRATION_PLAN.md      # Development docs
├── pytest.ini                  # Test configuration (updated)
├── one_click_setup_and_test.py # Updated for monorepo
├── .gitignore, .actrc, .env.test # Dev config
├── packages/                    # All Python packages
├── scripts/                     # Monorepo tools
├── config/                      # Configuration files
├── app/                         # Example applications
├── data/                        # Test data
├── docs/                        # Documentation
└── archive/                     # Legacy files moved here
```

## Implementation Steps
1. Create archive/legacy-automation/ directory
2. Move legacy scripts to archive
3. Remove outdated configuration files
4. Update one_click_setup_and_test.py
5. Update pytest.ini for package structure
6. Test that all functionality still works
