# Semantic MapReduce Claim Ledger

This ledger keeps the paper draft aligned with what the repository currently
implements and measures. It is intentionally conservative for double-blind
systems submission preparation.

## Supported Claims

| Claim | Evidence in repository | Allowed wording |
| --- | --- | --- |
| The prototype implements a MapReduce-like semantic orchestration pipeline. | `src/sage/workloads/large_scale_analysis.py` defines `Shard`, `MapEvidence`, `Normalize`, `GroupEvidence`, `SemanticReduce`, and `ReportTrace` operator names, shard-level summaries, reducer variants, and evidence-linked reports. | "implements", "demonstrates", "supports the abstraction in the workload" |
| The workload evaluates incident-level evidence reduction over large event streams. | Synthetic NPU-backed LLM serving telemetry generator, injected incidents, common scorer, missed/detected incidents, and workflow trace output. | "evaluates shard-level evidence extraction and incident-level reduction" |
| Diagnostic baselines isolate reducer behavior. | `map-only`, `window-aggregate`, `deterministic`, and `llm-stub` share the same generator and scorer. | "diagnostic baselines", "isolate the value of grouping and incident reduction" |
| The current reproducible quality baseline is deterministic. | Matrix artifacts under `.sage/benchmarks/large_scale_analysis/20260702T-map-policy-10seed-thr098-paper-matrix/`. | "deterministic reducer baseline" |
| The LLM reducer path is pluggable and OpenAI-compatible. | `OpenAICompletionIncidentReducer`, structured-output schema, evidence-id normalization, coverage repair, and CLI flags. | "provides an interface", "is ready for real-online comparison" |
| Reports carry audit-oriented metadata. | `reducer_trace`, `workflow_trace`, `cost_accounting`, detected/missed incident fields in workload reports. | "records", "emits", "makes auditable in the artifact" |
| Trace-driven failure analysis can distinguish evidence failures from reducer failures. | Missed incidents now include `failure_type`, overlapping candidate counts, and best overlapping candidates. The 50k/seed23 miss is classified as an evidence extraction failure under `tail-aware`. | "classifies reducer misses", "identifies missing map evidence" |
| Coverage sweeps identify whether a reducer comparison is well-posed. | `tools/benchmark_carrier/run_large_scale_analysis_coverage_sweep.py` measures how many injected incidents are present in shard-level evidence before reducer comparison. Artifact `.sage/benchmarks/large_scale_analysis_coverage/20260708T-coverage-10seed-paper/` shows `2000/4` tail-aware mean/min coverage of 0.3000/0.0000, while `10000/8` baseline-aware reaches mean/min coverage 1.0000/1.0000. | "uses a coverage gate", "separates evidence extraction failures from reducer failures" |
| A baseline-aware evidence policy fixes low-baseline service latency misses in the current workload. | `.sage/benchmarks/large_scale_analysis/20260708T-baseline-aware-10seed-paper-matrix/` shows baseline-aware deterministic reaches mean precision/recall/F1 of 1.0 across 20 deterministic runs, while map-only and window-aggregate remain much lower. | "improves this workload", "recovers hard low-baseline incidents" |
| A semantic-merge workload suite exposes several gaps between alert fragments, window aggregation, and incident hypotheses. | `src/sage/workloads/semantic_merge_analysis.py` and `.sage/benchmarks/semantic_merge_analysis/20260709T-semantic-merge-suite-with-ambiguous-overmerge-10seed/` evaluate `single-service`, `cascade`, `shared-bottleneck`, `concurrent`, `false-correlation`, `partial-evidence`, and `ambiguous-overmerge` scenarios. Semantic-graph reaches 0.7696 mean F1 versus 0.0906 for map-only, 0.0922 for service-local, and 0.4531 for window aggregation. | "introduces a representative semantic-merge suite", "shows incident-group reduction is distinct from alert aggregation across multiple workload families" |
| A hint-aware hybrid reducer repairs a missing-root-evidence failure mode in the semantic-merge suite. | The `hybrid-hint` reducer adds upstream root hints into the affected-service set. On `partial-evidence`, mean F1 improves from 0.5761 for `semantic-graph` to 0.8878 without changing the evidence schema or scorer. | "a deterministic hybrid reducer addresses one failure mode", "partial-evidence improves under hint-aware semantic reduction" |
| A split/merge-capable candidate-edit contract is implemented for ambiguous semantic candidates. | The `ambiguous-overmerge` scenario creates overlapping related incidents that can collapse into one graph candidate, while `ambiguous-disconnected-merge` and `ambiguous-temporal-split` create covered incident evidence that deterministic graph/hybrid reducers fragment. The candidate-edit contract supports bounded `split` and `merge` edits. Unit tests verify that evidence-bounded split and evidence-preserving merge payloads can recover F1/support-evidence recall of 1.0 on mocked hard cases. | "implements bounded candidate editing", "unit tests show the contract can express split and merge operations that deterministic reducers miss" |
| A candidate-level LLM hybrid reducer is implemented and measured for the semantic-merge suite. | `OpenAIHybridMergeReducer` first runs `semantic-graph`, then asks an OpenAI-compatible model to keep, drop, edit, or split compact incident candidates. Artifact `.sage/benchmarks/real_online_semantic_merge/20260709T161819Z-npu3-qwen25-7b-validated-smoke/` compares `semantic-graph`, `hybrid-hint`, `llm-hybrid`, `llm-hybrid-validated`, and `llm-openai` on the same NPU3 endpoint, seed, evidence objects, and scorer. The run uses `qwen25-7b-instruct`, structured-output readiness, explicit `/data` container mount, and eager fallback after graph-fusion readiness exposed a missing `libopapi` symbol. | "implements and measures candidate adjudication", "small real-online matrix" |
| A validated candidate editor turns live LLM reducer instability into an enforceable system contract. | `OpenAIHybridValidatedMergeReducer` validates candidate edits, suppresses unsafe drops by default, repairs evidence/hint consistency, and falls back to `hybrid-hint` on invalid schema. In the NPU3 smoke, `llm-hybrid-validated` matches `hybrid-hint` mean F1 0.8690 while recording invalid-schema responses and one fallback per hard case. Full-evidence `llm-openai` returns legal JSON but emits too few incidents, with F1 0.4000 and support-evidence recall 0.2500 on all three cases. Raw `llm-hybrid` shows both opportunity and risk: it improves ambiguous-overmerge F1 from 0.8571 to 1.0000 by splitting a candidate, but drops partial-evidence F1 from 1.0000 to 0.6667 by adding an extra fragment. | "validation makes model edits auditable and rejectable", "full-evidence prompting exposes why bounded candidate editing is needed", "guarded reduction rather than raw prompting" |
| Ambiguous-candidate stress cases distinguish evidence coverage from model output-contract readiness. | `.sage/benchmarks/semantic_merge_analysis/20260710T-ambiguous-stress-offline-smoke/` shows three stress scenarios have evidence coverage 1.0 while `semantic-graph` averages 0.3463 F1 and `hybrid-hint` averages 0.6948 F1. `.sage/benchmarks/real_online_semantic_merge/20260710T-npu3-ambiguous-candidate-stress/` reruns those cases on the NPU3 Qwen endpoint: `llm-openai` reaches 0.2667 F1, raw `llm-hybrid` reaches 0.1717 F1 with invalid schema in 2/3 runs, and `llm-hybrid-validated` preserves the 0.6948 hybrid baseline by falling back in all runs. Follow-up probes show the model can produce legal keep/edit payloads without the needed merge, `{}` under structured-output mode, or non-JSON output when the prompt is expanded. These probes motivate the one-token action interface used in the clean replay. | "coverage can be sufficient while the model-facing contract is wrong", "the system contribution is constraining semantic edits into a validated action interface" |
| A constrained pairwise edit interface can produce live evidence-preserving merge gains on a covered hard case. | `OpenAIPairwiseMergeReducer` presents short candidate pairs and asks only for `merge`/`keep`/`split` decisions with evidence IDs. `test_openai_pairwise_validated_reducer_accepts_constrained_merge` verifies the validated path accepts evidence-preserving pair merges under a mocked response. In `.sage/benchmarks/real_online_semantic_merge/20260710T-npu3-pairwise-constrained-v2-hardcases/`, raw `llm-pairwise` on `ambiguous-disconnected-merge` returns legal JSON, accepts three merge decisions, and improves F1 from the `hybrid-hint` baseline 0.7273 to 1.0000 with 530 estimated tokens. The same run still fails on `ambiguous-temporal-split`, and the independent `llm-pairwise-validated` calls fall back because their model outputs do not contain the required `decisions` list. This intermediate result is superseded by the one-token action replay for the final validated mechanism claim. | "constrained pairwise editing can produce accepted live merge edits on at least one covered hard case", "free-form pairwise JSON motivates bounded action classification" |
| One-token pairwise action classification converts LLM output instability into validated reducer edits. | `OpenAIPairwiseActionMergeReducer` and `OpenAIPairwiseActionValidatedMergeReducer` ask the model only for `KEEP`, `MERGE`, `SPLIT`, or `ABSTAIN`; the runtime assembles legal JSON edits and applies the same schema/root/affected/evidence validators. Invalid action text is fail-closed to `ABSTAIN` and counted. `test_openai_pairwise_action_validated_reducer_assembles_legal_edits` verifies mocked action edits recover `ambiguous-disconnected-merge` to F1 1.0, and `test_openai_pairwise_action_invalid_output_abstains_without_fallback` verifies invalid action text does not trigger global fallback. In the clean real-online replay `.sage/benchmarks/real_online_semantic_merge/clean-pairwise-action-hardcases-c3d4dfa/`, `llm-pairwise-action-validated` improves the three-hardcase mean F1 from 0.6948 (`hybrid-hint`) to 0.8857, records zero fallbacks, zero invalid-schema runs, and zero invalid-action outputs, and accepts 2.3333 edits on average. Per-case F1 is 1.0000 on `ambiguous-disconnected-merge`, 0.8000 on `ambiguous-temporal-split`, and 0.8571 on `ambiguous-overmerge` where it abstains and preserves baseline quality. The artifact records parent `git.dirty=false`, `evidence_label=real-online`, the NPU3 endpoint/model/env, and clean runtime/workload submodule provenance. | "one-token action classification removes the free-form JSON failure mode in a clean single-seed real-online hardcase replay", "validated pairwise action edits can improve covered ambiguous merge cases under the same scorer", "invalid model text becomes bounded action uncertainty rather than reducer failure" |
| Semantic-merge reports include reproducibility and failure-diagnosis metadata. | The `20260709T-semantic-merge-suite-with-ambiguous-overmerge-10seed` artifact records `manifest.json`, reducer traces, cost accounting, missed-incident failure classes, and false-positive classes for each raw JSON report. | "records run provenance", "classifies missed and false-positive hypotheses" |
| Public replay candidates have been source-probed. | `.sage/benchmarks/public_semantic_mapreduce_sources/20260708T-public-source-probe/` probes AIOps Challenge 2020, LO2, OpenTelemetry Demo, DeathStarBench, and the Illinois/FIRM trace page. Four are reachable at the metadata/repository level; Illinois returned HTTP 403 to the automated probe. | "source-level probe", "candidate public replay sources", "source-provenance artifact" |
| Shared LLM-serving workloads are part of the formal artifact surface. | `third_party/llm-serving-workloads` is a pinned submodule at `79ed8e3469c0bcfccdf1cd0a66efa2db27156055`. `tools/benchmark_carrier/run_shared_llm_serving_workload_probe.py` records shared workload generation provenance. Artifact `.sage/benchmarks/shared_llm_serving_workloads/20260708T-shared-workload-probe-3seed/` covers 23 generated cases per seed and 1,232 supported requests per seed across seeds 7/11/13. | "uses shared workload-source provenance", "separates shared serving workload probes from repo-local Semantic MR mechanism workloads" |
| The coverage sweep now reuses one map stage across reducer variants. | `run_large_scale_analysis_coverage_sweep.py` generates/shards/maps once per config, then runs multiple reducers over the same `ShardSummary` evidence objects. Offline suite smoke coverage stage dropped from about 2.18s to 0.67s for the same small config after the change. | "reuses evidence objects across reducer variants", "models the system benefit of a first-class evidence stage" |

## Challenge Claims Requiring More Evidence

| Claim | Current status | Required before stronger wording |
| --- | --- | --- |
| Live LLM-backed reduction improves beyond the strongest deterministic/hybrid reducer across seeds and broader suites. | Not claimed. The one-token action validated path improves a clean three-hardcase, single-seed NPU3 replay from 0.6948 to 0.8857 mean F1 with zero invalid actions, zero invalid schema, and zero fallback, but this is not yet a multi-seed or broader-suite result. | Add more seeds and hardcase families, and show the accepted-edit path remains above `hybrid-hint` without increasing false positives on easier scenarios. |
| Live LLM-backed reduction provides a quality-cost/latency advantage. | The action-classification path now improves quality in a small live replay while adding about 534 estimated tokens and about 326 ms mean reduce latency. This is a mechanism improvement, not yet a frontier claim. | Add candidate compression, batched pair judging, and accepted-edit-only ablations before claiming a quality-cost frontier. |
| Full-evidence prompting is sufficient for semantic reduction. | Refuted by the current hard cases. `llm-openai` returns legal JSON but emits one incident per case, giving F1 0.4000 and support-evidence recall 0.2500 despite full evidence coverage. | Keep full-evidence prompting as a negative control, not as the target mechanism. |
| The approach works over production telemetry. | The current main benchmark uses controlled synthetic telemetry grounded in LLM-serving signals; public and shared workload probes establish source/provenance surfaces but not production reducer quality. | Run on real vLLM-HUST/NPU telemetry or a production-derived trace with provenance. |
| Reducer quality holds on public datasets. | Public sources have been probed for availability and integration fit; no dataset-specific loader/scorer has been run yet. | Add dataset-specific loaders and scorer mappings, then run the same reducer matrix. |
| External engines can execute the lower-level scans/shards. | Adapter probes show wrappers can drive the same contract; no tuned distributed Spark/Flink/Ray deployment is claimed. | Integrate a real Spark/Ray/Flink backend and measure orchestration overhead and data movement. |
| Monetary cost accounting is complete. | Offline reducers report zero-token fields; LLM reducer records provider usage when available or chars/4 estimates otherwise. | Add provider-specific pricing config and vendor-specific billing metadata before claiming dollar-level cost. |

## Do Not Claim

- The system replaces Spark, Flink, Ray, databases, or vector systems.
- The prototype has production-grade distributed shuffle or exactly-once fault
  tolerance for this workload.
- Raw or full-evidence LLM prompting already beats deterministic/hybrid baselines.
- The 2026-07-08 or 2026-07-09 real-online LLM reducer runs show a quality-cost advantage.
- Adapter-level wrapper results are SOTA system comparisons.
- NPU3 sanity probes are broad serving-performance measurements.

## Implementation-Layer Boundary

The Semantic MapReduce claims in this package are implemented at the
orchestration and reducer-contract layer: evidence schemas, candidate
compression, bounded `Edit` actions, system-owned `Validate`, fallback,
token/latency accounting, and trace emission. The final clean replay does not
require any new Ascend kernel, Triton operator, mask/packing primitive, or
runtime-operator semantic change.

If a future reducer or validator depends on lower-level operator semantics,
that change must be developed in the pinned `external/triton-ascend-hust`
submodule on its project feature branch. `external/vllm-ascend-hust` should
remain thin integration glue for Ascend execution, while `external/vllm-hust`
owns scheduler, KV-lifecycle, request-metadata, and cleanup behavior. Runtime,
container, CANN, torch_npu, device-mount, and dev-hub management changes belong
in `third_party/ascend-runtime-manager` or the pinned dev-hub submodule, not in
an external shared checkout.

## Related-Work Positioning

| System family | What it is strong at | Boundary for this paper | Wording discipline |
| --- | --- | --- | --- |
| Hadoop MapReduce / Spark / Flink | Distributed execution, scan/join/aggregate, streaming state, fault tolerance. | They are substrate engines; semantic incident fusion and evidence-linked explanation are outside their core abstraction. | "complementary execution substrates" |
| Ray | General distributed Python execution and actor/task scheduling. | Useful for running shards; not itself a semantic reduce contract with auditable evidence objects. | "can carry tasks, but does not define this semantic contract" |
| LangChain / LangGraph | Agent/workflow composition and tool orchestration. | Strong for agent workflows; large-scale dataflow, reducer baselines, and data-system integration are not the center of the comparison here. | "related orchestration frameworks; adapter probes are diagnostic" |
| LlamaIndex | Connectors, indexing, RAG-oriented retrieval/data access. | Evidence retrieval is related, but the paper studies incident-level semantic reduction over sharded telemetry. | "connector/RAG substrate rather than the full runtime target" |
| AutoGen / Microsoft Agent Framework | Multi-agent conversation and coordination. | Multi-agent semantics differ from shard evidence aggregation and workflow trace over data pipelines. | "related multi-agent orchestration" |
| Databricks/Snowflake Cortex/BigQuery ML | Integrated data+AI platform services. | Strong production integrations; the paper emphasizes an open orchestration layer and evidence/reducer contract. | "platform integrations; further systematic comparison needed" |

These comparisons need citation checks before submission. The current repository
does not contain a full related-work survey.

## Benchmark Table Boundary

| Reducer | Role | LLM call? | Paper use |
| --- | --- | ---: | --- |
| `map-only` | Emits shard-local candidates without global incident fusion. | No | Shows why local anomaly surfacing creates duplicates and low precision. |
| `window-aggregate` | Deduplicates by service/region/window only. | No | Shows the value and limit of window grouping before incident-level reduction. |
| `deterministic` | Reproducible incident reducer baseline. | No | Main current quality baseline. |
| `llm-stub` | Interface/CI placeholder that reuses deterministic fusion. | No | Validates pluggability only; quality identical by design. |
| `llm-hybrid` | Real OpenAI-compatible candidate editor over semantic-graph hypotheses, including bounded split edits. | Yes | Measured in the small live matrix; exposes why split edits need evidence and affected-service validation. |
| `llm-hybrid-validated` | Candidate editor with schema validation, evidence/hint consistency checks, unsafe-drop suppression, and `hybrid-hint` fallback. | Yes | Supports the guarded-reduction mechanism in the small NPU3 matrix by making unsafe model edits rejectable. |
| `llm-pairwise` | Real OpenAI-compatible pairwise editor over compact candidate pairs. | Yes | Shows that narrowing the model output surface can produce a live accepted merge, but free-form JSON remains unstable. |
| `llm-pairwise-action-validated` | One-token pairwise action classifier; the model emits an enum and the system assembles validated edits. | Yes | Supports the constrained-edit-interface claim in the three-hardcase NPU3 probe. |
| `llm-openai` | Real OpenAI-compatible full-evidence semantic reducer. | Yes | Negative control for raw prompting; lower support-evidence recall on the small NPU3 matrix. |

## 2026-07-08/09 NPU3 Evidence Update

Current evidence-chain interpretation:

1. `llm-serving-workloads` probe records shared LLM-serving scenario structure
   and provenance, but not reducer quality.
2. Coverage gate measures whether the repo-local Semantic MR map stage surfaces
   enough evidence for reducer comparison.
3. Reducer matrices compare local/window/semantic reducers only after the map
   evidence question is visible.
4. NPU3 real-online smoke validates live LLM reducer paths, latency, token
   accounting, trace, and cleanup. The 2k large-scale run's low recall is
   explained by low map coverage, illustrating why coverage gates must precede
   reducer quality claims.
5. The 2026-07-09 semantic-merge live matrix tests what happens after evidence
   coverage is sufficient: raw model edits can help or hurt, while validation
   makes unsafe edits auditable and rejectable.
6. The clean pairwise-action replay narrows model output to one enumerated
   action per candidate pair. In the three-hardcase seed-7 run,
   `llm-pairwise-action-validated` improves mean F1 from 0.6948 to 0.8857,
   records zero invalid actions, zero invalid-schema runs, and zero fallback.
   This supports the constrained reducer-interface mechanism with clean
   provenance; the remaining boundary is single-seed scope, not a clean
   evidence blocker.

Additional one-command real-online smoke:

```text
.sage/benchmarks/real_online_semantic_mapreduce/20260708T-npu3-script-smoke/
```

This run launched vLLM-HUST through the repository-pinned dev-hub submodule on
NPU3, used the project-specific `esage-vllm-hust-dev` client environment, and
then stopped the endpoint. The streaming probe reported 8/8 successful
requests, mean TTFT 65.68 ms, mean TPOT 19.79 ms, and 45.71 completion
tokens/s. The 2k `llm-openai` workload produced precision 1.0, recall 0.25,
F1 0.4, and 432 total reducer tokens.

Interpretation: this is real-online path evidence, not reducer-quality
evidence. The paired coverage sweep shows the same `2000/4` tail-aware setting
only placed one of four injected incidents into map evidence, so three misses
were upstream of semantic reduction.

Real-online endpoint provenance:

```text
.sage/benchmarks/real_online_semantic_mapreduce/20260708T-npu3-smr-fair-baseline-server/
```

The endpoint was launched through the repository-pinned dev-hub submodule on
NPU3 with the project-specific `esage-vllm-hust-dev` conda environment for
client-side scripts. Smoke and streaming probes succeeded.

Fair reducer comparisons:

| artifact | map policy | workload | reducer result |
| --- | --- | --- | --- |
| `20260708T-npu3-fair-reducer-20k-seed7` | tail-aware | 20k / 8 shards / seed 7 | deterministic and `llm-openai` both F1=1.0; LLM adds 53.46s SemanticReduce and 1,148 tokens. |
| `20260708T-npu3-fair-reducer-50k-seed23` | tail-aware | 50k / 16 shards / seed 23 | both reducers miss `incident-3`; trace shows no overlapping map evidence, so the failure is upstream of semantic reduction. |
| `20260708T-npu3-fair-reducer-50k-seed23-baseline-aware` | baseline-aware | 50k / 16 shards / seed 23 | initial LLM run failed context budgeting: 1,281 input tokens + 768 requested output tokens exceeded 2048. |
| `20260708T-npu3-fair-reducer-50k-seed23-baseline-aware-t384` | baseline-aware | 50k / 16 shards / seed 23 | deterministic and `llm-openai` both F1=1.0; LLM adds 5.81s SemanticReduce and 1,683 tokens. |

Offline 10-seed evidence-policy matrix:

```text
.sage/benchmarks/large_scale_analysis/20260708T-baseline-aware-10seed-paper-matrix/
```

Aggregate result over two sizes and ten seeds:

| reducer | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: |
| map-only | 0.2260 | 0.7875 | 0.3500 |
| window-aggregate | 0.4693 | 1.0000 | 0.6366 |
| deterministic | 1.0000 | 1.0000 | 1.0000 |
| llm-stub | 1.0000 | 1.0000 | 1.0000 |

Interpretation: the evidence-backed claim strengthened today is that an
auditable Semantic MapReduce harness exposes whether a quality change comes
from map evidence, semantic reduction, or model execution. Baseline-aware
evidence extraction fixes a real low-baseline-service challenge in the current
workload. The next LLM mechanism should target hard semantic-merge cases where
accepted model edits can improve beyond deterministic clustering under the same
validator.

## Semantic-Merge Workload Suite

The repository now includes a separate workload suite for the next LLM-reducer
claim:

```text
src/sage/workloads/semantic_merge_analysis.py
tools/benchmark_carrier/run_semantic_merge_workload.py
tools/benchmark_carrier/run_semantic_merge_matrix.py
.sage/benchmarks/semantic_merge_analysis/20260709T-semantic-merge-suite-with-ambiguous-overmerge-10seed/
```

The current suite covers seven workload families:

- `single-service`: sanity check for local alert-style incidents.
- `cascade`: root causes with downstream symptoms.
- `shared-bottleneck`: common resource or queue pressure.
- `concurrent`: temporally overlapping independent incidents.
- `false-correlation`: unrelated symptoms that should not be over-merged.
- `partial-evidence`: missing root evidence with downstream symptoms and
  upstream hints.
- `ambiguous-overmerge`: overlapping related incidents that expose whether a
  reducer can safely split an over-compressed candidate.

The scorer requires the predicted hypothesis to recover the root service,
region, overlapping time, and enough affected services. This makes
map-only/service-local reducers fail on incident-group scenarios because they
emit symptom fragments, while `single-service` verifies that the benchmark is
not constructed to make local reducers always fail.

10-seed, seven-scenario aggregate:

| reducer | mean precision | mean recall | mean F1 | mean detections |
| --- | ---: | ---: | ---: | ---: |
| map-only | 0.0667 | 0.1429 | 0.0906 | 14.33 |
| service-local | 0.0685 | 0.1429 | 0.0922 | 13.46 |
| window-aggregate | 0.3457 | 0.6929 | 0.4531 | 8.07 |
| semantic-graph | 0.7907 | 0.7643 | 0.7696 | 3.93 |
| hybrid-hint | 0.8367 | 0.8143 | 0.8173 | 3.93 |
| llm-stub | 0.7907 | 0.7643 | 0.7696 | 3.93 |

Scenario-level mean F1:

| scenario | map-only | window-aggregate | semantic-graph | hybrid-hint |
| --- | ---: | ---: | ---: | ---: |
| single-service | 0.6345 | 0.4803 | 0.7143 | 0.7143 |
| cascade | 0.0000 | 0.4738 | 0.9143 | 0.9143 |
| shared-bottleneck | 0.0000 | 0.5316 | 0.8667 | 0.8889 |
| concurrent | 0.0000 | 0.5051 | 0.7964 | 0.7964 |
| false-correlation | 0.0000 | 0.5101 | 0.8050 | 0.8050 |
| partial-evidence | 0.0000 | 0.4288 | 0.5761 | 0.8878 |
| ambiguous-overmerge | 0.0000 | 0.2417 | 0.7143 | 0.7143 |

Interpretation: this suite better motivates the semantic-reduce abstraction
than the original single-service incident workload alone. It also shows that a
specific failure mode can be fixed at the reducer contract: adding upstream
root hints to affected services improves `partial-evidence` from 0.5761 to
0.8878 mean F1. The `ambiguous-overmerge` family adds a second failure mode:
evidence coverage is complete, but the graph candidate can be too coarse and
needs a safe split operation. The live semantic-merge matrix
`.sage/benchmarks/real_online_semantic_merge/20260709T161819Z-npu3-qwen25-7b-validated-smoke/`
adds real LLM reducers for three hard cases under one endpoint, one seed, one
evidence schema, and one scorer. Full-evidence `llm-openai` reaches only
0.4000 F1 on each case. Raw `llm-hybrid` shows why candidate editing is the
right surface but cannot be trusted without guards: it improves
`ambiguous-overmerge` from 0.8571 to 1.0000 by splitting a graph candidate, yet
regresses `partial-evidence` from 1.0000 to 0.6667 by adding an extra fragment.
`llm-hybrid-validated` records invalid schema outputs and one fallback per hard
case, matching the hybrid baseline mean F1 of 0.8690. The result turns live LLM
instability into a system contract: coverage-gated candidate edits must pass
schema, evidence-reference, root/affected, and no-regression validation before
they become incident hypotheses.

## Adapter Comparison Boundary

The adapter comparison fixes generator, evidence schema, reducer, and scorer.
Therefore identical quality across SAGE-local, LangGraph-local, LlamaIndex, and
Ray-local wrappers is expected. The result should motivate the abstraction:
external substrates can transport the computation, while the missing piece is
first-class semantic reduction and auditable evidence. It should not be framed
as proof that one wrapper is semantically better than another.

## NPU3 Real-Online Follow-up Checklist

The small NPU3 semantic-merge comparison has been recorded. Before any stronger
quality claim:

1. Start vLLM-HUST through `external/vllm-hust-dev-hub/manage.sh` on NPU3.
2. Confirm `/health` on the configured OpenAI-compatible endpoint.
3. Rerun the semantic-merge comparison with more seeds only after accepted
   candidate edits are expected to beat `hybrid-hint`, not merely fall back.
4. For the large-scale workload, run:

   ```bash
   ALLOW_NPU3_REAL_ONLINE=1 \
   SAGE_LSA_LLM_BASE_URL=http://127.0.0.1:18383 \
   SAGE_LSA_LLM_MODEL=<served-model-name> \
   tools/benchmark_carrier/run_npu3_llm_reducer_comparison.sh
   ```

5. For the semantic-merge suite, run
   `tools/benchmark_carrier/run_npu3_semantic_merge_llm_comparison.sh` with
   `semantic-graph`, `hybrid-hint`, `llm-hybrid`, `llm-hybrid-validated`, and
   `llm-openai` on the same seeds, scenarios, evidence objects, and scorer.
6. Report precision, recall, F1, coverage, support-evidence recall,
   `SemanticReduce` latency, token counts, candidate-edit traces, estimated
   cost, and raw workflow trace paths.
7. The next multi-seed run should report whether accepted validated edits
   improve over `hybrid-hint` under the same scorer and evidence contract.
