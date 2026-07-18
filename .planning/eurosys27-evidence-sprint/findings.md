# Findings

- Starting branch `feature/semantic-mapreduce-paper` is clean at `987e9ff` and
  matches its remote; all repo-owned submodules are pinned and clean.
- Current primary online result is the complete nine-family, three-seed matrix:
  action-validated pooled F1 0.8571 versus hybrid 0.7801. The three-hardcase
  0.9301 versus 0.7204 result is mechanism-diagnostic only.
- Current live evidence is one model/endpoint with one decision sample per
  scenario/seed. Repeated-sampling stability and a cost/budget curve are the
  highest-value no-new-abstraction evaluation gaps.
- AIOps Challenge 2020 currently supports public replay at the
  `MapEvidence/Normalize` boundary. Its four fault windows do not automatically
  provide reliable reducer-level incident grouping ground truth.
- Final clean online rerun requires a rotated local dev-hub key and controlled
  NPU3 endpoint metadata tied to the exact clean commit; code must not claim or
  simulate credential rotation.
- Claim audit confirms the abstract and introduction use the complete nine-family
  online result as primary and explicitly disclaim production/cross-model
  robustness. The readiness report still contains a stale hardcase-centric
  "strongest claim" paragraph and stale latency/token numbers that must be
  reconciled with the expanded matrix.
- Existing online `run_metadata.json` records evidence label, git state,
  endpoint, model, workload, environment, and submodules, but it does not expose
  explicit repeated-sampling identifiers, request-attempt/retry policy, or a
  raw-response retention policy at top level.
- Per-case JSON retains `reducer_trace` and an execution contract, including
  bounded actions, state digests, validator ownership, commit outcome, and
  replay ID. The next audit must determine whether raw provider responses and
  attempt timing are fully retained or only normalized actions are retained.
- The action reducer currently stores each raw enum text (truncated to 120
  characters) and normalized action, but not the full provider response envelope,
  per-pair request timestamp/latency/error, temperature, or repeated-sample ID.
- `run_semantic_merge_matrix.py` has no repetition axis and filenames would
  overwrite repeated calls for the same scenario/seed/reducer. The comparison
  summarizer also reconstructs filenames without a sample dimension.
- Existing comparison regimes already supply fair baselines under one scorer:
  `hybrid-hint` is the non-LLM valid pre-edit state, free-form
  `llm-pairwise-validated` is the structured-output/workflow control, and
  `llm-pairwise-action-validated` is the bounded contract. The missing analysis
  is repeated-sample stability plus quality/latency/token statistics and budget
  sweeps, not another nominal wrapper.
- AIOps 2020 labels identify individual fault object/time/KPI windows, not
  multi-object incident equivalence classes. They cannot honestly score
  cross-evidence SemanticReduce grouping. A defensible minimum is external-data
  contract conformance (evidence IDs, bounded no-op, invalid-reference rejection,
  fallback preservation, digests, replay), explicitly without reducer F1.
- Hardware preflight finds NPU3 healthy and idle, port 18383 free, the scoped
  service inactive, and the Qwen2.5-7B model path present. NPU4/5 are occupied
  by unrelated jobs and remain untouched.
- The untracked dev-hub `.env` contains the required key variable, but its mtime
  is 2026-07-05, before the 2026-07-18 terminal exposure. Rotation is therefore
  not proven and the clean real-online gate must remain blocked. The repository
  has no safe rotation command; do not print, hash, or copy the existing value.
- The user has now explicitly authorized rotating this locally controlled
  `VLLM_HUST_API_KEY`. Rotation may proceed by generating the value inside a
  non-echoing process, atomically rewriting only the `.env` entry, preserving
  mode 0600, and recording a separate secret-free attestation.
