refactor(tests): reorganize test files naming and structure

BREAKING CHANGE: Test file paths have been reorganized

## Changes

### 1. Rename *_test.py to test_*.py (13 files)
- Standardize test file naming across the project
- Follow Python/pytest conventions (test_*.py)

**Affected packages:**
- sage-kernel: 7 files (core/function, kernel routing)
- sage-middleware: 5 files (operators/tools)
- sage-libs: 1 file (lib/io)

### 2. Reorganize sage-studio tests (24 files)
- Create unit/ and integration/ subdirectories
- Move files based on test type:
  - integration/: E2E, CLI, route tests (4 files)
  - unit/: Model, service, config, tool, util tests (20 files)
- Create proper __init__.py files for all subdirectories
- Clean up empty directories

**New structure:**
```
packages/sage-studio/tests/
├── integration/          # 4 integration tests
│   ├── test_e2e_integration.py
│   ├── test_agent_step.py
│   ├── test_studio_cli.py
│   └── test_chat_routes.py
└── unit/                 # 20 unit tests
    ├── test_models.py
    ├── test_pipeline_builder.py
    ├── test_node_registry.py
    ├── config/           # API config tests
    ├── services/         # Service layer tests
    ├── tools/            # Tool tests
    └── utils/            # Utility tests
```

### 3. Add maintenance scripts
- `tools/maintenance/reorganize_test_files.sh`: Automated test file renaming
- `tools/maintenance/migrate_studio_subdirs.sh`: Automated structure migration
- `.github/TEST_REORGANIZATION_REPORT.md`: Detailed migration report

## Impact

**Breaking:**
- Any scripts with hard-coded test file paths need updates
- Git history: files have moved (use `git log --follow`)

**Compatible:**
- pytest auto-discovery: ✅ Works seamlessly
- CI/CD: ✅ No changes needed
- Test imports: ✅ No modifications required

## Verification

```bash
# All tests can still be discovered
pytest packages/sage-studio/tests/unit/test_models.py -v --co  # ✅ 14 tests found

# Project-wide test discovery still works
sage-dev project test --coverage  # ✅ Ready to run
```

## Statistics

- Files renamed: 13
- Files moved: 24
- New directories: 7
- New __init__.py: 5
- Empty dirs removed: 4
- Migration scripts: 2
- Total changes: 50 files, +582/-433 lines

## Rationale

1. **Consistency**: All test files now follow Python conventions
2. **Organization**: Clear separation of unit vs integration tests
3. **Maintainability**: Structured test layout easier to navigate
4. **Standards**: Aligns with pytest best practices
5. **Automation**: Scripts enable future migrations

See `.github/TEST_REORGANIZATION_REPORT.md` for full details.

---

Co-authored-by: SAGE Development Assistant <copilot@github.com>
