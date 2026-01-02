# ANN Migration Plan (benchmark_anns → sage-libs)

Last updated: 2025-12-28

## Goals

- Consolidate reusable ANN implementations under L3 `sage-libs` to allow sharing by benchmark_anns,
  sage-db, and sage-flow.
- Preserve layering: L3 provides algorithms; L4/L5 consume via a factory (no upward deps).
- Keep heavy dependencies optional via extras; fail fast with clear ImportError if missing.

## Target layout (L3)

```
packages/sage-libs/src/sage/libs/ann/
  base.py        # AnnIndex, AnnIndexMeta (abstract interface)
  factory.py     # register/create/registry view
  implementations/
    faiss/       # HNSW, IVF-PQ, etc. (faiss extra)
    diskann_ms/  # DiskANN MS flavor (diskannpy extra)
    vsag/        # VSAG HNSW (vsag extra if needed)
    dummy/       # Reference/brute-force for tests
```

## Migration phases

1. Interfaces ready (DONE): `sage.libs.ann` base + registry.
1. Light implementations: port pure/low-dep algorithms (e.g., Faiss HNSW/IVF-PQ) with extras and
   unit tests; add thin wrappers in benchmark_anns pointing to the new factory.
1. Heavy implementations: port DiskANN MS flavor, VSAG, others behind extras and markers; keep
   perf/benchmark scripts in benchmark_anns.
1. Consumers update: benchmark_anns, sage-db, sage-flow resolve ANN via `AnnFactory` (no direct
   algorithm imports); performance tests stay in benchmark_anns.

## Candidate algorithms to port first

- `faiss_HNSW`, `faiss_HNSW_Optimized`, `faiss_IVFPQ`, `faiss_pq`
- `diskann` (MS flavor), `ipdiskann` (if interface-compatible)
- `vsag_hnsw`

## Compatibility approach

- Maintain thin wrappers in `benchmark_anns/bench/algorithms/*` during transition; wrappers call
  `sage.libs.ann.create(name, **cfg)`.
- Keep benchmark_anns-only harness (runbooks, perf metrics) in place; do not move perf scripts.
- Add pytest markers for heavy deps (`ann_heavy`, `ann_faiss`, `ann_diskann`). CI can opt-in
  selectively.

## Dependency handling

- Add extras to `packages/sage-libs/pyproject.toml` (planned): `[ann-faiss]`, `[ann-diskann]`,
  `[ann-vsag]`.
- Explicit import guards with actionable error messages (no silent fallbacks).

## Next steps

- (DONE) Add `implementations/` skeleton in `sage.libs.ann` with a dummy/brute-force index and
  registration helper.
- Draft wrapper for one Faiss-based algorithm to validate the API and wiring.
- Update benchmark_anns registry to optionally resolve via `sage.libs.ann` when available; keep
  legacy path as fallback only during migration window.
