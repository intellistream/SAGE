# Semantic MapReduce Readiness Report

This report summarizes the current ASPLOS-readiness state for the Semantic
MapReduce paper draft. It separates supported claims from mechanism probes and
keeps real-online evidence provenance explicit.

## Latest Hardcase Result

Clean replay artifact:

```text
.sage/benchmarks/real_online_semantic_merge/clean-pairwise-action-hardcases-c3d4dfa/
```

Artifact package:

```text
.sage/benchmarks/real_online_semantic_merge/clean-pairwise-action-hardcases-c3d4dfa.tar.gz
sha256: 80eb03e4d3e735ce46b5b1fff7cb79e323fb7be37ebbd0cdf86f395b35fd6d30
```

The `.sage/` tree is ignored by git, so the raw clean replay should be attached
as a separate artifact package rather than committed to the paper branch.

Provenance:

- Evidence label: `real-online`
- Endpoint: `http://127.0.0.1:18383`
- Model: `qwen25-7b-sage-realonline`
- Hardware: NPU3, Ascend 910B2
- Conda env: `esage-vllm-hust-dev`
- Clean replay parent commit: `c3d4dfa79638a59432da8424175aed9339abafb5`
- Paper package commit: any later paper-only synchronization commit that
  preserves this clean replay artifact and result table.
- Parent dirty: `false`
- `third_party/llm-serving-workloads`: `79ed8e3469c0bcfccdf1cd0a66efa2db27156055`
- `third_party/ascend-runtime-manager`: `c5b0461aaecffe7e5011f8fab0944d32bedb1092`, clean
- Workload source: repo-local `src/sage/workloads/semantic_merge_analysis.py`
- Scenarios: `ambiguous-disconnected-merge`, `ambiguous-temporal-split`, `ambiguous-overmerge`
- Seed: `7`

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
trace capture. This is the central abstraction that should carry the ASPLOS
paper narrative.

Three-hardcase aggregate:

| Reducer | Precision | Recall | F1 | Support recall | Tokens | Accepted edits | Fallback | Invalid action | Invalid schema |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `semantic-graph` | 0.3810 | 0.3333 | 0.3463 | 0.4167 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| `hybrid-hint` | 0.6349 | 0.9167 | 0.6948 | 0.6528 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| `llm-pairwise` | 0.3810 | 0.3333 | 0.3463 | 0.4167 | 506.7 | 0.0 | 1.0 | 0.0 | 3 |
| `llm-pairwise-validated` | 0.6349 | 0.9167 | 0.6948 | 0.6528 | 506.7 | 0.0 | 1.0 | 0.0 | 3 |
| `llm-pairwise-action` | 0.8889 | 0.9167 | 0.8857 | 0.9444 | 534.0 | 2.3333 | 0.0 | 0.0 | 0 |
| `llm-pairwise-action-validated` | 0.8889 | 0.9167 | 0.8857 | 0.9444 | 534.0 | 2.3333 | 0.0 | 0.0 | 0 |

Per-case action-validated outcomes:

| Scenario | Hybrid F1 | Action-validated F1 | Accepted merges | Main interpretation |
| --- | ---: | ---: | ---: | --- |
| `ambiguous-disconnected-merge` | 0.7273 | 1.0000 | 3 | Succeeds: validated merge edits repair fragmented incident evidence. |
| `ambiguous-temporal-split` | 0.5000 | 0.8000 | 4 | Partial success: evidence is present and edits are valid, but pair proposal still over-reports. |
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
- Model semantic ability: the model can make useful bounded merge decisions
  when the pair proposal exposes the right relation; it is not yet proven
  robust across seeds.
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
output. A single-seed real-online hardcase probe shows this design can accept
validated merge edits and improve over `hybrid-hint` on covered ambiguous merge
cases.

## Current Final State

- Paper narrative has been updated around the `Semantic MapReduce Operator
  Model`.
- A new operator-algebra figure shows the model-facing boundary at `Edit`,
  while `Validate`, trace generation, and fallback remain system-owned.
- The action reducer is written as an `Edit` + `Validate` instance, not as a
  prompt-engineering trick.
- The current PDF compiles to 11 total pages in the local ACM-style draft, with
  references beginning on page 11. The operator figure and hardcase table have
  been visually checked for overlap/overflow.
- No-NPU regression tests pass under `esage-vllm-hust-dev`:
  `29 passed` for the semantic-merge and large-scale-analysis workload tests.
- The three-hardcase NPU3 clean replay passes the artifact gate: F1 0.8857,
  zero fallback, zero invalid schema, zero invalid action, single seed, clean
  parent commit.
- Implementation-layer boundary is explicit: the submitted Semantic MapReduce
  mechanism does not require new Ascend kernel, Triton operator, mask/packing,
  or runtime-operator semantic changes. If future work needs such behavior, it
  must land in the pinned `external/triton-ascend-hust` feature branch rather
  than as an ad hoc `vllm-ascend-hust` workaround; `vllm-ascend-hust` remains
  thin glue, and `vllm-hust` owns scheduler/KV/request-metadata concerns.
- No additional NPU run is required for the current submission package unless
  the paper is upgraded to make multi-seed live robustness claims.

## Claims Not Yet Supported

- Do not claim broad multi-seed robustness for live LLM-backed reduction.
- Do not claim a quality-cost frontier; the action reducer still adds roughly
  534 estimated tokens and 326 ms mean reduce latency in the small live probe.
- Do not claim production trace generality; the current mechanism suite is
  repo-local and controlled.
- Do not claim that this replaces Spark, Flink, Ray, databases, LangGraph, or
  LlamaIndex.
- Do not claim that validators prove the LLM is always useful; validators make
  model edits auditable, rejectable, and fallback-safe.

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

READY for the current single-seed mechanism claim. The clean replay has passed.
The remaining useful next experiment is optional strengthening, not a blocker:

1. Run a minimal multi-seed hardcase sweep across
   `ambiguous-disconnected-merge`, `ambiguous-temporal-split`, and
   `ambiguous-overmerge`.
2. Report per-case accepted edit count, fallback count, invalid action/schema,
   token cost, latency, support evidence recall, and failure taxonomy.

## Clean Replay Artifact Gate

The gate below has been run successfully for
`.sage/benchmarks/real_online_semantic_merge/clean-pairwise-action-hardcases-c3d4dfa/`.
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
SEEDS=7 \
SCENARIOS=ambiguous-disconnected-merge,ambiguous-temporal-split,ambiguous-overmerge \
REDUCERS=semantic-graph,hybrid-hint,llm-pairwise,llm-pairwise-validated,llm-pairwise-action,llm-pairwise-action-validated \
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

Pass criteria for keeping the current mechanism claim at "clean single-seed
real-online result":

- `llm-pairwise-action-validated` has `fallback=0`, `invalid action=0`, and
  `invalid schema=0` over the three hardcases.
- Mean F1 for `llm-pairwise-action-validated` is greater than `hybrid-hint`
  under the same scorer.
- `ambiguous-disconnected-merge` reaches F1 1.0 with at least one accepted
  evidence-preserving merge edit.
- `ambiguous-overmerge` does not regress below `hybrid-hint`.
- The result directory contains `manifest.txt`, `run_metadata.json`,
  `python-env.json`, `matrix/manifest.json`, `matrix/summary.json`,
  `matrix/scenario_summary.json`, and `comparison_summary.json`.

Fail criteria:

- Dirty parent commit, missing manifest fields, or missing submodule provenance.
- Any validated action fallback or invalid action/schema output.
- Action-validated F1 not above `hybrid-hint` on the three-hardcase aggregate.
- Accepted edits cite evidence that fails the validator.
