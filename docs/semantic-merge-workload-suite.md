# Semantic-Merge Workload Suite

This suite complements the large-scale telemetry workload in
`docs/large-scale-analysis-workload.md`. The original workload evaluates
whether shard-level evidence can be reduced into incident hypotheses. This
suite isolates a harder question: can a reducer turn symptom fragments into
incident-level semantic groups under different operational conditions?

The suite is still synthetic. Its role is to provide a controlled benchmark
axis for reducer development, not to replace production trace replay.

## Research Question

Given structured evidence objects from sharded telemetry, can a reducer recover
the incident unit: root service, region, time overlap, affected services, and
supporting evidence links?

This is a semantic-reduction problem rather than a scan or windowing problem.
The same evidence, reducers, scorer, and trace schema are reused across all
scenarios so that changes in quality can be attributed to reducer behavior.

## Operator-Algebra View

The suite is organized around the Semantic MapReduce operator model:

```text
Shard -> MapEvidence -> Normalize -> GroupEvidence
      -> SemanticReduce -> Edit -> Validate -> ReportTrace
```

The first four operators determine whether enough evidence reaches the reducer.
The reducer families then test different implementations of
`SemanticReduce`, `Edit`, and `Validate`. In particular, the latest action
reducers intentionally avoid asking the model to generate complete reducer
JSON. The model only implements the `Edit` decision over a candidate pair by
selecting `KEEP`, `MERGE`, `SPLIT`, or `ABSTAIN`; the system binds evidence
IDs, assembles the edit payload, validates root/affected/schema invariants, and
falls back if the edit is unsafe. This is the mechanism under test, not a
prompt-only variation.

## Scenario Families

| Scenario | Role | What It Tests |
| --- | --- | --- |
| `single-service` | Sanity / control | Local alert-style reducers should be able to recover simple incidents. |
| `cascade` | Realistic semantic merge | One root service creates downstream symptoms in dependent services. |
| `shared-bottleneck` | Resource contention | Multiple services show symptoms from a shared queue/cache/resource pressure. |
| `concurrent` | Stress / separation | Independent incidents overlap in time or region and should not be merged. |
| `false-correlation` | Negative control | Temporally correlated symptoms should not become a shared-root incident. |
| `partial-evidence` | Hard semantic inference | Direct root evidence is missing; only downstream evidence and upstream hints remain. |
| `ambiguous-overmerge` | Split / adjudication stress | Related overlapping incidents collapse into one graph candidate; a safe reducer must split only with evidence-bounded edits. |
| `ambiguous-disconnected-merge` | Merge / weak-topology stress | The same upstream incident appears through weakly connected service fragments; a safe reducer must merge only when evidence hints and incident IDs agree. |
| `ambiguous-temporal-split` | Merge / temporal fragmentation stress | One incident appears as separated evidence bursts; a safe reducer must join fragments without inventing unsupported time or service coverage. |

These families intentionally include both easy and hard cases. `single-service`
checks that local reducers can win when the incident unit is local; the harder
families then isolate the specific semantic-reduction challenges that require
graph structure, hints, validated edits, or split operations.

## Reducers

| Reducer | Role |
| --- | --- |
| `map-only` | Emits each local evidence object as an alert. |
| `service-local` | Groups evidence by service and region, approximating local alert correlation. |
| `window-aggregate` | Groups evidence by region and coarse time window. |
| `semantic-graph` | Uses service dependencies, overlap, score, and hints to produce incident groups. |
| `hybrid-hint` | Extends graph groups with explicit upstream root hints for missing-root evidence cases. |
| `llm-stub` | Exercises the reducer interface while delegating to `semantic-graph`. |
| `llm-hybrid` | OpenAI-compatible candidate editor: first runs `semantic-graph`, then asks the model to keep, drop, edit, or split compact incident candidates. |
| `llm-hybrid-validated` | Candidate editor with schema validation, evidence/hint consistency checks, unsafe-drop suppression, and `hybrid-hint` fallback. |
| `llm-pairwise` | OpenAI-compatible pairwise editor: proposes compact candidate pairs and asks for bounded merge/keep/split decisions. |
| `llm-pairwise-validated` | Pairwise editor with schema validation, evidence-reference checks, and fallback. |
| `llm-pairwise-action` | One-token action classifier: the model selects only `KEEP`, `MERGE`, `SPLIT`, or `ABSTAIN`; the system assembles legal edit JSON. |
| `llm-pairwise-action-validated` | Validated one-token action classifier with root/affected/evidence/schema checks and fallback. |
| `llm-openai` | OpenAI-compatible live reducer path for NPU or remote model endpoints. |

The `llm-stub` row must not be reported as a real LLM result. It is an
interface and CI placeholder. The `llm-hybrid` contract supports bounded
`split` and `merge` edits over graph candidates; the validated path only
accepts edits that preserve referenced evidence and pass schema,
root/affected-service, evidence-reference, and no-regression checks. The
`llm-hybrid-validated` reducer is the preferred live LLM path for strong
experiments because it bounds model context to candidate hypotheses and
prevents invalid model edits from regressing below the deterministic hybrid
fallback.

The pairwise action reducers narrow the interface further. They do not ask the
model to generate a reducer JSON object. Instead, the model answers with one
enumerated action for each proposed pair, and the reducer constructs the
schema-compliant edit payload. This design treats structured-output instability
as a reducer-interface problem rather than a prompt-tuning issue.

## Metrics

- `precision`: fraction of detected hypotheses that match an injected incident.
- `recall`: fraction of injected incidents recovered.
- `f1`: harmonic mean of precision and recall.
- `evidence_coverage`: fraction of injected incidents with at least one source
  evidence object.
- `root_evidence_coverage`: fraction of injected incidents whose source
  evidence includes the true root service.
- `support_evidence_recall`: fraction of source evidence IDs cited by matched
  detected hypotheses.
- `detected_incident_count`: report load after reduction.
- `reduce_duration_ms`: reducer latency over compact evidence objects.
- `missed_incidents`: ground-truth incidents not matched by any hypothesis.
- `false_positive_incidents`: hypotheses that do not match ground truth.
- `workflow_trace`: operator sequence, evidence objects, dependency graph, and
  evidence links.

The scorer requires root-service match, region match, time overlap, and enough
affected-service overlap. This makes symptom fragments different from incident
hypotheses.

## Reproduction

Run a single scenario:

```bash
PYTHONPATH=src python tools/benchmark_carrier/run_semantic_merge_workload.py \
  --scenario cascade \
  --seed 7 \
  --reducer semantic-graph \
  --output /tmp/semantic-merge-cascade.json
```

Run the full offline matrix:

```bash
PYTHONPATH=src python tools/benchmark_carrier/run_semantic_merge_matrix.py \
  --run-id 20260709T-semantic-merge-suite-with-ambiguous-overmerge-10seed
```

The matrix defaults to:

- seeds: `7,11,13,17,19,23,29,31,37,41`
- scenarios: all nine scenario families
- reducers: `map-only,service-local,window-aggregate,semantic-graph,hybrid-hint,llm-stub`

Artifacts are written under:

```text
.sage/benchmarks/semantic_merge_analysis/<run-id>/
```

Each run directory contains raw JSON reports, `summary.csv`, `summary.json`,
`scenario_summary.csv`, `scenario_summary.json`, `aggregate.json`, and
`manifest.json`.

## Current Offline Baseline

Artifact:

```text
.sage/benchmarks/semantic_merge_analysis/20260709T-semantic-merge-suite-with-ambiguous-overmerge-10seed/
```

Seven-scenario, ten-seed aggregate:

| Reducer | Precision | Recall | F1 | Detections |
| --- | ---: | ---: | ---: | ---: |
| `map-only` | 0.0667 | 0.1429 | 0.0906 | 14.33 |
| `service-local` | 0.0685 | 0.1429 | 0.0922 | 13.46 |
| `window-aggregate` | 0.3457 | 0.6929 | 0.4531 | 8.07 |
| `semantic-graph` | 0.7907 | 0.7643 | 0.7696 | 3.93 |
| `hybrid-hint` | 0.8367 | 0.8143 | 0.8173 | 3.93 |
| `llm-stub` | 0.7907 | 0.7643 | 0.7696 | 3.93 |

Scenario-level mean F1:

| Scenario | Map-only | Window-aggregate | Semantic-graph | Hybrid-hint |
| --- | ---: | ---: | ---: | ---: |
| `single-service` | 0.6345 | 0.4803 | 0.7143 | 0.7143 |
| `cascade` | 0.0000 | 0.4738 | 0.9143 | 0.9143 |
| `shared-bottleneck` | 0.0000 | 0.5316 | 0.8667 | 0.8889 |
| `concurrent` | 0.0000 | 0.5051 | 0.7964 | 0.7964 |
| `false-correlation` | 0.0000 | 0.5101 | 0.8050 | 0.8050 |
| `partial-evidence` | 0.0000 | 0.4288 | 0.5761 | 0.8878 |
| `ambiguous-overmerge` | 0.0000 | 0.2417 | 0.7143 | 0.7143 |

`hybrid-hint` preserves `semantic-graph` results on most scenarios and improves
`partial-evidence` from 0.5761 to 0.8878 mean F1 by adding the inferred
upstream root service to the affected-service set when the direct root evidence
is missing. This is a deterministic hybrid baseline, not an LLM result.

Interpretation:

- The suite supports the claim that incident-level semantic reduction differs
  from map-only alerts and coarse window aggregation.
- It shows why live LLM reducers need a guarded contract before they can be
  compared as quality-improving semantic operators.
- `partial-evidence` shows why a hybrid reducer is useful: the graph heuristic
  leaves substantial quality headroom, and a small hint-aware rule recovers much
  of it without changing the evidence schema or scorer.
- `ambiguous-overmerge` shows a different reducer challenge: the evidence is
  covered, but related incidents can be over-compressed into one candidate.
  This motivates a split-capable candidate-edit contract with validation rather
  than a generic "ask the LLM to reduce everything" prompt.

## Next Extensions

1. Extend the `llm-hybrid-validated` comparison beyond the current three-scenario
   matrix only after accepted model edits are expected to beat `hybrid-hint`
   rather than merely falling back safely.
2. Add a production-trace replay scenario once real vLLM-HUST/NPU telemetry is
   available.
3. Compare full-evidence LLM reduction against candidate-level LLM adjudication
   to test whether first-class semantic candidates reduce token/latency cost
   without losing quality.

Already implemented in the current artifact:

- `llm-hybrid` starts from `semantic-graph` candidates and asks an
  OpenAI-compatible model only to keep, edit, drop, or split compact
  hypotheses.
- `llm-hybrid-validated` adds schema validation, evidence/hint consistency,
  unsafe-drop suppression, and no-regression fallback to `hybrid-hint`.
- `manifest.json` records the command arguments, conda environment, Python
  executable, parent-repo git commit, branch, and dirty status.
- Each report records `reducer_trace`, `workflow_trace`, and
  `cost_accounting`.
- Missed incidents include a failure taxonomy such as missing map evidence,
  reducer under-merge/filtering, wrong root, incomplete affected services, or
  duplicate/matching conflict.
- False positives include a taxonomy for distractor evidence, over-merged
  incidents, or unmatched incident fragments.

## 2026-07-10 Ambiguous Candidate Stress

The stress extension asks a narrower question than the original seven-scenario matrix:
can accepted model edits improve hard semantic merge cases once evidence
coverage is already sufficient?

Offline smoke artifact:

```text
.sage/benchmarks/semantic_merge_analysis/20260710T-ambiguous-stress-offline-smoke/
```

The three stress cases all have evidence coverage 1.0. The deterministic
reducers still leave headroom:

| Reducer | Precision | Recall | F1 | Support recall |
| --- | ---: | ---: | ---: | ---: |
| `semantic-graph` | 0.3810 | 0.3333 | 0.3463 | 0.4167 |
| `hybrid-hint` | 0.6349 | 0.9167 | 0.6948 | 0.6528 |
| `llm-stub` | 0.3810 | 0.3333 | 0.3463 | 0.4167 |

Unit tests fix the intended contract behavior with mocked model outputs: an
evidence-preserving `merge` payload on `ambiguous-disconnected-merge` can raise
the validated path to F1 1.0 without inventing evidence, just as the existing
split test does for `ambiguous-overmerge`.

Real-online NPU3 artifact:

```text
.sage/benchmarks/real_online_semantic_merge/20260710T-npu3-ambiguous-candidate-stress/
```

All rows use the same seed, evidence schema, scorer, endpoint, and
Qwen2.5-7B model. The result is intentionally not reported as a quality win:

| Reducer | Precision | Recall | F1 | Support recall | Tokens | Fallback | Invalid schema |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `semantic-graph` | 0.3810 | 0.3333 | 0.3463 | 0.4167 | 0.0 | 0.0000 | 0 |
| `hybrid-hint` | 0.6349 | 0.9167 | 0.6948 | 0.6528 | 0.0 | 0.0000 | 0 |
| `llm-hybrid` | 0.2143 | 0.1667 | 0.1717 | 0.1667 | 1141.0 | 0.6667 | 2 |
| `llm-hybrid-validated` | 0.6349 | 0.9167 | 0.6948 | 0.6528 | 1070.3 | 1.0000 | 3 |
| `llm-openai` | 0.6667 | 0.1667 | 0.2667 | 0.2917 | 794.7 | 0.0000 | 0 |

Interpretation: coverage is sufficient, but the live accepted-edit path is not
yet stable. Follow-up probes isolate the failure mode. With structured-output
mode, the model often returns `{}` or legal keep/edit payloads without the
needed merge; with the expanded merge-hint prompt or without structured-output
mode, the model can produce non-JSON text. The validated reducer is therefore
doing the right systems job today: preserve the deterministic hybrid output,
record invalid edits and fallbacks, and expose the next bottleneck as
structured-output readiness plus candidate compression rather than map
coverage.

The next experiment should not simply add seeds. It should first shrink the
candidate-edit interface, for example by proposing deterministic merge pairs
and asking the model for a constrained accept/reject decision with evidence
IDs, then rerun this same stress suite.

## 2026-07-10 Constrained Pairwise Probe

The next probe implements that narrower interface as `llm-pairwise` and
`llm-pairwise-validated`. Instead of asking the model to rewrite complete
hypotheses, the reducer proposes short candidate pairs and asks for one of
`merge`, `keep`, or `split`, plus evidence IDs and a short reason. The reducer
then turns accepted `merge` decisions into evidence-preserving hypothesis
merges and validates evidence references.

Artifacts:

```text
.sage/benchmarks/real_online_semantic_merge/20260710T-npu3-pairwise-constrained-hardcases/
.sage/benchmarks/real_online_semantic_merge/20260710T-npu3-pairwise-constrained-v2-hardcases/
.sage/benchmarks/real_online_semantic_merge/20260710T-npu3-pairwise-validated-retry-disconnected/
```

Key result from the v2 probe:

| Scenario | Reducer | F1 | Accepted merges | Fallback | Invalid schema | Tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `ambiguous-disconnected-merge` | `hybrid-hint` | 0.7273 | 0 | 0 | 0 | 0 |
| `ambiguous-disconnected-merge` | `llm-pairwise` | 1.0000 | 3 | 0 | 0 | 530 |
| `ambiguous-disconnected-merge` | `llm-pairwise-validated` | 0.7273 | 0 | 1 | 1 | 483 |
| `ambiguous-temporal-split` | `hybrid-hint` | 0.5000 | 0 | 0 | 0 | 0 |
| `ambiguous-temporal-split` | `llm-pairwise` | 0.0000 | 0 | 1 | 1 | 888 |
| `ambiguous-temporal-split` | `llm-pairwise-validated` | 0.5000 | 0 | 1 | 1 | 777 |

Interpretation: constrained pairwise editing materially improves the model
interface. On `ambiguous-disconnected-merge`, the live raw pairwise reducer
returns legal JSON, accepts three evidence-preserving merges, and reaches F1
1.0 where `hybrid-hint` reaches 0.7273. This is the first live accepted-edit
gain in the suite. It is not yet a robust validated win: independent
`llm-pairwise-validated` calls still fall back because the model sometimes
returns malformed JSON or a JSON object without the required `decisions` list,
even after one retry. On `ambiguous-temporal-split`, pairwise proposals remain
insufficient and the model either emits incomplete decisions or falls back.

Failure taxonomy for this round:

- `output_format`: validated pairwise outputs can omit the required
  `decisions` list or produce non-JSON text.
- `candidate_representation`: the pairwise v2 prompt fixes the earlier
  "different services" misclassification for one disconnected-merge case, but
  temporal fragmentation still needs a better proposal surface.
- `evidence`: evidence coverage is 1.0, so the failures are not map-stage
  misses.
- `model_capability`: the same endpoint can emit a correct raw pairwise merge
  and an invalid validated response on neighboring calls. This motivated the
  one-token action probe below, which removes free-form JSON generation from
  the model-facing interface.

## 2026-07-10 One-Token Pairwise Action Probe

The next probe implements the narrower interface above as
`llm-pairwise-action` and `llm-pairwise-action-validated`. The model no longer
generates a JSON object. For each deterministic pair proposal, it must answer
with exactly one action token: `KEEP`, `MERGE`, `SPLIT`, or `ABSTAIN`. The
runtime then assembles the edit payload, copies evidence IDs from the pair
proposal, and runs the same schema, evidence-reference, root/affected-service,
and fallback validators.

Artifact:

```text
.sage/benchmarks/real_online_semantic_merge/20260710T-npu3-pairwise-action-hardcases/
.sage/benchmarks/real_online_semantic_merge/20260710T-npu3-pairwise-action-v2-hardcases/
```

The v2 run uses the project-specific `esage-vllm-hust-dev` conda environment,
a single NPU3 Qwen2.5-7B endpoint, seed 7, the repo-local semantic-merge
workload, and the same evidence schema and scorer as the earlier pairwise
probes. The parent repository and `third_party/ascend-runtime-manager` were
dirty during this development run, so the numbers should be rerun from a clean
commit before camera-ready submission. They are still useful mechanism evidence
because the raw reports contain endpoint, model, submodule, trace, token,
fallback, invalid-action, and validation metadata.

Aggregate over `ambiguous-disconnected-merge`, `ambiguous-temporal-split`, and
`ambiguous-overmerge`:

| Reducer | Precision | Recall | F1 | Support recall | Reduce ms | Tokens | Accepted edits | Fallback | Invalid action | Invalid schema |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `semantic-graph` | 0.3810 | 0.3333 | 0.3463 | 0.4167 | 0.59 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| `hybrid-hint` | 0.6349 | 0.9167 | 0.6948 | 0.6528 | 0.26 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| `llm-pairwise` | 0.3810 | 0.3333 | 0.3463 | 0.4167 | 911.48 | 506.7 | 0.0 | 1.0 | 0.0 | 3 |
| `llm-pairwise-validated` | 0.6349 | 0.9167 | 0.6948 | 0.6528 | 841.94 | 506.7 | 0.0 | 1.0 | 0.0 | 3 |
| `llm-pairwise-action` | 0.8889 | 0.9167 | 0.8857 | 0.9444 | 729.29 | 534.0 | 2.3333 | 0.0 | 0.0 | 0 |
| `llm-pairwise-action-validated` | 0.8889 | 0.9167 | 0.8857 | 0.9444 | 723.74 | 534.0 | 2.3333 | 0.0 | 0.0 | 0 |

Per-scenario validated action results:

| Scenario | Hybrid F1 | Action-validated F1 | Accepted merges | Fallback | Invalid action | Invalid schema | Tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ambiguous-disconnected-merge` | 0.7273 | 1.0000 | 3 | 0 | 0 | 0 | 483 |
| `ambiguous-temporal-split` | 0.5000 | 0.8000 | 4 | 0 | 0 | 0 | 950 |
| `ambiguous-overmerge` | 0.8571 | 0.8571 | 0 | 0 | 0 | 0 | 169 |

Interpretation: this run moves the mechanism from "safe fallback" to accepted
validated edits on covered hard cases. The old free-form pairwise prompt still
fails the schema contract in all three cases. The one-token action interface
removes that failure mode: the model emits only enum actions, the system
assembles legal edits, and validators accept evidence-preserving merges without
fallback. On `ambiguous-disconnected-merge`, the validated action path reaches
F1 1.0. On `ambiguous-temporal-split`, it improves F1 from 0.5000 to 0.8000
but still over-reports two hypotheses, so temporal candidate proposal remains a
reducer challenge rather than a solved problem. On `ambiguous-overmerge`, the
model returns `ABSTAIN`, the system keeps the baseline hypotheses, and quality
does not regress.

The raw `reducer_trace.metadata.action_trace` confirms the interface boundary.
For `ambiguous-disconnected-merge`, the endpoint returned three `MERGE` tokens;
`edit_trace` then records three system-assembled merge edits, and
`validation_trace` records `schema_valid=true`, `fallback_count=0`,
`repair_count=0`, and `accepted_edit_count=3`.

Failure taxonomy for this round:

- `output_format`: fixed for the action interface in this run. Free-form
  pairwise JSON still has invalid schema in all three cases; action reducers
  have zero invalid action and zero invalid schema.
- `candidate_representation`: still the main weakness for
  `ambiguous-temporal-split`. The model merges proposed pairs, but the pair
  proposal surface still leaves too many final hypotheses.
- `evidence`: evidence coverage is 1.0, so the remaining temporal miss is not a
  map-stage coverage failure.
- `action_granularity`: `KEEP/MERGE/SPLIT/ABSTAIN` is sufficient for the
  disconnected merge and abstention over overmerge, but temporal fragmentation
  may need higher-level multi-pair grouping or transitive-closure constraints.
- `validator`: not the blocker in this run. No validator rejection or fallback
  occurs for action-validated outputs.

## 2026-07-09 Real-Online Matrix

A small single-seed NPU3 matrix compares `semantic-graph`, `hybrid-hint`,
`llm-hybrid`, `llm-hybrid-validated`, and full-evidence `llm-openai` on three
hard semantic-merge cases:

```text
.sage/benchmarks/real_online_semantic_merge/20260709T161819Z-npu3-qwen25-7b-validated-smoke/
```

| Scenario | Graph F1 | Hybrid F1 | LLM-hybrid F1 | Validated F1 | Full LLM F1 | Validated/full support recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `partial-evidence` | 0.5000 | 1.0000 | 0.6667 | 1.0000 | 0.4000 | 1.0000 / 0.2500 |
| `false-correlation` | 0.7500 | 0.7500 | 0.7500 | 0.7500 | 0.4000 | 0.7500 / 0.2500 |
| `ambiguous-overmerge` | 0.8571 | 0.8571 | 1.0000 | 0.8571 | 0.4000 | 1.0000 / 0.2500 |

Interpretation: this matrix turns live LLM reducer behavior into a systems
mechanism. Candidate-level validation prevents schema or unsafe-edit violations
from degrading below the deterministic hybrid fallback, while a full-evidence
prompt returns too few incidents and cites only 25% of source evidence on these
cases. Raw candidate editing exposes both sides of the mechanism: it can repair
an over-merged graph candidate on `ambiguous-overmerge`, but it can also add an
extra fragment on `partial-evidence`. The validated path records invalid-schema
outputs, falls back to the deterministic hybrid reducer, and makes the rejected
model behavior auditable.
