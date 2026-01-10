# ANNS - Unified Approximate Nearest Neighbor Search (Externalized)

**Status**: ✅ Implementations moved to external package `isage-anns`; this tree will be pruned to
registries/interfaces only.

`sage-libs` now serves as the **interface/registry layer**. Heavy wrappers/C++ implementations live
in the independent repository
[`intellistream/sage-anns`](https://github.com/intellistream/sage-anns) and PyPI package
[`isage-anns`](https://pypi.org/project/isage-anns/).

Install via extras (recommended):

```bash
pip install -e packages/sage-libs[anns]
```

If `isage-anns` is missing, attempts to create/use ANNS implementations should **fail fast** with an
actionable error—no silent fallbacks.

## What remains here

- Interface/registry contracts: `AnnIndex`, `AnnIndexMeta`, `create`, `register`, `registered`.
- Backward-compat shims until all imports are pointed to the external package.

## Migration guidance

1. Add `isage-anns` as an optional extra in `pyproject.toml` and install via extras.
1. Remove local implementations/wrappers after downstreams confirm the external package works.
1. Treat missing optional dependencies as errors—surface actionable messages.

## References

- External repo: https://github.com/intellistream/sage-anns
- Package architecture: `docs-public/docs_src/dev-notes/package-architecture.md`
- Migration tracker: `packages/sage-libs/docs/MIGRATION_EXTERNAL_LIBS.md`
