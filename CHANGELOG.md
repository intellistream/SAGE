# CHANGELOG

All notable changes to this repository are documented in this file.

## PyPI Verified Releases (`isage`)

Source: `https://pypi.org/pypi/isage/json` (checked on 2026-02-14, UTC).

- `0.2.4.13` — 2026-02-13T03:42:08Z
- `0.2.4.12` — 2026-02-12T14:29:53Z
- `0.2.3.3` — 2026-01-13T17:42:33Z
- `0.2.3.2` — 2026-01-07T17:00:03Z
- `0.2.3.1` — 2026-01-05T16:47:49Z

## [Unreleased]

### Changed
- Updated documentation references from `dev-notes` paths to stable repository-level references.
- Consolidated markdown retention policy to aggressively trim non-critical docs while preserving root entry docs (`README.md`, `CONTRIBUTING.md`, `DEVELOPER.md`) and Copilot/agent instruction metadata.
- Preserved critical operational constraints in changelog: `sageFlownet` replaces Ray for runtime direction, and new work should avoid adding Ray-oriented dependencies.
- Preserved critical engineering policy in changelog: dependency changes must be declared in `pyproject.toml` (no ad-hoc manual install workflow as a source of truth).
- Consolidated guidance from removed governance/docs markdown into changelog-level policy summaries:
	- Cross-package governance baselines remain: layer-boundary compliance, fail-fast behavior, and quality/test gate expectations.
	- Runtime API layering intent remains: facade APIs for default users and environment APIs for advanced control, with contract-level semantic consistency.
	- Installation/operations note remains: long-install progress and install optimization guidance are now treated as implementation details rather than standalone markdown docs.
- Markdown inventory in tracked files was reduced to a minimal set (primarily `README*.md` + `CHANGELOG*.md` + root contribution docs + agent/copilot instruction docs).

### Removed
- Removed selected Copilot-related markdown documents and obsolete dev-notes references from documentation.
- Removed selected markdown in package docs/examples and tools docs to reduce documentation footprint.
- Removed markdown-heavy governance and template docs across packages (CLI/Common/Kernel/Libs/Middleware/Platform/Tools/meta-package), plus issue/PR markdown templates and selected install-fix notes.
