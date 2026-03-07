# isage Meta Dependency Audit Gate

## Purpose

This document is the evidence registry for `pyproject.toml` direct dependencies. For Wave A task
`SAGE#1474`, any dependency declaration change must include callsite evidence update in this file.

## Gate Contract

- Gate script: `tools/scripts/check_meta_dependency_audit.py`
- Enforced in pre-commit and CI
- Hard rule:
  - Every direct dependency in `pyproject.toml` must have a dedicated section here.
  - Every section must include at least one `Callsite` entry.
  - If dependency declarations change, this document must be updated in the same change.

## Independent Sub-Repository Boundary (Mandatory)

`SAGE` is a meta repository in a polyrepo ecosystem.

- Sub-package implementations must be changed in the owning sub-repo first (`sage-common`,
  `sage-platform`, `sage-kernel`, `sage-libs`, `sage-middleware`, `sage-cli`, etc.).
- This document only audits dependency declaration evidence in `pyproject.toml`; it is not a bypass
  for sub-repo ownership.
- Cross-repo rollout order is mandatory:
  1. Sub-repo implementation + release
  1. Version pin update in `pyproject.toml`
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
- Any `isagellm` dependency change in `pyproject.toml` must provide callsite evidence proving
  integration/orchestration usage only, not internal implementation migration into SAGE core.

## Dependency Evidence Registry

### `isage-common`

- Callsite: `tools/verify_hello_world.py` (`import sage.common`, `import sage.libs`)
- Rationale: L1 base package; as of 0.2.5.0 absorbs `isage-libs` — `sage.libs.*` algorithm
  interfaces (BaseTool, RAG/agentic interfaces) now provided by this package.
- Version pin: `>=0.2.5.0`.

### `isage-platform`

- Callsite: `tools/verify_hello_world.py` (`import sage.platform`)
- Rationale: L2 platform import check in meta installation verification.

### `isage-kernel`

- Callsite: `tools/verify_hello_world.py` (`import sage.kernel`, `import sage.middleware`)
- Rationale: L2 runtime; as of 0.2.5.0 absorbs `isage-middleware` — `sage.middleware.*` pipeline
  operators and service adapters now provided by this package.
- Version pin: `>=0.2.5.0`.

### `isage-rag`

- Callsite: `sage-middleware` repo — `operators/rag/retriever.py`
  (`from sage_rag.backends import ChromaBackend, MilvusBackend`) — RAG retriever runtime depends on
  Chroma/Milvus backends.
- Rationale: RAG pipeline package; Chroma and Milvus vector store adapters migrated from
  `sage-middleware/components/vector_stores/` into `isage-rag 0.3.0`. Required by
  `isage-middleware>=0.2.4.47` at runtime.
- Version pin: `>=0.3.0`.

### `isage-libs-intent`

- Callsite: `sage-libs-intent` repo — `src/sage_libs/sage_agentic/intent/__init__.py` (intent
  recognition for tool-use agents)
- Rationale: L3 intent recognition library; required by `isage-studio` and tool-use agent pipelines.
  Implementation ownership in `sage-libs-intent` sub-repo.
- Version pin: `>=0.1.0.7`.

### `isage-neuromem`

- Callsite: `neuromem` repo — `sage/neuromem/__init__.py` (memory management engine for RAG)
- Rationale: L4 memory engine; required by `isage-studio` backend for memory collection and vector
  retrieval. Implementation ownership in `neuromem` sub-repo.
- Version pin: `>=0.2.1.4`.

### `isage-sias`

- Callsite: `sage-agentic-tooluse-sias` repo — `sage_sias/__init__.py` (SIAS continual-learning
  tool-use selection)
- Rationale: L3 continual-learning / coreset-selection for tool-use agents; required by
  `isage-studio`. Implementation ownership in `sage-agentic-tooluse-sias` sub-repo.
- Version pin: `>=0.1.0`.
- **Note (2026-03-08)**: moved from `project.dependencies` to
  `project.optional-dependencies.capability-tooluse`; still included transitively via `isage[full]`
  → `isage[capability-tooluse]`.

### `isage-cli`

- Callsite: `tools/verify_hello_world.py` (`import sage.cli`)
- Rationale: L5 CLI import check in meta installation verification.

### `isage-flow`

- Callsite: `.github/workflows/ci-integration.yml` (smoke test install list includes `isage-flow`)
- Rationale: runtime package is a required transitive runtime for meta integration smoke tests.

### `isage-dev-tools`

- Callsite: `README.md` (`pip install isage[dev]` explicitly states dev install includes
  `isage-dev-tools`)
- Callsite: `DEVELOPER.md` (`sage-dev` workflow and external `sage-dev-tools` repository guidance)
- Rationale: developer workflow CLI is independently released in `sage-dev-tools`; `SAGE` meta
  should depend on it instead of shipping the implementation in-tree.

### `isagellm`

- Callsite: `setup.py` (installation hint explicitly references `pip install isagellm`)
- Callsite: `README.md` (`SageLLMGenerator` usage and ecosystem package list)
- Rationale: LLM gateway/inference integration entry in meta package; capability implementation
  ownership remains in independent `sagellm*` repositories.

## Change Log

| Date       | Dependency                                                                                                | Change Type        | Callsite Evidence Updated | Notes                                                                                                                         |
| ---------- | --------------------------------------------------------------------------------------------------------- | ------------------ | ------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| 2026-03-01 | isage-common, isage-platform, isage-kernel, isage-libs, isage-middleware, isage-cli, isage-flow, isagellm | Baseline registry  | Yes                       | Initial gate rollout for SAGE#1474                                                                                            |
| 2026-03-01 | isage-middleware                                                                                          | Version bump       | Yes                       | Bump to >=0.2.4.32; drop `accelerate`/`peft`/`torch`/CUDA transitive deps (~2 GB)                                             |
| 2026-03-02 | isage-common, isage-libs, isage-middleware                                                                | Version bump       | Yes                       | Pins updated to >=0.2.4.23 / >=0.2.4.28 / >=0.2.4.35,\<0.2.4.36; neuromem optional                                            |
| 2026-03-02 | isage (optional `full`)                                                                                   | Dependency cleanup | Yes                       | Removed `torch`/`torchvision`/`accelerate`/`peft` from meta `full`; dev remains `full+dev`                                    |
| 2026-03-04 | isage-libs-intent, isage-neuromem, isage-sias                                                             | New dep            | Yes                       | Add missing isage-studio transitive deps as direct pins                                                                       |
| 2026-03-04 | isage-middleware                                                                                          | Version bump       | Yes                       | Bump pin to >=0.2.4.43; middleware fixed phantom huggingface-hub dep                                                          |
| 2026-03-07 | isage-middleware, isage-rag                                                                               | Version bump / New | Yes                       | Bump middleware to >=0.2.4.47; add isage-rag>=0.3.0 (vector_stores migrated from middleware)                                  |
| 2026-03-08 | isage-sias                                                                                                | Restructure        | Yes                       | isage-sias moved from direct deps to optional capability-tooluse group; still in full via alias                               |
| 2026-03-08 | isage-dev-tools                                                                                           | Restore external   | Yes                       | External ownership restored; meta `dev` now depends on `isage-dev-tools`                                                      |
| 2026-03-08 | isage-common, isage-kernel, isage-libs, isage-middleware                                                  | Package merge      | Yes                       | isage-libs merged into isage-common 0.2.5.0; isage-middleware merged into isage-kernel 0.2.5.0; both removed from direct deps |

## How To Update

When `pyproject.toml` changes in dependencies:

1. Update relevant dependency sections in this file.
1. Add at least one concrete `Callsite` per changed dependency.
1. Append one row per changed dependency in `Change Log`.
1. Run:

```bash
python3 tools/scripts/check_meta_dependency_audit.py --enforce-change-evidence --staged
```
