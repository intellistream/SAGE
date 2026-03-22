# SAGE Copilot Instructions

## Scope and architecture
- SAGE is the core framework repo; examples/benchmarks/studio/docs are split into independent repos.
- Keep the 4-layer workspace dependency rule: L4 (apps) → L3 (CLI) → L2 (runtime/stream) → L1 (foundation) only (no upward imports).
- Runtime direction is Flutty-first: use `flutty` integration patterns, do not introduce new `ray` imports/dependencies.
- Keep algorithm/tooling adapters external when they do not belong to the consolidated in-tree core; keep shared contracts in lower layers and keep applications above `sage-cli`.

## Polyrepo architecture (critical)
- SAGE is still coordinating multiple independently released packages, but the main repo is actively reclaiming stream/runtime/serving ownership in-tree.
- This repo (`intellistream/SAGE`) now ships the editable package from `src/` via the root `pyproject.toml`.
- External sub-package changes are only visible here after publication to PyPI and a version bump in the root `pyproject.toml`.
- Do not add local editable installs of external sub-packages to `quickstart.sh` or install helpers. The standard flow is `pip install -e .` or `pip install -e '.[dev]'`.

## Critical repo conventions
- No manual dependency drift: update external sub-package version pins in the root `pyproject.toml` only after the sub-package is published to PyPI.
- Branch policy: use `main` as the only working/integration branch. Do not create, target, or reference `main-dev` in workflows, docs, scripts, or PR guidance. For large changes, use a `feature/*` branch and merge via PR into `main`.
- NEVER create any new Python virtual environment (`venv`/`.venv`) in this repo under any circumstance.
- Do not use an active Python venv for SAGE install/run/test flows; if `VIRTUAL_ENV` is set, exit and switch to Conda or a pre-configured non-venv Python environment.
- Never suggest or invoke `--auto-venv`, `python -m venv`, or `virtualenv` in SAGE workflows.
- If a task, script, or prompt requests creating a venv, do not do it; use an existing non-venv Python environment instead.
- Fail-fast policy: avoid silent fallback patterns that hide missing config/import/runtime errors.
- Do not add compatibility shims/re-export layers during migrations; update call sites directly.
- Centralize service ports via `sage.foundation.config.ports.SagePorts` (and keep lower-layer exports aligned; no hard-coded port literals).

## Fast developer workflow
- Setup dev environment from repo root: `./quickstart.sh --dev --yes`.
- Diagnose env issues: `./quickstart.sh --doctor`.
- Quality auto-fix: `sage-dev quality fix --all-files`.
- Quality checks: `sage-dev quality check --all-files --readme`.
- Main test run: `sage-dev project test --coverage`.
- Root package code lives under `src/sage/`; root `pytest.ini` is configured for the main repo test collection.

## Documentation and file placement
- User-facing project docs are centralized in the `sage-docs` repository; add `../sage-docs` to the multi-root workspace when available.
- In this meta repo, keep only root entry docs (`README.md`, `DEVELOPER.md`, `CONTRIBUTING.md`) plus machine-owned governance artifacts such as `docs/layer-manifest.json` and dependency audit evidence.
- Do not add new duplicated user-facing markdown under root `docs/`; publish or update it in `sage-docs` instead.

## Integration map (what to call, what not to reintroduce)
- LLM control-plane/gateway functionality is externalized; prefer `isagellm` integration points instead of re-adding legacy in-repo gateway patterns.
- Middleware and higher capability integrations map to optional packages (e.g., `isage-rag`, `isage-neuromem`, `isage-sias`).
- Keep SAGE-side code focused on stable contracts/interfaces, stream/runtime ownership, and serving adapters across layers.

## High-signal paths to inspect first
- Root workflow/docs: `README.md`, `DEVELOPER.md`, `CONTRIBUTING.md`, `quickstart.sh`, `pytest.ini`.
- Quality/hooks: `.pre-commit-config.yaml`, `tools/hooks/check_docs_location.sh`.
- Meta-package: `pyproject.toml` — version pins for all external dependencies.
- In-tree surfaces: `src/sage/foundation/`, `src/sage/stream/`, `src/sage/runtime/`, `src/sage/serving/`.

## 🚫 NEVER_CREATE_DOT_VENV_MANDATORY

- 永远不要创建 `.venv` 或 `venv`（无任何例外）。
- NEVER create `.venv`/`venv` in this repository under any circumstance.
- 必须复用当前已配置的非-venv Python 环境（如现有 conda 环境）。
- If any script/task suggests creating a virtualenv, skip that step and continue with the existing environment.
