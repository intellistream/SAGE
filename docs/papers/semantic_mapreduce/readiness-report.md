# Semantic MapReduce Readiness Report

This report summarizes the current EuroSys'27-readiness state for the Semantic
MapReduce paper draft. It separates supported claims from mechanism probes and
keeps real-online evidence provenance explicit.

## Primary Online Result

Expanded nine-family, three-seed real-online artifact (27 rows per reducer):

```text
.sage/benchmarks/real_online_semantic_merge/20260718T-eurosys27-9family-3seed-real-online-v2/
```

| Reducer | Precision | Recall | F1 | Support recall | Reduce ms | Tokens | Accepted edits | Invalid/fallback |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `hybrid-hint` | 0.7692 | 0.8426 | 0.7801 | 0.7810 | 0.26 | 0.0 | 0.0 | 0 |
| `llm-pairwise-validated` | 0.8065 | 0.8056 | 0.7896 | 0.8116 | 3213.27 | 312.1 | 0.6296 | 0 |
| `llm-pairwise-action-validated` | 0.8852 | 0.8426 | 0.8571 | 0.8795 | 122.61 | 203.1 | 0.8148 | 0 |

This is now the main workload-coverage result. The clean three-hardcase artifact
below remains the strongest isolated ambiguity result and the anonymous package
source; its free-form schema-failure behavior should not be generalized to the
expanded structured-output run.

Clean three-workload-seed real-online artifact:

```text
.sage/benchmarks/real_online_semantic_merge/20260718T-smr-hardcases-3seed-5a8419e/
```

Anonymous submission artifact package:

```text
.sage/benchmarks/semantic-mapreduce-3seed-real-online-5a8419e-anonymous.tar.gz
sha256: 161446f93164b3985c481613768d22f5330a2dafeec4399f90615b1d83f6d640
```

The `.sage/` tree is ignored by git, so this archive should be attached as a
separate artifact rather than committed. The raw local evidence remains intact;
the submission package uses an allowlist, replaces identity-bearing paths,
hostnames, and private IPs, excludes historical service logs, and records source
and packaged SHA-256 hashes in `ANONYMIZATION_MANIFEST.json`.

Provenance:

- Evidence label: `real-online`
- Endpoint: `http://127.0.0.1:18383`
- Model: `qwen25-7b-sage-realonline`
- Hardware: NPU3, Ascend 910B2
- Conda env: `esage-vllm-hust-dev`
- Clean run parent commit: `5a8419eddd9b1971e38b8d2109e3bf8c78a44f8c`
- Paper package commit: any later paper-only synchronization commit that
  preserves this clean replay artifact and result table.
- Parent dirty: `false`
- `third_party/llm-serving-workloads`: `79ed8e3469c0bcfccdf1cd0a66efa2db27156055`
- `third_party/ascend-runtime-manager`: `c5b0461aaecffe7e5011f8fab0944d32bedb1092`, clean
- Workload source: repo-local `src/sage/workloads/semantic_merge_analysis.py`
- Scenarios: `ambiguous-disconnected-merge`, `ambiguous-temporal-split`, `ambiguous-overmerge`
- Workload seeds: `7`, `11`, `13`

## Operator Model Update

The paper now frames Semantic MapReduce as an operator algebra rather than a
workflow demo. The core operators are:

```text
Shard(D; pi) -> {D_i}
MapEvidence(D_i; phi) -> E_i
Normalize(E; sigma) -> E_hat
GroupEvidence(E_hat; gamma) -> C
SemanticReduce(C; rho) -> H_0
Edit(C, H_0; a) -> Delta, where a in {KEEP, MERGE, SPLIT, ABSTAIN}
Validate(H_0, Delta, E_hat; V) -> H or fallback(H_0)
ReportTrace(H, E_hat, T; tau) -> report + trace
```

This reframes the live LLM result as a reducer-interface result. Free-form
pairwise JSON asks the model to implement too much of `SemanticReduce` and
`ReportTrace` at once, so schema failures and evidence-reference failures
become reducer failures. The new action reducer maps the model to `Edit` only:
the model emits a bounded enum action, while the system owns evidence binding,
JSON assembly, schema validation, root/affected-service checks, fallback, and
trace capture. This is the central abstraction that should carry the EuroSys
paper narrative.

Three-hardcase, three-workload-seed aggregate (nine rows per reducer):

| Reducer | Precision | Recall | F1 | Support recall | Tokens | Accepted edits | Fallback | Invalid action | Invalid schema |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `semantic-graph` | 0.4427 | 0.4722 | 0.4318 | 0.5185 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| `hybrid-hint` | 0.6596 | 0.9167 | 0.7204 | 0.7083 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| `llm-pairwise-validated` | 0.6596 | 0.9167 | 0.7204 | 0.7083 | 508.7 | 0.0 | 1.0 | 0.0 | 9 |
| `llm-pairwise-action-validated` | 0.9630 | 0.9167 | 0.9301 | 0.9815 | 536.1 | 2.2222 | 0.0 | 0.0 | 0 |

Per-case action-validated outcomes:

| Scenario | Hybrid F1 | Action-validated F1 | Accepted merges | Main interpretation |
| --- | ---: | ---: | ---: | --- |
| `ambiguous-disconnected-merge` | 0.7273 | 1.0000 | 3 | Succeeds: validated merge edits repair fragmented incident evidence. |
| `ambiguous-temporal-split` | 0.5769 | 0.9333 | 3.67 | Two seeds reach F1 1.0; seed 7 retains two unmatched fragments. |
| `ambiguous-overmerge` | 0.8571 | 0.8571 | 0 | Safe abstention: action reducer avoids gratuitous edits and preserves baseline. |

## Accepted Edit Example

For `ambiguous-disconnected-merge`, the endpoint returned three enum actions:

```json
[
  {"pair": 0, "raw": "MERGE", "action": "MERGE", "valid": true},
  {"pair": 1, "raw": "MERGE", "action": "MERGE", "valid": true},
  {"pair": 2, "raw": "MERGE", "action": "MERGE", "valid": true}
]
```

The system assembled validated merge edits:

```json
[
  {"candidate": 0, "action": "merge", "candidates": [0, 4], "evidence_ids": ["e4", "e5"]},
  {"candidate": 2, "action": "merge", "candidates": [2, 6], "evidence_ids": ["e0", "e1"]},
  {"candidate": 3, "action": "merge", "candidates": [3, 5], "evidence_ids": ["e2", "e3"]}
]
```

The validator recorded `schema_valid=true`, `fallback_count=0`,
`repair_count=0`, `candidate_evidence_count=8`, and
`output_evidence_count=8`.

## Failure Taxonomy

- Output format: fixed for action reducers in the latest run. Free-form
  pairwise JSON still fails schema in all three cases.
- Candidate pair expression: still weak for `ambiguous-temporal-split`; valid
  pairwise merges reduce fragmentation but still leave too many hypotheses.
- Evidence coverage: not the blocker in the latest run; all three hardcases
  have evidence coverage 1.0.
- Action granularity: enum actions are sufficient for disconnected merge and
  safe abstention, but temporal grouping may need multi-pair grouping or
  transitive closure constraints.
- Model semantic ability: useful bounded merge decisions repeat across three
  workload seeds, but cross-model and repeated-sampling robustness are untested.
- Validator conservatism: not the blocker in the latest run; no validator
  rejection or fallback occurred for action-validated outputs.

## Strongest Current Claim

Semantic MapReduce is best framed as an operator algebra for evidence-linked
semantic reduction, not as a prompt chain. Its key operators are
`MapEvidence`, `SemanticReduce`, `Edit`, `Validate`, and `ReportTrace`.
Semantic Reduce should expose a constrained, evidence-linked edit protocol
rather than asking an LLM to emit free-form hypotheses or reducer JSON. In the
current prototype, one-token pairwise action classification maps the model only
to `Edit` and converts output instability into bounded action uncertainty:
invalid model text becomes `ABSTAIN`, evidence references are supplied by the
system, validators enforce the incident schema, and fallback protects baseline
output. A three-workload-seed real-online hardcase matrix shows this design can
accept validated merge edits and improve over `hybrid-hint` on covered ambiguous
merge cases under one model and endpoint.

## Current Final State

- Paper narrative has been updated around the `Semantic MapReduce Operator
  Model`.
- The complete nine-family, ten-seed derived matrix contains 540 rows (90 per
  reducer). `hybrid-hint` reaches mean F1 0.7796 versus 0.0705 map-only and
  0.4916 window aggregation. Artifact:
  `.sage/benchmarks/semantic_merge_analysis/20260718T-eurosys27-9family-10seed/`.
- The runtime-contract matrix covers nine families x seeds 7/11/13. All 27
  runs pass valid commit, invalid-edit rejection, baseline preservation,
  checkpoint-digest restoration, and deterministic replay. Artifact:
  `.sage/benchmarks/semantic_mapreduce_runtime_contract/20260718T-eurosys27-9family-3seed/`.
- The AIOps Challenge 2020 May-29 public replay consumes the official daily ZIP
  without republishing raw rows. It detects 2/4 official fault windows with
  zero false positives over eight matched negative windows (precision 1.0,
  recall 0.5, F1 0.6667). The misses are retained as evidence-coverage limits.
  Artifact: `.sage/benchmarks/aiops2020_public_replay/20260718T-may29-map-evidence-replay-v4/`.
- A new operator-algebra figure shows the model-facing boundary at `Edit`,
  while `Validate`, trace generation, and fallback remain system-owned.
- The action reducer is written as an `Edit` + `Validate` instance, not as a
  prompt-engineering trick.
- The rebuilt EuroSys PDF is 11 pages total, within the 12-page technical-
  content limit. All pages, tables, the operator diagram, and references were
  rendered to PNG and visually checked for clipping, overlap, and legibility.
- The final focused no-NPU regression selection passes under
  `esage-vllm-hust-dev`: `47 passed` across semantic-merge, runtime-contract,
  checkpoint/recovery, AIOps replay, summary, and shared-state tests.
- The three-hardcase, three-workload-seed NPU3 matrix passes the artifact gate:
  F1 0.9301 versus 0.7204 for `hybrid-hint`, support recall 0.9815, zero
  fallback/invalid schema/invalid action, and clean parent/submodule provenance.
- Implementation-layer boundary is explicit: the submitted Semantic MapReduce
  mechanism does not require new Ascend kernel, Triton operator, mask/packing,
  or runtime-operator semantic changes. If future work needs such behavior, it
  must land in the pinned `external/triton-ascend-hust` feature branch rather
  than as an ad hoc `vllm-ascend-hust` workaround; `vllm-ascend-hust` remains
  thin glue, and `vllm-hust` owns scheduler/KV/request-metadata concerns.
- The nine-family derived matrix, 27-run runtime fault matrix, and nine-family
  real-online action expansion are complete. The remaining submission gate is a
  clean-tree repetition and anonymous packaging of the full-coverage online
  matrix. Cross-model, repeated-sampling, and production incident-group claims
  remain separate evidence upgrades.

## EuroSys Workload-Coverage Gate

The current workload inventory contains nine unique repo-local scenario
families. All nine now have a common ten-seed derived matrix and three-seed
runtime fault injection; three ambiguity families have the current real-online
action matrix.

Before submission, organize coverage by contract obligation rather than by
adding more names:

| Obligation | Existing families | What the action path must demonstrate |
| --- | --- | --- |
| Sanity/no-op | `single-service` | Preserve an already-correct incident without gratuitous edits. |
| Positive cross-service fusion | `cascade`, `shared-bottleneck`, `ambiguous-disconnected-merge`, `ambiguous-temporal-split` | Accept only evidence-preserving merges and improve fragmentation when candidate ambiguity exists. |
| Negative separation | `concurrent`, `false-correlation`, `ambiguous-overmerge` | Reject spurious merges or abstain without regressing the hybrid baseline. |
| Incomplete evidence | `partial-evidence` | Expose that missing root evidence is a coverage/inference boundary; do not manufacture provenance. |
| Recovery/admission | all families | Every action is accepted, rejected, or mapped to `ABSTAIN`; rejected edits retain `H_0`, and the trace records action, validation, latency, and tokens. |

The completed real-online matrix uses all nine families with seeds `7`, `11`,
and `13` (27 case/seed rows per reducer), under the same model, endpoint,
evidence schema, scorer, and candidate generator. It keeps three fixed comparison
regimes:

1. `hybrid-hint` as the valid pre-edit state `H_0`;
2. `llm-pairwise-validated` as the free-form/schema negative control; and
3. `llm-pairwise-action-validated` as bounded `Edit` + system-owned `Validate`.

The expanded run meets the admission gate: accepted edits do not violate schema
or evidence invariants, pooled F1 improves, and all actions remain visible in
the trace. Per-family deltas are retained in the artifact. Cross-model and
repeated-sampling matrices remain robustness extensions.

## Claims Not Yet Supported

- Do not turn three controlled workload seeds on one model into broad stochastic,
  cross-model, or production robustness.
- Do not claim a quality-cost frontier; the action reducer still adds roughly
  536 estimated tokens and 324 ms mean reduce latency in the live matrix.
- Do not claim production incident-group generality; the AIOps replay covers
  public labeled metrics at MapEvidence/Normalize, while reducer quality still
  uses controlled incident-group labels.
- Do not claim that this replaces Spark, Flink, Ray, databases, LangGraph, or
  LlamaIndex.
- Do not claim that validators prove the LLM is always useful; validators make
  model edits auditable, rejectable, and fallback-safe.

## 2026-07-18 Evidence-Sprint Audit

The submission-facing claim boundary is sound, but the current online evidence
is still one sample per case on one model and endpoint. This sprint therefore
added an executable repeated-sampling and candidate-budget harness rather than
rewriting the existing point estimate as robustness evidence:

- `run_semantic_merge_matrix.py --samples N` writes a distinct raw report for
  every case/seed/reducer/sample tuple.
- The bounded action reducer retains model text, provider response envelope,
  prompt/response digests, timestamps, latency, and every request failure. No
  credential or bearer header is retained.
- `summarize_semantic_merge_stability.py` reports within-case F1 standard
  deviation and exact action agreement. Cross-workload F1 variation is not
  mislabeled as sampling instability.
- Provider-reported token usage is used when available; otherwise the artifact
  labels the value as a character-based estimate.
- `run_npu3_semantic_merge_stability_sweep.sh` evaluates candidate budgets
  `4,8,12` over all nine families, seeds `7,11,13`, and repeated samples, then
  derives a quality--reducer-latency--token curve. It does not claim an
  end-to-end serving speedup or a monetary-cost frontier.

A deterministic five-sample development run over all nine families verified
the repetition and aggregation plumbing. Its source evidence label is
`simulation/model`; it is not LLM stability evidence. A public AIOps replay now
also executes the reducer contract over the two detected official windows:
valid bounded edits commit, an edit that cites missing evidence is rejected,
the baseline is preserved, and deterministic replay succeeds. Because AIOps
2020 does not provide incident-group merge/split labels, this is external
contract conformance, not reducer-quality generalization.

The real-online stability/budget sweep is currently **blocked**: the local test
key predates a known terminal exposure and no post-exposure rotation has been
attested. The runner now requires a secret-free JSON attestation with
`rotated_utc`, `api_key_env`, and
`operator_acknowledged_no_key_logged=true`, and records only its basename and
SHA-256. A second model remains optional and requires a separately controlled
endpoint with matching clean-commit metadata; no result is inferred in its
absence.

Clean no-credential evidence at parent commit
`e0ffdffeef7a059ee3059064eb5c86a25307738a`:

```text
.sage/benchmarks/semantic_mapreduce_runtime_contract/20260718T-eurosys27-9family-3seed-e0ffdff-clean/
.sage/benchmarks/aiops2020_semantic_reduce_contract/20260718T-eurosys27-public-contract-e0ffdff-clean/
```

The runtime matrix is `derived-artifact`: 27/27 valid commits, invalid-edit
rejections, baseline-preservation checks, checkpoint restores, and
deterministic replays pass. The AIOps artifact is `replay`: it contains two
stable evidence IDs from the previously detected public windows and passes
valid commit, missing-evidence rejection, baseline preservation, and
deterministic replay. Its contract-result SHA-256 is
`f490e817a9ff1d04958d3853430c85fd879c716b574d666a39e03cdbdb7300ce`.

## Reviewer Attack Prep

**Is this just prompt engineering?**

No. The paper should answer this through the operator model. The model is not
asked to write an incident report or full reducer JSON; it implements only the
`Edit` operator over candidate pairs. `Validate` is a separate system operator
that owns evidence IDs, JSON construction, schema validation, merge
application, fallback, cost accounting, and trace capture. The experiment
contrasts free-form `SemanticReduce`-style JSON with `Edit`+`Validate` under
the same model, evidence, scorer, and endpoint.

**Why not just use JSON mode?**

JSON mode can make syntax valid but does not guarantee that the required
decision list is present, that evidence IDs are copied correctly, or that the
incident unit is preserved. The previous pairwise JSON path still falls back
with invalid schema in the latest hardcases. The action protocol removes JSON
generation from the model-facing contract and moves it into the system-owned
`Validate` path.

**Why is deterministic hybrid not enough?**

Hybrid-hint is a strong baseline and should stay in the paper. Its limitation
is visible on covered ambiguous merge cases: it recovers recall but over-reports
fragmented incidents. The action reducer improves disconnected merge to F1 1.0
and temporal split to F1 0.8 by applying evidence-preserving merge edits. The
correct framing is not "LLMs replace deterministic reducers"; it is that
deterministic reducers provide `H_0`, while bounded `Edit` can repair ambiguous
candidate relations when evidence coverage is sufficient.

**Does LLM instability invalidate the direction?**

It invalidates free-form reducer prompting, not Semantic Reduce. The system
contribution is to turn instability into an explicit protocol with bounded
actions, validation, and fallback.

**Do validators/fallback hide that the LLM contributes little?**

The artifact reports accepted edit count, fallback count, invalid action count,
invalid schema count, and per-case F1. In the latest action run, the validated
path has accepted edits and zero fallback; in prior runs, fallback preserved the
baseline and was reported rather than hidden.

**Is the workload toy?**

The workload is controlled, not production trace replay. Its role is to expose
operator-level semantic reduction behaviors that ordinary alert/window
benchmarks do not isolate. The paper should frame public/production replay as
the next validation step, while emphasizing that the suite has multiple
scenario families, shared scorer, evidence objects, and failure taxonomies.

**How is this different from LangGraph, Ray, Spark, or Flink?**

Those systems can carry parts of the computation. Spark/Flink/Ray can execute
`Shard`, `MapEvidence`, or grouping work; LangGraph/LangChain can express a
control flow. The paper's abstraction is the operator contract across
`MapEvidence`, `SemanticReduce`, `Edit`, `Validate`, and `ReportTrace`: bounded
evidence objects, candidate pairs, validated edits, fallback-safe execution,
and workflow trace under one scorer. Adapter results should be framed as
substrate probes, not SOTA leaderboards.

**Where is the systems contribution?**

The contribution is the reducer protocol and evaluation harness: standard
Semantic MapReduce operators, a semantic-merge workload suite, constrained
edit interfaces, evidence-linked validators, fallback-safe execution,
real-online NPU endpoint evidence, and claim discipline around coverage,
latency, token cost, and traceability.

## Status

READY for the bounded-contract mechanism claim and internal EuroSys review,
but NOT frozen for submission.
The real-online matrix and machine-executable artifact gates pass. Per-case/seed
JSON and CSV report F1, support recall, accepted edits, fallback, invalid
action/schema, tokens, latency, and failure taxonomy. The current PDF has 11
total pages and has passed a complete visual inspection. Final submission
freeze still requires the clean full-coverage rerun and regenerated anonymous
package tracked in [`NEXT_STEPS.md`](NEXT_STEPS.md).

The 2026-07-18 rebuilt PDF remains 11 letter-size pages. All pages were rendered
and visually inspected after the coverage-table correction; fonts are embedded
and no identity, home-path, email, replacement glyph, clipping, overlap, or
table/caption drift was found. PDF SHA-256:
`2ff1fe68fcad173274d6decfc9dd0ce09615068caeb8090b37e31eafa84b75b7`.

## Clean Replay Artifact Gate

The gate below has been run successfully for
`.sage/benchmarks/real_online_semantic_merge/20260718T-smr-hardcases-3seed-5a8419e/`.
Run it again only when refreshing the submission artifact or changing reducer
code.

Prerequisite endpoint path:

```bash
# Optional: start the NPU3 service through the repo-owned dev-hub/runtime path.
# This launches through external/vllm-hust-dev-hub/manage.sh and enforces NPU3.
SAGE_REAL_ONLINE_NPU_DEVICE=3 \
SAGE_REAL_ONLINE_PORT=18383 \
SAGE_REAL_ONLINE_RUN_ID=clean-semantic-merge-endpoint \
SAGE_REAL_ONLINE_EVENTS=2000 \
SAGE_REAL_ONLINE_SHARDS=4 \
tools/benchmark_carrier/run_npu3_semantic_mapreduce_experiment.sh \
  --skip-llm-reducer \
  --run-id clean-semantic-merge-endpoint
```

Clean hardcase replay:

```bash
RUN_ID=clean-pairwise-action-hardcases-$(git rev-parse --short HEAD) \
OUTDIR=.sage/benchmarks/real_online_semantic_merge/${RUN_ID} \
ALLOW_NPU3_REAL_ONLINE=1 \
SAGE_SMR_CONDA_ENV=esage-vllm-hust-dev \
SAGE_SMR_LLM_BASE_URL=http://127.0.0.1:18383 \
SAGE_SMR_LLM_MODEL=qwen25-7b-sage-realonline \
SAGE_SMR_LLM_MAX_EVIDENCE=24 \
SAGE_SMR_LLM_MAX_CANDIDATES=12 \
SAGE_SMR_LLM_MAX_TOKENS=8 \
SAGE_SMR_ENDPOINT_METADATA=.sage/benchmarks/real_online_semantic_mapreduce/20260718T-smr-multiseed-endpoint-5a8419e/metadata.json \
SEEDS=7,11,13 \
SCENARIOS=ambiguous-disconnected-merge,ambiguous-temporal-split,ambiguous-overmerge \
REDUCERS=semantic-graph,hybrid-hint,llm-pairwise-validated,llm-pairwise-action-validated \
SHARDS=8 \
INCIDENTS=4 \
bash tools/benchmark_carrier/run_npu3_semantic_merge_llm_comparison.sh
```

Required manifest fields:

- `evidence_label=real-online`.
- `conda_env=esage-vllm-hust-dev`.
- `hardware.npu_device=3` or equivalent `device_label=NPU3`.
- `git.commit`, `git.branch`, and `git.dirty=false`.
- Endpoint `base_url`, `model`, and `api_key_env`.
- Workload source: repo-local `src/sage/workloads/semantic_merge_analysis.py`.
- `third_party/llm-serving-workloads` commit and dirty status.
- Runtime submodule commits and dirty status, especially
  `third_party/ascend-runtime-manager`.
- Reducers, scenarios, seed, shards, incidents, token limits, and result path.

Pass criteria for keeping the current mechanism claim at a clean three-workload-
seed real-online result:

- `llm-pairwise-action-validated` has `fallback=0`, `invalid action=0`, and
  `invalid schema=0` over all nine case/seed runs.
- Mean F1 for `llm-pairwise-action-validated` is greater than `hybrid-hint`
  under the same scorer.
- `ambiguous-disconnected-merge` reaches F1 1.0 with at least one accepted
  evidence-preserving merge edit.
- `ambiguous-overmerge` does not regress below `hybrid-hint`.
- The result directory contains `manifest.txt`, `run_metadata.json`,
  `python-env.json`, `matrix/manifest.json`, `matrix/summary.json`,
  `matrix/scenario_summary.json`, `comparison_summary.json`,
  `case_seed_summary.json`, `case_seed_summary.csv`, and `artifact_gate.json`.

Machine-executable gate:

```bash
python tools/benchmark_carrier/verify_semantic_merge_artifact.py \
  .sage/benchmarks/real_online_semantic_merge/20260718T-smr-hardcases-3seed-5a8419e \
  --endpoint-metadata \
  .sage/benchmarks/real_online_semantic_mapreduce/20260718T-smr-multiseed-endpoint-5a8419e/metadata.json
```

Anonymous package and recheck:

```bash
python tools/benchmark_carrier/package_semantic_merge_artifact.py \
  --comparison-dir .sage/benchmarks/real_online_semantic_merge/20260718T-smr-hardcases-3seed-5a8419e \
  --endpoint-dir .sage/benchmarks/real_online_semantic_mapreduce/20260718T-smr-multiseed-endpoint-5a8419e \
  --output-dir .sage/benchmarks/submission_semantic_mapreduce/20260718T-smr-hardcases-3seed-5a8419e-anonymous \
  --archive .sage/benchmarks/semantic-mapreduce-3seed-real-online-5a8419e-anonymous.tar.gz
python tools/benchmark_carrier/verify_semantic_merge_artifact.py \
  .sage/benchmarks/submission_semantic_mapreduce/20260718T-smr-hardcases-3seed-5a8419e-anonymous/comparison \
  --endpoint-metadata \
  .sage/benchmarks/submission_semantic_mapreduce/20260718T-smr-hardcases-3seed-5a8419e-anonymous/endpoint/metadata.json
```

Fail criteria:

- Dirty parent commit, missing manifest fields, or missing submodule provenance.
- Any validated action fallback or invalid action/schema output.
- Action-validated F1 not above `hybrid-hint` on the three-hardcase aggregate.
- Accepted edits cite evidence that fails the validator.
