# Changelog

All notable changes to the SAGE Studio package will be documented in this file.

## [0.1.0] - 2025-10-10

### Added
- 🎉 Initial release as an independent package
- Separated from `sage-tools` package for better modularity
- Complete Studio functionality including:
  - Frontend (Angular-based UI)
  - Backend API (FastAPI)
  - StudioManager for service management
  - CLI integration through `sage-tools`

### Changed
- **Package Structure**: Moved from `sage.tools.studio` to `sage.studio`
- **Import Path**: Changed from `from sage.tools.studio.studio_manager` to `from sage.studio.studio_manager`
- **Installation**: Now installed as part of SAGE's core dependencies

### Technical Details
- Package name: `isage-studio`
- Version: 0.1.0
- Python requirement: >=3.10
- Key dependencies: FastAPI, Uvicorn, Starlette, Pydantic

### Migration Notes
- CLI commands remain unchanged: `sage studio start`, `sage studio stop`, etc.
- Existing users should upgrade with: `pip install --upgrade isage isage-studio isage-tools`
- Import paths need to be updated in custom code (see README for details)

### Documentation
- Comprehensive README with installation, usage, and development guides
- Test suite using pytest
- Integration with quickstart.sh installation script

---

For more details, see [README.md](README.md)
