# Semantic MapReduce Mechanism-Completion Checklist

This is the active post-v1 task list. The goal is mechanism-complete and
offline-evidence-ready, not deadline closure. The paper is not submission-ready.

## Active Offline Gates

- [x] Define the executable H0 → finite catalog → ID selection → Validate →
  atomic Commit → Trace contract and distinct KEEP/ABSTAIN/no-proposal/failure
  outcomes.
- [x] Implement true system-generated SPLIT plans for conflicting hints,
  temporal gaps, and disconnected topology; implement bounded MERGE proposals.
- [x] Test conservation, duplicate/missing/foreign evidence, conflicts, atomic
  rollback, permutation/source-label/renaming invariance, checkpoint, and
  independent-process replay.
- [x] Freeze development/held-out seeds, ambiguity axes, proposal budgets, and
  success gates before viewing held-out results.
- [x] Establish shared-H0/shared-catalog H0, proposal-oracle, deterministic,
  mock ID-only policy, and permission-labeled constrained-reference layers.
- [x] Commit the mechanism/docs base and reach a clean parent tree
  without discarding the existing Figure 3 drafts.
- [x] Run full development and held-out `simulation/model` matrices from that
  clean commit into new non-overwriting directories and quantify coverage,
  truncation, selector quality, conditioned deltas, conservation, separability,
  and failure taxonomy.
- [x] Regenerate only `derived-artifact` tables/figures from the clean matrix,
  update claims, and verify the frozen online tree content hash is unchanged.
- [ ] Push the final clean parent commit and synchronize the umbrella handoff.

Clean runs are frozen as `bb140c0-development`, `bb140c0-heldout`, and
`bb140c0-audit-final`. The 40-unit held-out matrix passes every offline gate:
36 oracle repairs, improving merge/split proposals in 29/14 units, shared
catalog digest equality, and no online execution. The replacement anonymous
archive bundles its verifier and passes a safe independent extraction; its
SHA-256 is
`882e1b0a952e7fed7ab0964462bf42efeadb2a14eea81bc438bf14b690696fb7`.

Clean matrix command (after the tree is clean):

```bash
PYTHONPATH=src /home/shuhao/miniconda3/envs/esage-vllm-hust-dev/bin/python \
  tools/benchmark_carrier/run_semantic_reduce_edit_offline_matrix.py \
  --split development --run-id <clean-commit>-development
PYTHONPATH=src /home/shuhao/miniconda3/envs/esage-vllm-hust-dev/bin/python \
  tools/benchmark_carrier/run_semantic_reduce_edit_offline_matrix.py \
  --split heldout --run-id <clean-commit>-heldout
```

## Online v2 Status: BLOCKED

Do not use NPU or start a new online sweep in this phase. A runbook may be
written only if true-SPLIT, conservation/atomicity/replay, merge+split proposal
coverage, shared selector input, reduced score/hint proxy, and a falsifiable
model increment all pass. Endpoint/model/hardware/credentials readiness and
secret-safe logging must then be checked independently. Replay or old responses
cannot substitute for a v2 real-online run.

## Historical 2026-07-18 Submission Checklist (Superseded)

The checked items below record the prior merge-only v1 evidence sprint. They do
not determine current readiness and must not be read as v2 SPLIT validation.

### Previously Required Before Submission Freeze

- [x] Rotate the local dev-hub test API key that appeared in one local terminal
  diagnostic. Confirm that no key, bearer header, `.env` content, home path,
  hostname, private IP, or email address is present in tracked files or the
  submission archive. Create an untracked, secret-free rotation attestation and
  pass it through `SAGE_SMR_KEY_ROTATION_ATTESTATION`.
- [x] Freeze a clean SAGE commit with clean repo-owned submodules on their
  documented `feature/semantic-mapreduce-*` branches.
- [x] Start the controlled NPU3 endpoint from the pinned repo-owned dev-hub and
  runtime-manager paths in `esage-vllm-hust-dev`; record fresh endpoint metadata
  against the frozen commit.
- [x] Repeat all nine scenario families with seeds `7,11,13` using
  `hybrid-hint`, `llm-pairwise-validated`, and
  `llm-pairwise-action-validated`, with at least five samples per case. Do not set
  `SAGE_SMR_ALLOW_DIRTY_PARENT=1` for this run.
- [x] Require the clean rerun to preserve the contract gate: every model action
  is accepted, rejected, or converted to `ABSTAIN`; committed outputs are
  validator-owned; invalid edits preserve `H_0`; every row has a replay ID and
  state digests; fallback/invalid counts remain explicitly reported.
- [x] Regenerate the anonymous archive with
  `package_semantic_merge_artifact.py`, run its anonymity audit and
  `verify_semantic_merge_artifact.py`, and record the archive SHA-256 here and
  in `readiness-report.md`:
  `f590fde5a371c2d663ebeddd9b609fe4d6ea74a5f36c794e9fd3fbad2d73d4a0`.
  The independently extracted package contains 693 files, including 243 raw
  second-scale reports and the final 27-row runtime-contract matrix; identity,
  email, exact Git-SHA, and private-IP scans each report zero matches.
  The superseded SHA-bearing archive is explicitly non-submittable.
- [x] Build the private-title review PDF outside the tracked paper tree, rerun
  focused tests, inspect all rendered pages, and cross-check every paper number
  against the frozen result manifests and `claim-ledger.md`. The 12-page private
  review PDF SHA-256 is
  `5d2a46f1a011e87b1575cd391bfc7ef5c4070fb1a38a1d75b91800cb4263ebdf`;
  neither its title/system-name sources nor PDF is Git-tracked.
- [x] Strengthen the paper's runtime/operator framing with a concrete
  admit--reduce--select--propose--assemble--validate--publish--recover
  lifecycle figure. Keep checkpoint recovery scoped to the
  model-free runtime-contract matrix and live evidence scoped to compatible
  state digests/outcomes; do not imply distributed exactly-once execution.
- [x] Verify the paper against the live EuroSys 2027 CFP: at most 12 technical
  pages plus references, letter/A4 two-column layout, page numbers, double-blind
  anonymization, grayscale-readable figures, optional supplementary material,
  and explicit AI-tool disclosure. Checked 2026-07-18 against
  <https://2027.eurosys.org/cfp.html>.
- [ ] Before upload, the authors must confirm the final author list, conflicts,
  per-author three-submission limit, ORCIDs, concurrent/resubmission status,
  artifact availability choice, and HotCRP metadata. These cannot be inferred
  from the anonymous repository.

## Clean Rerun Shape

After starting the controlled endpoint and writing a matching clean endpoint
metadata file:

```bash
ALLOW_NPU3_REAL_ONLINE=1 \
SEEDS=7,11,13 \
SCENARIOS=single-service,cascade,shared-bottleneck,concurrent,false-correlation,partial-evidence,ambiguous-disconnected-merge,ambiguous-temporal-split,ambiguous-overmerge \
REDUCERS=hybrid-hint,llm-pairwise-validated,llm-pairwise-action-validated \
SAGE_SMR_CONDA_ENV=esage-vllm-hust-dev \
SAGE_SMR_NPU_DEVICE=3 \
SAGE_SMR_LLM_BASE_URL=http://127.0.0.1:18383 \
SAGE_SMR_LLM_MODEL=<served-model-name> \
SAGE_SMR_ENDPOINT_METADATA=<clean-endpoint-metadata.json> \
SAGE_SMR_KEY_ROTATION_ATTESTATION=<untracked-rotation-attestation.json> \
SAGE_SMR_SAMPLES=5 \
RUN_ID=<frozen-commit>-eurosys27-9family-3seed \
tools/benchmark_carrier/run_npu3_semantic_merge_llm_comparison.sh
```

The clean, double-blind replacement is
`.sage/benchmarks/semantic-reduction-eurosys27-review-evidence-cross-audit-20260719.tar.gz`.
The older SHA-bearing package must not be uploaded.
Retain the earlier diff-hashed run only as development evidence.

## Optional Evidence Upgrades

- [x] Implement bounded-action repeated sampling, raw-attempt retention,
  within-case variance/exact-agreement aggregation, and the full artifact gate.
  The clean real-online execution is complete.
- [x] Add a second model scale while holding candidate generation, validators,
  scorer, workload seeds, candidate budget, and endpoint stack fixed. The 14B
  same-family matrix retains 243 raw reports; action F1 is 0.8392 versus 0.7801
  hybrid, with paired 27-unit delta `+0.0591` and 95% CI
  `[0.0147,0.1149]`. This does not establish cross-family robustness.
- [x] Add reducer-level external incident-unit evidence. The AIOpsArena complex
  case has 23 injection rows grouped by native timestamp/service/failure/duration
  labels into eight episodes. The replay is explicitly
  `reducer-only-label-conditioned` (`replay`), not end-to-end detection or
  production generality. A production-derived, non-oracle MapEvidence path
  remains unsupported and must not be claimed.
- [ ] Add a second execution substrate only if it tests the same operator
  contract; do not turn adapter breadth into an unsupported SOTA comparison.

These upgrades strengthen external validity but are not prerequisites for the
narrow claim that model-backed semantic edits can enter a distributed analysis
runtime through a bounded, validated, replayable execution contract.
