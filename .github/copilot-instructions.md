# SAGE Copilot Instructions

## Scope and architecture
- SAGE is the core framework repo; examples/benchmarks/studio/docs are split into independent repos.
- Keep the 5-layer dependency rule: L5 → L4 → L3 → L2 → L1 only (no upward imports).
- Runtime direction is Flownet-first: use `isage-flownet` patterns, do not introduce new `ray` imports/dependencies.
- `sage-libs` is interface/algorithm layer; runtime/service-bound code (VDB, memory backends, networked operators) belongs in `sage-middleware`.

## Polyrepo architecture (critical)
- SAGE is a **polyrepo**: each sub-package (`isage-common`, `isage-platform`, `isage-kernel`, `isage-libs`, `isage-middleware`, `isage-cli`, etc.) lives in its own GitHub repository.
- This repo (`intellistream/SAGE`) only contains the meta-package at `packages/sage/` — it is **the only local package** installed with `-e`.
- All sub-package dependencies are declared with PyPI version pins in `packages/sage/pyproject.toml`. A sub-package change is only visible here **after it is published to PyPI and the version is bumped** in that file.
- Do not add local editable installs of sub-packages to `quickstart.sh` or `core_installer.sh`. The install flow is simply: `pip install -e packages/sage` (standard) or `pip install -e packages/sage[dev]` (dev).

## Critical repo conventions
- No manual dependency drift: update sub-package version pins in `packages/sage/pyproject.toml` only after the sub-package is published to PyPI.
- NEVER create any new Python virtual environment (`venv`/`.venv`) in this repo under any circumstance.
- Do not use an active Python venv for SAGE install/run/test flows; if `VIRTUAL_ENV` is set, exit and switch to Conda or a pre-configured non-venv Python environment.
- Never suggest or invoke `--auto-venv`, `python -m venv`, or `virtualenv` in SAGE workflows.
- If a task, script, or prompt requests creating a venv, do not do it; use an existing non-venv Python environment instead.
- Fail-fast policy: avoid silent fallback patterns that hide missing config/import/runtime errors.
- Do not add compatibility shims/re-export layers during migrations; update call sites directly.
- Centralize service ports via `sage.common.config.ports.SagePorts` (no hard-coded port literals).

## Fast developer workflow
- Setup dev environment from repo root: `./quickstart.sh --dev --yes`.
- Diagnose env issues: `./quickstart.sh --doctor`.
- Quality auto-fix: `sage-dev quality fix --all-files`.
- Quality checks: `sage-dev quality check --all-files --readme`.
- Main test run: `sage-dev project test --coverage`.
- Package-scoped tests use `packages/<pkg>/tests/`; root `pytest.ini` is configured to collect package tests only.

## Documentation and file placement
- Root `docs/` is forbidden by hooks (`tools/hooks/check_docs_location.sh`).
- Put project docs under `docs-public/docs_src/...`; package docs under `packages/<pkg>/README.md` or `packages/<pkg>/docs/`.
- If `docs-public/` is not present in this checkout, rely on root docs (`README.md`, `DEVELOPER.md`, `CONTRIBUTING.md`) and package READMEs as source of truth.

## Integration map (what to call, what not to reintroduce)
- LLM control-plane/gateway functionality is externalized; prefer `isagellm` integration points instead of re-adding legacy in-repo gateway patterns.
- Middleware feature integrations map to independent packages (e.g., `isage-vdb`, `isage-neuromem`, `isage-flow`, `isage-tsdb`).
- Keep SAGE-side code focused on stable contracts/interfaces and adapters across layers.

## High-signal paths to inspect first
- Root workflow/docs: `README.md`, `DEVELOPER.md`, `CONTRIBUTING.md`, `quickstart.sh`, `pytest.ini`.
- Quality/hooks: `tools/pre-commit-config.yaml`, `tools/hooks/check_docs_location.sh`.
- Meta-package: `packages/sage/pyproject.toml` — version pins for all sub-package dependencies.
- Install logic: `tools/install/installation_table/core_installer.sh` — installs `packages/sage` (or `packages/sage[dev]`) only.
