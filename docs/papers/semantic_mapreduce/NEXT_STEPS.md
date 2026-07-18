# EuroSys'27 Submission Freeze Checklist

This file is the authoritative post-remediation task list for the Semantic
MapReduce submission. The current paper and development evidence are suitable
for internal review; the items below distinguish final submission gates from
optional evidence upgrades.

## Required Before Submission Freeze

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
  `c92cb17f5e43a3a5b3699a736fc5bb410af9ffaf397d0773f63b2e41be4705d5`.
  The superseded SHA-bearing archive is explicitly non-submittable.
- [x] Build the private-title review PDF outside the tracked paper tree, rerun
  focused tests, inspect all rendered pages, and cross-check every paper number
  against the frozen result manifests and `claim-ledger.md`. The 11-page private
  review PDF SHA-256 is
  `6924163cd3fefada557e4ec12234df1b603fc6be7a95623e1344600b25e7049f`;
  neither its title/system-name sources nor PDF is Git-tracked.
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
`.sage/benchmarks/semantic-reduction-eurosys27-review-evidence.tar.gz`.
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
