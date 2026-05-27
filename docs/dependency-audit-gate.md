# SAGE Dependency Audit Gate

## Purpose

This document records the current direct and optional dependency surfaces declared in
`pyproject.toml` for the consolidated `isage` package.

Any dependency change in `pyproject.toml` must be reflected here in the same change.

## Gate Contract

- Gate script: `tools/scripts/check_meta_dependency_audit.py`
- Enforced in pre-commit and CI
- Every direct dependency or optional dependency group must have a matching evidence section.

## Consolidated Product Boundary

SAGE now ships its core product surface from the main repository:

- `sage.foundation`
- `sage.stream`
- `sage.runtime`
- `sage.serving`
- `sage.cli`
- `sage.edge`

The repo no longer treats the retired split-package layout as a set of direct dependency owners.

## Direct Dependency Evidence

### `cloudpickle`

- Callsite: `src/sage/runtime/flownet/runtime/comm/backends.py`
- Rationale: serialization library for distributed runtime communication backends.

### `pyyaml`

- Callsite: `src/sage/runtime/flownet/client/cluster_context.py`,
  `src/sage/runtime/flownet/node/cluster_inventory.py`
- Rationale: YAML parsing for cluster configuration and inventory management.

### Removed direct dependency: `tomli`

- Status: removed from `[project.dependencies]` in `pyproject.toml` after baseline moved to Python
  \>=3.11.
- Rationale: `tomllib` is available in stdlib for all supported runtimes, so backport is no longer
  required.

### `isagellm`

- Callsite: `src/sage/serving/gateway.py`
- Callsite: `README.md`
- Rationale: external inference engine and gateway family used through integration boundaries only.

## Optional Dependency Group Evidence

### `serving-edge`

- Packages: `fastapi`, `uvicorn`
- Callsite: `src/sage/edge/server.py`
- Rationale: edge aggregation and service exposure for the in-tree serving shell.

### `capability-adapters`

#### `isage-libs-intent`

- Callsite: optional tool-use / orchestration integrations documented in the main repo.
- Rationale: intent recognition remains an external capability adapter.

#### `isage-rag`

- Callsite: retrieval and vector-store adapter workflows referenced by the docs and examples.
- Rationale: RAG capability remains optional and external to the core stream/runtime surface.

#### `isage-neuromem`

- Callsite: memory-oriented integrations referenced by the docs and examples.
- Rationale: memory capability remains optional and external to the core stream/runtime surface.

### `capability-tooluse`

#### `isage-sias`

- Callsite: optional tool-use / continual-learning integrations.
- Rationale: SIAS remains an external capability adapter.

### `full`

- Packages: `fastapi`, `uvicorn`, `isage-libs-intent`, `isage-rag`, `isage-neuromem`, `isage-sias`,
  `isage-data`
- Callsite: `README.md`
- Rationale: convenience install for the consolidated main package plus optional adapters.

### `dev`

- Packages: `fastapi`, `uvicorn`, `httpx`, `pytest`, `pytest-cov`, `pytest-asyncio`, `pytest-mock`,
  `ruff`, `mypy`, `pre-commit`,
  `sagepypi @ git+https://github.com/intellistream/sagepypi.git@main`
- Callsite: `DEVELOPER.md`
- Rationale: in-tree `sage-dev` developer workflow, validation, and release tooling.

## How To Update

When `pyproject.toml` dependency declarations change:

1. Update the matching section in this file.
1. Keep at least one concrete callsite or workflow reference per dependency or dependency group.
1. Run:

```bash
python3 tools/scripts/check_meta_dependency_audit.py --enforce-change-evidence --staged
```
