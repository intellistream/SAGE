# isage Meta Dependency Audit Gate

## Purpose

This document is the evidence registry for `packages/sage/pyproject.toml` direct dependencies. For
Wave A task `SAGE#1474`, any dependency declaration change must include callsite evidence update in
this file.

## Gate Contract

- Gate script: `tools/scripts/check_meta_dependency_audit.py`
- Enforced in pre-commit and CI
- Hard rule:
  - Every direct dependency in `packages/sage/pyproject.toml` must have a dedicated section here.
  - Every section must include at least one `Callsite` entry.
  - If dependency declarations change, this document must be updated in the same change.

## Independent Sub-Repository Boundary (Mandatory)

`SAGE` is a meta repository in a polyrepo ecosystem.

- Sub-package implementations must be changed in the owning sub-repo first (`sage-common`,
  `sage-platform`, `sage-kernel`, `sage-libs`, `sage-middleware`, `sage-cli`, etc.).
- This document only audits dependency declaration evidence in `packages/sage/pyproject.toml`; it is
  not a bypass for sub-repo ownership.
- Cross-repo rollout order is mandatory:
  1. Sub-repo implementation + release
  1. Version pin update in `packages/sage/pyproject.toml`
  1. Evidence update in this document
  1. Meta integration verification (CI/pre-commit gate)

### Workspace-Validated Independent Repo Set (for boundary review)

Besides `sagellm`, current workspace confirms multiple independent capability repositories.

- Runtime/middleware capability repos: `neuromem`, `sageVDB`, `sageFlow`, `sageTSDB`
- L3 algorithm repos: `sage-agentic`, `sage-agentic-tooluse`, `sage-agentic-tooluse-sias`,
  `sage-rag`, `sageRefiner`, `sage-eval`, `sage-finetune`, `sage-libs-intent`, `sage-privacy`,
  `sage-safety`, `sage-edge`, `sage-anns`, `sage-amms`
- SageLLM capability repos: `sagellm`, `sagellm-protocol`, `sagellm-comm`, `sagellm-core`,
  `sagellm-compression`, `sagellm-kv-cache`, `sagellm-backend`, `sagellm-control-plane`,
  `sagellm-gateway` (plus benchmark/docs/dev-tools/website repos)

Governance implication: all the above are implementation owners; `SAGE` meta is integration,
dependency pin governance, and contract-level policy only.

## `sagellm` Capability Boundary (Mandatory)

`isagellm` is an external capability package family from independent SageLLM repositories.

- `SAGE` meta can depend on and orchestrate `isagellm` capability.
- `SAGE` core layers (L1-L5) must not re-embed SageLLM internals
  (protocol/core/backend/control-plane/gateway).
- Any `isagellm` dependency change in `packages/sage/pyproject.toml` must provide callsite evidence
  proving integration/orchestration usage only, not internal implementation migration into SAGE
  core.

## Dependency Evidence Registry

### `isage-common`

- Callsite: `tools/verify_hello_world.py` (`import sage.common`)
- Rationale: L1 base package import check in meta installation verification.
- Version pin: `>=0.2.4.23`.

### `isage-platform`

- Callsite: `tools/verify_hello_world.py` (`import sage.platform`)
- Rationale: L2 platform import check in meta installation verification.

### `isage-kernel`

- Callsite: `tools/verify_hello_world.py` (`import sage.kernel`)
- Rationale: L3 kernel import check in meta installation verification.

### `isage-libs`

- Callsite: `tools/verify_hello_world.py` (`import sage.libs`)
- Rationale: L3 libs import check in meta installation verification.
- Version pin: `>=0.2.4.28`.

### `isage-middleware`

- Callsite: `tools/verify_hello_world.py` (`import sage.middleware`)
- Rationale: L4 middleware import check in meta installation verification.
- Version pin: `>=0.2.4.33,<0.2.4.34`.

### `isage-cli`

- Callsite: `tools/verify_hello_world.py` (`import sage.cli`)
- Rationale: L5 CLI import check in meta installation verification.

### `isage-flow`

- Callsite: `.github/workflows/ci-integration.yml` (smoke test install list includes `isage-flow`)
- Rationale: runtime package is a required transitive runtime for meta integration smoke tests.

### `isagellm`

- Callsite: `packages/sage/setup.py` (installation hint explicitly references
  `pip install isagellm`)
- Callsite: `README.md` (`SageLLMGenerator` usage and ecosystem package list)
- Rationale: LLM gateway/inference integration entry in meta package; capability implementation
  ownership remains in independent `sagellm*` repositories.

## Change Log

| Date       | Dependency                                                                                                | Change Type       | Callsite Evidence Updated | Notes                                                                             |
| ---------- | --------------------------------------------------------------------------------------------------------- | ----------------- | ------------------------- | --------------------------------------------------------------------------------- |
| 2026-03-01 | isage-common, isage-platform, isage-kernel, isage-libs, isage-middleware, isage-cli, isage-flow, isagellm | Baseline registry | Yes                       | Initial gate rollout for SAGE#1474                                                |
| 2026-03-01 | isage-middleware                                                                                          | Version bump      | Yes                       | Bump to >=0.2.4.32; drop `accelerate`/`peft`/`torch`/CUDA transitive deps (~2 GB) |
| 2026-03-02 | isage-common, isage-libs, isage-middleware                                                                | Version bump      | Yes                       | Pins updated to >=0.2.4.23 / >=0.2.4.28 / >=0.2.4.33,\<0.2.4.34                   |

## How To Update

When `packages/sage/pyproject.toml` changes in dependencies:

1. Update relevant dependency sections in this file.
1. Add at least one concrete `Callsite` per changed dependency.
1. Append one row per changed dependency in `Change Log`.
1. Run:

```bash
python3 tools/scripts/check_meta_dependency_audit.py --enforce-change-evidence --staged
```
