# SAGE Dependency Management Plan

## Current State

The project currently has scattered dependency definitions for `vllm` and `transformers` across
multiple `pyproject.toml` files. This leads to maintenance difficulties and potential version
conflicts.

## Proposed Solution: Centralized Dependency Management

We should centralize the version definitions in `packages/sage-common/pyproject.toml` and have other
packages inherit or reference these versions.

### 1. Central Definition (sage-common)

Define the "source of truth" versions in `packages/sage-common/pyproject.toml`.

```toml
[project.optional-dependencies]
vllm = [
    "vllm>=0.10.1,<0.13",  # Pinned for stability
    "transformers>=4.52.0,<4.58.0", # Compatible with vLLM 0.12.x
    "torch>=2.4.0",
]
```

### 2. Downstream Usage

Other packages should ideally depend on `sage-common[vllm]` instead of redefining the version
constraints.

**Example (sage-libs):**

```toml
[project.optional-dependencies]
llm = [
    "isage-common[vllm]",  # Inherit version constraints
]
```

### 3. Benefits

- **Single Source of Truth**: Update vLLM version in one place.
- **Consistency**: Ensures all packages use compatible versions of vLLM, Torch, and Transformers.
- **Simplified Maintenance**: Easier upgrades in the future.

## Action Items

1. Refactor `sage-common` to export a robust `vllm` extra.
1. Update `sage-libs`, `sage-middleware`, `sage-apps` to depend on `isage-common[vllm]`.
1. Remove explicit version numbers from downstream packages.

## Future vLLM Upgrade Path

When upgrading to vLLM >= 0.14.0 (for Speculative Decoding support):

1. Update `sage-common/pyproject.toml`: `vllm>=0.14.0`.
1. Verify `transformers` compatibility (likely need newer version).
1. Re-install dependencies.
