# Semantic MapReduce Claim Ledger

## 2026-07-19 Active Claim Boundary

This section supersedes the older submission-preparation entries below.

| Claim | Current direct evidence | Allowed wording |
| --- | --- | --- |
| Runtime v2 implements finite, typed, executable KEEP/MERGE/SPLIT/ABSTAIN proposals with ID-only selection and atomic validation/commit. | `src/sage/workloads/semantic_reduce_edit_runtime.py`, `bounded-edit-runtime-contract.md`, and adversarial/property/replay tests. | “implements and tests true cataloged SPLIT offline”, “evidence-conserving atomic Edit runtime” |
| Deterministic and mock model-policy selectors receive byte-identical H0/catalog input. | Clean development and held-out matrices plus focused tests; the mock selector invokes no endpoint/model. | “shared-catalog policy harness”, “offline policy-emulator mechanism check” |
| The difficult workload axes are controlled `simulation/model`, with hidden labels restricted to generation/scoring. | Frozen held-out matrix: 40 units, 36 oracle repairs, improving merge/split proposals in 29/14 units, and all offline gates pass. | “controlled held-out ambiguity axes”, “proposal-coverage diagnostic”; never “model gain” |
| Runtime recovery uses an independently supplied pre-failure checkpoint rather than current live state. | Clean 27-row runtime matrix: 27 state-changing commits, invalid-edit rejections, baseline preservations, checkpoint restores, independent-checkpoint checks, and deterministic replays. | “model-free supplied-checkpoint recovery”; not distributed exactly-once |
| Historical action online evidence validates accepted merges and bounded rejection only. | Frozen 2026-07-18 artifact; legacy verifier PASS; all historical `split_count` values are zero. | “historical merge-only bounded-action result”, “accepted merge repairs semantic-graph grouping” |
| Constrained agglomerative is a strong broader-permission reference. | Clean 90-unit controlled matrix: 0.9287; matched 27-unit value: 0.9028. | “full-evidence controlled reference”, “not a shared-H0 edit peer or published SOTA” |
| A v2 real-online experiment is frozen and independently request-ready, but unexecuted. | Protocol SHA `33b48e86...a6ba83d`, execution `fc0978d`, and three exact-SHA SIGN envelopes; no central grant or online rows. | “three-reviewer-signed frozen protocol”, “request-only reservation readiness”; never “v2 real-online result” |

Forbidden until new direct evidence exists: “v2 SPLIT is real-online,” “the
model beats the strongest deterministic policy,” “hybrid is the action pre-edit
state,” “0.9287 is external SOTA,” or “submission-ready.” The historical 27-unit
action-versus-constrained result is 3 wins, 15 ties, and 9 losses; all eight
units containing accepted legacy merges tie constrained.

Clean audit evidence is frozen under ignored `.sage/benchmarks` paths. The
held-out aggregate SHA-256 is
`b0e46955e43616e31714a55ba8a6d22257c234a363623893e3a24a25c97b8d46`.
The independently extractable anonymous archive has 1,329 manifest-covered
files and SHA-256
`0470ea7a43fb2b33cb4344b9097fb67d433b2f380830f296d8280340dd86e937`.

This ledger keeps the paper draft aligned with what the repository currently
implements and measures. It is intentionally conservative for double-blind
systems submission preparation.

## Supported Claims

| Claim | Evidence in repository | Allowed wording |
| --- | --- | --- |
| The legacy prototype implements a merge-only bounded semantic-reducer path; runtime v2 implements the complete finite proposal contract offline. | Legacy `semantic_merge_analysis.py` plus v2 `semantic_reduce_edit_runtime.py`; see the active boundary above. | "legacy merge-only online path", "v2 complete offline Edit runtime" |
| The workload evaluates incident-level evidence reduction over large event streams. | Synthetic NPU-backed LLM serving telemetry generator, injected incidents, common scorer, missed/detected incidents, and workflow trace output. | "evaluates shard-level evidence extraction and incident-level reduction" |
| Diagnostic baselines isolate reducer behavior. | `map-only`, `window-aggregate`, `deterministic`, and `llm-stub` share the same generator and scorer. | "diagnostic baselines", "isolate the value of grouping and incident reduction" |
| The current reproducible quality baseline is deterministic. | Matrix artifacts under `.sage/benchmarks/large_scale_analysis/20260702T-map-policy-10seed-thr098-paper-matrix/`. | "deterministic reducer baseline" |
| Representative 50K/100K scale checks record throughput and operator latency. | The seed-7 tail-aware deterministic reports `.sage/benchmarks/large_scale_analysis/20260702T-map-policy-10seed-thr098-paper-matrix/events50000_shards16_seed7_tail_aware_deterministic.json` and `events100000_shards32_seed7_tail_aware_deterministic.json` detect all four injected incidents at both scales. They report 105.8K and 101.6K events/s, 72.94 ms and 169.61 ms MapEvidence latency, and 0.35 ms and 0.31 ms SemanticReduce latency. | "representative scale/timing checks", "map evidence dominates local runtime while reduce over compact evidence is sub-millisecond in these runs" |
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
| One-token pairwise action classification converts LLM output instability into validated reducer edits. | `OpenAIPairwiseActionMergeReducer` and `OpenAIPairwiseActionValidatedMergeReducer` ask the model only for `KEEP`, `MERGE`, `SPLIT`, or `ABSTAIN`; the runtime assembles legal JSON edits and applies the same schema/root/affected/evidence validators. Invalid action text is fail-closed to `ABSTAIN` and counted. In `.sage/benchmarks/real_online_semantic_merge/20260718T-smr-hardcases-3seed-5a8419e/`, the validated action path improves mean F1 from 0.7204 (`hybrid-hint`) to 0.9301 over seeds 7/11/13 and three hardcases, with support recall 0.9815, 2.2222 accepted edits, zero fallback, and zero invalid action/schema. The free-form validated negative has invalid schema and fallback in all nine runs. Per-case/seed JSON/CSV and `artifact_gate.json` preserve failures, tokens, and latency. The endpoint and comparison manifests record clean parent/runtime/workload provenance, NPU3, model, environment, and evidence label. | "one-token action classification removes the free-form JSON failure mode across three controlled workload seeds", "validated pairwise action edits improve covered hardcases under the same scorer", "invalid model text becomes bounded action uncertainty rather than reducer failure" |
| Semantic-merge reports include reproducibility and failure-diagnosis metadata. | The `20260709T-semantic-merge-suite-with-ambiguous-overmerge-10seed` artifact records `manifest.json`, reducer traces, cost accounting, missed-incident failure classes, and false-positive classes for each raw JSON report. | "records run provenance", "classifies missed and false-positive hypotheses" |
| A public telemetry replay exercises the evidence boundary. | `.sage/benchmarks/aiops2020_public_replay/20260718T-may29-map-evidence-replay-v4/` reads the official AIOps Challenge 2020 May-29 daily ZIP and four fault labels in place, evaluates eight matched negative windows, and archives no raw data. It detects two fault windows with zero false positives (precision 1.0, recall 0.5, F1 0.6667). | "public-dataset replay at MapEvidence/Normalize", "two misses expose weak or missing evidence", "not incident-group reducer quality" |
| Runtime commit/reject/recovery is executable across the workload inventory. | `.sage/benchmarks/semantic_mapreduce_runtime_contract/20260719T-eurosys27-final-d5ba73d-clean/` covers nine families x seeds 7/11/13 from clean pushed commit `d5ba73d`. All 27 model-free rows pass valid commit, invalid-edit rejection, baseline preservation, checkpoint digest restore, and deterministic replay. The online path separately records compatible candidate/evidence/committed-state digests and outcomes. | "27-run derived runtime-contract matrix", "model-free checkpoint recovery preserves committed semantic state", "online traces record compatible state digests", "not distributed exactly-once FT" |
| Shared LLM-serving workloads are part of the formal artifact surface. | `third_party/llm-serving-workloads` is a pinned submodule at `79ed8e3469c0bcfccdf1cd0a66efa2db27156055`. `tools/benchmark_carrier/run_shared_llm_serving_workload_probe.py` records shared workload generation provenance. Artifact `.sage/benchmarks/shared_llm_serving_workloads/20260708T-shared-workload-probe-3seed/` covers 23 generated cases per seed and 1,232 supported requests per seed across seeds 7/11/13. | "uses shared workload-source provenance", "separates shared serving workload probes from repo-local Semantic MR mechanism workloads" |
| The coverage sweep now reuses one map stage across reducer variants. | `run_large_scale_analysis_coverage_sweep.py` generates/shards/maps once per config, then runs multiple reducers over the same `ShardSummary` evidence objects. Offline suite smoke coverage stage dropped from about 2.18s to 0.67s for the same small config after the change. | "reuses evidence objects across reducer variants", "models the system benefit of a first-class evidence stage" |

## Challenge Claims Requiring More Evidence

| Claim | Current status | Required before stronger wording |
| --- | --- | --- |
| Live LLM-backed reduction improves beyond the strongest hybrid reducer across the controlled workload inventory. | On the clean 7B matrix, action validation reaches F1 0.8645 versus 0.7801; a paired bootstrap over 27 scenario x seed means gives delta `+0.0844`, 95% CI `[0.0328,0.1449]`. On the same-family 14B checkpoint, F1 is 0.8392 versus 0.7801, delta `+0.0591`, CI `[0.0147,0.1149]`. The 14B run retains 243/243 raw reports and zero unsafe credential files. | Keep wording to two checkpoints in one model family, temperature zero, and controlled telemetry; do not claim cross-family or production robustness. |
| Live LLM-backed reduction provides a quality-cost/latency advantage. | The controlled 7B budgets 4/8/12 reach action F1 0.7791/0.8645/0.8571. At budget 8 the action path calls the model on 65/135 rows; conditional median latency is 160.0 ms and mean provider tokens are 541.8 with 65/65 provider-usage coverage. The 14B action path calls on 39/81 rows, with 276.2 ms and 542.3 provider tokens. | This is a measured operating boundary and call-conditioned reducer cost, not a general frontier, monetary cost, or end-to-end serving speedup. |
| Repeated-sampling and second-scale stability have been measured. | The 7B budget-8 matrix has 135 action rows, zero within-case F1 standard deviation, and mean exact action agreement 0.9926. The 14B matrix has 81 action rows, zero within-case F1 standard deviation, 0.9877 mean exact action agreement, two unparsable responses mapped to `ABSTAIN`/no-op, zero validator rejection, zero schema invalid, and zero fallback. Raw responses, provider envelopes, sample IDs, timestamps, request failures, replay IDs, and state digests are retained. | Supports repeatability at temperature zero and a same-family scale check; do not infer cross-family or broad stochastic robustness. |
| Token cost is measured rather than estimated. | New action traces retain provider usage and aggregate it when available; older artifacts and endpoints without usage retain the explicit `char-estimate` label. | Say "provider-reported tokens" only for rows whose `token_measurement_source` is `provider-usage`; otherwise say "estimated tokens." |
| Full-evidence prompting is sufficient for semantic reduction. | Refuted by the current hard cases. `llm-openai` returns legal JSON but emits one incident per case, giving F1 0.4000 and support-evidence recall 0.2500 despite full evidence coverage. | Keep full-evidence prompting as a negative control, not as the target mechanism. |
| The approach works over production telemetry. | The current main benchmark uses controlled synthetic telemetry grounded in LLM-serving signals; public and shared workload probes establish source/provenance surfaces but not production reducer quality. | Run on real vLLM-HUST/NPU telemetry or a production-derived trace with provenance. |
| Reducer grouping executes against public incident-episode ground truth. | The AIOpsArena complex-case replay converts 23 public injection rows into eight native episodes using dataset fields `(timestamp, service, failure_type, duration)`. Episode IDs are withheld from reducers. Map-only/window/service-local/semantic F1 is 0.5161/0.8000/1.0000/1.0000. Artifact evidence label is `replay`; scope is `reducer-only-label-conditioned`. | Allowed: "external incident-unit grouping replay." Not allowed: end-to-end detection, LLM generalization, or production robustness; MapEvidence is oracle/label-conditioned and there are only eight episodes. |
| The reducer contract executes over external public data. | `.sage/benchmarks/aiops2020_semantic_reduce_contract/20260718T-eurosys27-public-contract-e0ffdff-clean/` consumes only two replay-detected official AIOps windows at clean commit `e0ffdff`, commits bounded evidence-preserving edits, rejects a missing-evidence edit, preserves the baseline, records digests/replay ID, and replays deterministically. Evidence label: `replay`. | "external public-data contract conformance"; never "public reducer-quality generalization." |
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

The Semantic MapReduce claims in this package are implemented at a runtime-owned
reducer boundary: evidence schemas, candidate compression, bounded `Edit`
actions, system-owned `Validate`, commit/fallback, checkpoint metadata,
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
| LangChain / LangGraph | Agent/workflow composition and tool orchestration. | They can carry the graph; this paper studies evidence eligibility, finite edit authority, validator-owned commit/fallback, and replayable reducer state. | "related workflow substrates; adapter probes are diagnostic" |
| LlamaIndex | Connectors, indexing, RAG-oriented retrieval/data access. | Evidence retrieval is related, but the paper studies incident-level semantic reduction over sharded telemetry. | "connector/RAG substrate rather than the full runtime target" |
| AutoGen / Microsoft Agent Framework | Multi-agent conversation and coordination. | Multi-agent semantics differ from shard evidence aggregation and workflow trace over data pipelines. | "related multi-agent orchestration" |
| Databricks/Snowflake Cortex/BigQuery ML | Integrated data+AI platform services. | Strong production integrations; the paper isolates a portable runtime-owned reducer boundary rather than claiming a broader platform. | "platform integrations; further systematic comparison needed" |

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
| `llm-pairwise-action-validated` | One-token pairwise action classifier; the model emits an enum and the system assembles validated edits. | Yes | Main constrained-edit result across nine families x three seeds; the hardcase subset isolates merge/abstain behavior. |
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
6. The clean pairwise-action matrix narrows model output to one enumerated
   action per candidate pair. Across three hardcases and seeds 7/11/13,
   `llm-pairwise-action-validated` improves mean F1 from 0.7204 to 0.9301,
   reaches support recall 0.9815, and records zero invalid action/schema or
   fallback. This supports the constrained reducer-interface mechanism with
   clean endpoint, parent, environment, NPU3, and submodule provenance. The
   original diagnostic boundary is one model/endpoint and controlled telemetry;
   the later full-coverage five-sample matrix supersedes it for submission-facing
   quality and stability claims.

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
.sage/benchmarks/semantic_merge_analysis/20260718T-eurosys27-9family-10seed/
```

The current paper suite covers nine workload families:

- `single-service`: sanity check for local alert-style incidents.
- `cascade`: root causes with downstream symptoms.
- `shared-bottleneck`: common resource or queue pressure.
- `concurrent`: temporally overlapping independent incidents.
- `false-correlation`: unrelated symptoms that should not be over-merged.
- `partial-evidence`: missing root evidence with downstream symptoms and
  upstream hints.
- `ambiguous-overmerge`: overlapping related incidents that expose whether a
  reducer can safely split an over-compressed candidate.
- `ambiguous-disconnected-merge`: grouping fragments one incident and requires
  evidence-preserving merge edits.
- `ambiguous-temporal-split`: one incident spans candidate windows and tests
  temporal/transitive fusion.

The scorer requires the predicted hypothesis to recover the root service,
region, overlapping time, and enough affected services. This makes
map-only/service-local reducers fail on incident-group scenarios because they
emit symptom fragments, while `single-service` verifies that the benchmark is
not constructed to make local reducers always fail.

10-seed, nine-scenario aggregate (90 rows per reducer):

| reducer | mean precision | mean recall | mean F1 | mean detections |
| --- | ---: | ---: | ---: | ---: |
| map-only | 0.0519 | 0.1111 | 0.0705 | 13.97 |
| service-local | 0.0533 | 0.1111 | 0.0717 | 13.27 |
| window-aggregate | 0.3779 | 0.7444 | 0.4916 | 8.17 |
| semantic-graph | 0.6485 | 0.6639 | 0.6435 | 4.97 |
| hybrid-hint | 0.7585 | 0.8556 | 0.7796 | 4.97 |
| llm-stub | 0.6485 | 0.6639 | 0.6435 | 4.97 |

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
7. The three-workload-seed run reports accepted edits, fallback/invalid counts,
   tokens, latency, support recall, and failure taxonomy under the same scorer.
   The next strengthening step is broader/easy families or repeated models, not
   another undocumented seed-only rerun.
