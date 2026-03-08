# SAGE Layer Ownership Matrix v1 (Wave A / A1)

> Status: Approved for Phase 1 baseline\
> Source issue: [#1473](https://github.com/intellistream/SAGE/issues/1473)\
> Parent issue: [#1471](https://github.com/intellistream/SAGE/issues/1471)\
> Master tracker: [#1472](https://github.com/intellistream/SAGE/issues/1472)

## 1) Purpose

This document defines the canonical ownership boundaries for SAGE L1-L5 in this meta repository,
including:

- In-scope responsibilities per layer
- Out-of-scope responsibilities per layer
- Forbidden dependency directions and import patterns
- Typical violation examples and fix direction
- Phase 1 remediation priority

This is the review baseline for all boundary refactor work.

## 2) Independent Sub-Repository Coordination Boundary (Polyrepo)

`SAGE` is a meta repository. Most implementation ownership is in independently versioned sub-repos,
and only becomes visible in this repo after release + version pin update.

| Area                                  | Primary Ownership Repo(s)                                                                                                                                                                    | In-Scope for `SAGE` Meta                                                                        | Out-of-Scope for `SAGE` Meta                                                                 |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Core layer packages (L1-L5)           | `sage-common`, `sage-platform`, `sage-kernel`, `sage-libs`, `sage-middleware`, `sage-cli`                                                                                                    | dependency pin governance, integration contract, docs and workflow guardrails                   | direct feature implementation that should happen in the owning sub-repo                      |
| L3 algorithm capability repos         | `sage-agentic`, `sage-agentic-tooluse`, `sage-agentic-tooluse-sias`, `sage-rag`, `sageRefiner`, `sage-eval`, `sage-finetune`, `sage-libs-intent`, `sage-privacy`, `sage-safety`, `sage-edge` | feature-level capability integration contract and version governance                            | implementing algorithm internals in `SAGE` meta as temporary shortcut                        |
| L4 middleware/engine capability repos | `sageVDB`, `neuromem`, `sageFlow`, `sageTSDB`                                                                                                                                                | capability composition and dependency pin orchestration through middleware/meta contracts       | moving backend runtime internals into L3 or directly into meta docs/scripts as fallback path |
| Runtime engine                        | `sageFlownet`                                                                                                                                                                                | runtime direction policy (Flownet-first), integration constraints                               | re-introducing `ray` dependency via meta-side shortcuts                                      |
| LLM inference ecosystem               | `sagellm` + its sub-repos                                                                                                                                                                    | integration entrypoint (`isagellm` dependency), capability contract for SAGE operators/CLI/apps | implementing control-plane/backend/protocol internals inside SAGE core layers                |
| Bench/docs/examples                   | dedicated L6 repos                                                                                                                                                                           | reference linkage, compatibility notes                                                          | core architecture boundary ownership changes                                                 |

Coordination rule (mandatory):

1. Fix boundary violations in the owning sub-repo first
1. Publish that sub-repo package
1. Bump version pin in the meta repo dependency file
1. Verify integration in `SAGE` meta

No meta-side compatibility shim should be added to bypass step 1.

## 2.2) Ownership Matrix (L1-L5)

| Layer | Package(s)                   | In Scope (MUST own)                                                              | Out of Scope (MUST NOT own)                                                                            |
| ----- | ---------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| L1    | `isage-common`               | config/logging/protocols/base utils/base service primitives                      | scheduling/runtime orchestration/operator business logic/app CLI                                       |
| L2    | `isage-platform`             | queue/storage/service abstractions/runtime adapters                              | algorithm implementations/domain operators/user-facing CLI                                             |
| L3    | `isage-kernel`, `isage-libs` | dataflow runtime + scheduler (`kernel`), algorithm interfaces/factories (`libs`) | infrastructure-bound middleware resources (VDB/memory backends/networked operators), app orchestration |
| L4    | `isage-middleware`           | domain operators + service-binding components (VDB/memory/flow/TSDB integration) | top-level CLI UX/tooling commands                                                                      |
| L5    | `isage-cli`                  | user-facing commands, platform/app operation entrypoints                         | lower-layer reusable core logic reimplementation                                                       |

## 3) Dependency Direction Rules

Allowed direction (strict):

```text
L5 -> L4 -> L3 -> L2 -> L1
```

Forbidden:

1. Reverse import (e.g. `L2 -> L3`, `L1 -> L4`)
1. L3 runtime/service-bound implementations in `sage-libs`
1. Compatibility shim / re-export / fallback layers that hide migration work
1. New `ray` dependency/imports (Flownet-first policy)
1. Implementing sub-repo-owned runtime/LLM internals directly in `SAGE` meta as a workaround

## 3.1) Independent Sub-Repository Boundary (Polyrepo Mandatory)

SAGE is a polyrepo ecosystem. This meta repository (`intellistream/SAGE`) is the composition entry,
not the implementation home for all capabilities.

Mandatory rules:

1. Sub-package implementation changes must be done in their own repositories first (`sage-common`,
   `sage-platform`, `sage-kernel`, `sage-libs`, `sage-middleware`, `sage-cli`, etc.).
1. `SAGE` meta repo consumes published versions via root package metadata; no implicit local sibling
   coupling assumptions.
1. Cross-repo rollout order is: sub-repo publish -> bump pin in meta repo -> meta integration
   verification.
1. Do not add local editable install requirements for sibling sub-repos in default setup/docs as a
   replacement for versioned dependency governance.

Review trigger:

- Any PR touching boundary/migration text must state whether it is a sub-repo change or a meta-pin
  orchestration change.

### External Capability Repo Set (non-exhaustive, workspace-validated)

- Middleware/engine capabilities: `sageVDB`, `neuromem`, `sageFlow`, `sageTSDB`
- L3 capability algorithms: `sage-agentic`, `sage-agentic-tooluse`, `sage-agentic-tooluse-sias`,
  `sage-rag`, `sageRefiner`, `sage-eval`, `sage-finetune`, `sage-libs-intent`, `sage-privacy`,
  `sage-safety`, `sage-edge`
- LLM capabilities: `sagellm` family (`sagellm-core`, `sagellm-backend`, `sagellm-control-plane`,
  `sagellm-gateway`, etc.)

Governance implication: all these repos are implementation owners; `SAGE` meta is integration and
contract governance only.

## 3.2) `sagellm` Capability Boundary (Mandatory)

`isagellm` is an independent SageLLM meta package/repository family and must be treated as an
external capability package from SAGE meta governance perspective.

Boundary rules:

1. Keep SAGE core layers (L1-L5) focused on framework/runtime/contracts; do not re-embed SageLLM
   control-plane/gateway internals into SAGE core packages.
1. LLM inference/gateway capability should be integrated through declared package dependency and
   stable API usage (`isagellm` and its sub-repos), not by copying implementation into SAGE layers.
1. No compatibility shim/fallback import path between legacy in-repo gateway code and `sagellm`
   packages; update call sites directly to canonical package paths.
1. Any change that claims SageLLM capability in SAGE docs/UX must include explicit package-level
   ownership statement (which repo owns implementation, which repo only orchestrates).

Capability scope reminder:

- SAGE meta: orchestration/integration and dependency declaration.
- SageLLM repos: protocol, comm, core engine, backend, kv-cache, compression, control-plane,
  gateway, and their benchmark/dev-tools/docs/website.
- Other independent capability repos (non-exhaustive but mandatory in boundary review): runtime/
  middleware engines `neuromem`, `sageVDB`, `sageFlow`, `sageTSDB`; L3 algorithm repos
  `sage-agentic*`, `sage-rag`, `sageRefiner`, `sage-eval`, `sage-finetune`, `sage-libs-intent`,
  `sage-privacy`, `sage-safety`, `sage-edge`, `sage-anns`, `sage-amms`.

## 4) Forbidden Import Patterns (Examples)

> These are policy examples used during review and grep-based audits.

1. `sage.common` importing any of:
   - `sage.platform`
   - `sage.kernel`
   - `sage.libs`
   - `sage.middleware`
   - `sage.cli`
1. `sage.platform` importing any of:
   - `sage.kernel`
   - `sage.libs`
   - `sage.middleware`
   - `sage.cli`
1. `sage.libs` containing runtime/service-coupled backend logic
1. New module-level fallback imports such as:
   - `try: import new_path ... except: import old_path ...`

## 5) Violation Examples and Direct Fix Strategy

| Violation Type              | Example Symptom                                    | Direct Fix (No Shim)                                                   |
| --------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------- |
| Upward dependency           | L2 module imports L3 scheduler helper              | Move helper to L2/L1 interface or update caller to consume L2 API      |
| Runtime code in `sage-libs` | VDB/network client appears in L3 interface package | Move runtime implementation to L4 and keep only protocol/factory at L3 |
| Compatibility re-export     | old path re-exports new API silently               | Update all call sites to new path and remove old export                |
| Fallback import             | dual-path import to preserve legacy path           | keep only canonical import path, fail-fast on missing dependency       |

## 6) Phase 1 Remediation Priority (for tracking)

P0 (must clear first):

1. Any reverse dependency violating `L5 -> L4 -> L3 -> L2 -> L1`
1. Any new/existing shim/fallback that masks boundary migration
1. Any new `ray` import introduced after Flownet-first policy

P1:

1. Runtime/service-bound logic hosted in `sage-libs`
1. Mixed ownership modules with both interface and concrete infra behavior

P2:

1. Documentation and script references that still imply old boundary assumptions
1. Non-blocking import-path cleanup in tests/examples

## 7) Review Checklist (PR/Issue)

- [ ] Does this change preserve strict layer direction?
- [ ] Does this change avoid compatibility shim/re-export/fallback?
- [ ] Are runtime/service implementations kept out of `sage-libs`?
- [ ] Are any dependency additions truly layer-necessary?
- [ ] Does this change avoid introducing `ray`?

## 8) No-Compatibility-Layer Checklist Baseline (A3)

To make reviews consistent across contributors, the following checklist is now mandatory in the PR
template:

- [ ] No dual-path import (`try new_path` + `except old_path`) is introduced
- [ ] No compatibility alias/re-export wrapper is added for migration convenience
- [ ] Call sites are updated directly to canonical import paths
- [ ] Missing dependency/path fails fast (no silent fallback)

## 9) Evidence for #1473 Completion

The boundary problem for A1 is "missing canonical ownership matrix in SAGE meta".

Resolved by:

1. Adding this repository-level matrix as review baseline
1. Explicitly defining independent sub-repo coordination boundary across capability repos (including
   `neuromem`, `sageVDB`, `sageFlow`, `sageTSDB`, and L3 algorithm repos)
1. Defining `sagellm` capability boundary in the same baseline document
1. Linking it from key contributor docs (`README.md`, `DEVELOPER.md`)
1. Backfilling links and conclusion in tracker issues

This document is the single source of truth for Wave A A1 boundary ownership in `SAGE`.

## 10) Evidence for #1475 Completion

The boundary problem for A3 is "review criteria for no-shim/no-fallback are not enforced uniformly
at PR intake".

Resolved by:

1. Defining a normalized "No-Compatibility-Layer Checklist Baseline" in this governance document
1. Wiring the same mandatory checks into `.github/PULL_REQUEST_TEMPLATE.md`
