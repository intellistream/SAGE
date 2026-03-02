# Architecture Layer Ownership Matrix v1 (Wave A)

> Canonical ownership matrix for SAGE / SageLLM polyrepo coordination.
>
> Priority rule for layer truth (high → low):
>
> 1. Repository-local `.github/copilot-instructions.md` (`Layer` declaration)
> 1. This matrix
> 1. Workspace labels in `SAGE.code-workspace`
>
> If conflicts appear, update lower-priority sources to match higher-priority sources.

Machine-readable source for automation:

- `packages/sage/docs/layer-manifest.json`
- Verified by `tools/scripts/check_layer_manifest_sync.py` (local hook + CI)

## SAGE Core (L1-L5)

| Layer | Repo(s)                      | PyPI package(s)                | Responsibility                               |
| ----- | ---------------------------- | ------------------------------ | -------------------------------------------- |
| L1    | `sage-common`                | `isage-common`                 | Foundation utilities / config / protocols    |
| L2    | `sage-platform`              | `isage-platform`               | Queue / storage / service abstractions       |
| L3    | `sage-kernel`, `sage-libs`   | `isage-kernel`, `isage-libs`   | Runtime + algorithm/interface layer          |
| L4    | `sage-middleware`            | `isage-middleware`             | Service binding / operators / infra adapters |
| L5    | `sage-cli`, `sage-dev-tools` | `isage-cli`, `isage-dev-tools` | User CLI + developer workflows               |

## SAGE Ecosystem (L6)

These repos are above the SAGE core stack and are not part of the L1-L5 dependency chain.

| Tier                   | Repo(s)                                                                                     |
| ---------------------- | ------------------------------------------------------------------------------------------- |
| L6 app/data/docs/bench | `sage-studio`, `sageData`, `sage-benchmark`, `sage-examples`, `sage-tutorials`, `sage-docs` |

## SageLLM Stack

SageLLM uses an independent layered stack. Layer tags in the SAGE workspace must follow this
mapping.

| Layer | Repo(s)                                                                                        | Notes                                          |
| ----- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Meta  | `sagellm`                                                                                      | Umbrella package / coordination                |
| L1    | `sagellm-protocol`                                                                             | Protocol definitions                           |
| L2    | `sagellm-comm`, `sagellm-backend`                                                              | Transport + hardware backend                   |
| L3    | `sagellm-kv-cache`, `sagellm-compression`                                                      | Cache/compression algorithms                   |
| L4    | `sagellm-core`, `sagellm-control-plane-benchmark`                                              | Engine runtime + control-plane benchmark suite |
| L5    | `sagellm-control-plane`                                                                        | Routing / scheduling / lifecycle               |
| L6    | `sagellm-gateway`, `sagellm-benchmark`, `sagellm-dev-tools`, `sagellm-docs`, `sagellm-website` | Gateway and upper-layer ecosystem              |

## Governance Checklist

- Keep `SAGE.code-workspace` layer labels aligned with repo-local layer declarations.
- Do not infer layers from folder names alone.
- For new repos, add/confirm `Layer` in local Copilot instructions first, then update this matrix
  and workspace labels.
- During reviews, reject PRs that introduce cross-layer direction violations (upward imports).
