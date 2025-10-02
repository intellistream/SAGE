# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Development infrastructure improvements
  - Pre-commit hooks configuration for code quality
  - Developer helper script (`scripts/dev.sh`)
  - Architecture diagram in documentation
- Dev notes organization with template and quick start guide (#880)

### Changed
- Reorganized `docs/dev-notes/` directory structure with subdirectories for better organization

### Fixed
- Improved documentation clarity and accessibility

## [0.1.0] - 2025-10-02

### Added
- Initial release of SAGE framework
- Core API: LocalEnvironment and RemoteEnvironment
- RAG pipeline components (retriever, generator, refiner)
- Service architecture for background services
- Job management system with dispatcher
- Multi-agent framework support
- Memory service integration
- Vector database support (Milvus, Chroma)
- Reranker support (BGE, Cohere)
- CI/CD pipeline with GitHub Actions
- Comprehensive documentation and examples

### Security
- Environment variable configuration for API keys
- Secure credential management with `.env` files
- Configuration file security cleanup

---

## Changelog Guidelines

When updating this file:

### Categories
- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** in case of vulnerabilities

### Format
- Keep entries in reverse chronological order (newest first)
- Link to GitHub issues/PRs where applicable using `(#issue-number)`
- Group related changes together
- Be concise but descriptive
- Write in imperative mood ("Add feature" not "Added feature")

### Version Numbers
- Follow [Semantic Versioning](https://semver.org/):
  - MAJOR version for incompatible API changes
  - MINOR version for backwards-compatible functionality additions
  - PATCH version for backwards-compatible bug fixes

### Release Process
1. Move items from `[Unreleased]` to a new version section
2. Add release date in ISO format (YYYY-MM-DD)
3. Update version comparison links at bottom
4. Create git tag for the release

[Unreleased]: https://github.com/intellistream/SAGE/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/intellistream/SAGE/releases/tag/v0.1.0
