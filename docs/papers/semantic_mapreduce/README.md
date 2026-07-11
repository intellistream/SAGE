# Semantic MapReduce Paper Draft

This directory contains the systems-conference LaTeX draft for the SAGE
large-scale analysis workload and Semantic MapReduce framing.

## Venue Choice

Recommended style target: **ASPLOS full paper**, with the submission story
centered on the systems evidence chain: evidence coverage, semantic reducer
contracts, validated model-backed edits, cost/latency accounting, and
auditable traces.

Rationale:

- The user asked for a traditional systems-conference long-paper target rather
  than an ML systems paper.
- ASPLOS is a closer fit than MLSys for the current framing because the paper
  emphasizes system abstraction, runtime/orchestration boundaries, workload
  design, and careful claim discipline around LLM-serving integration.
- The ASPLOS case is strongest when the paper reads as a systems-contract
  contribution: the hard part is not simply calling an LLM, but making
  semantic reduction explicit, validated, auditable, and comparable under one
  evidence schema and scorer.
- The draft currently follows the ACM `acmart` anonymous two-column form used
  by ASPLOS-style submissions. Page-count and anonymity details must be checked
  against the active CFP before submission.
- SOSP/OSDI remain plausible future targets after the prototype has a real
  LLM-backed reducer, real telemetry, stronger distributed execution evidence,
  and a deeper related-work comparison.

Template:

- `main.tex` uses the official ACM `acmart` class in the CFP-recommended form:
  `\documentclass[sigplan,10pt,anonymous]{acmart}`.
- The document enables page numbers with `\settopmatter{printfolios=true}` and
  uses `\pagestyle{plain}`.

## Build

From this directory:

```bash
tectonic main.tex
```

The generated PDF is:

```text
docs/papers/semantic_mapreduce/main.pdf
```

## Claim Discipline

Before changing the paper's claims or result language, update and check:

```text
docs/papers/semantic_mapreduce/claim-ledger.md
```

The current submission framing is:

- SAGE is an AI-native orchestration and semantic-reduction layer above or
  beside engines such as Spark, Flink, Ray, databases, and vector systems.
- The artifact supports shard-level map, evidence objects, reducer variants,
  missed-incident reporting, workflow trace, failure taxonomy, run manifests,
  and token/cost accounting fields.
- The deterministic reducer is the current reproducible quality baseline.
- `llm-stub` is a pluggability check only; it intentionally has the same
  quality as the deterministic reducer.
- Real `llm-openai` reducer runs on NPU3 validate the live reducer path,
  expose token/latency costs, and motivate the validated candidate-edit
  mechanism for constraining model omissions, over-merges, and schema errors.

## Experiment Artifact

### Coverage Gate

Reducer comparisons should first check whether injected incidents are present
in shard-level evidence objects. Use the coverage sweep before quality
comparisons:

```bash
PYTHONPATH=src python tools/benchmark_carrier/run_large_scale_analysis_coverage_sweep.py \
  --sizes '2000:4:8,10000:8:12,50000:16:12,100000:32:16' \
  --seeds '7,11,13,17,19,23,29,31,37,41' \
  --map-policies 'tail-aware,baseline-aware'
```

The sweep writes `manifest.json`, `summary.csv`, `summary.json`, per-config
coverage details, and `aggregate.json`. It records the repo-local workload
source and the pinned `third_party/llm-serving-workloads` commit. The current
10-seed paper artifact is:

```text
.sage/benchmarks/large_scale_analysis_coverage/20260708T-coverage-10seed-paper/
```

It shows why the NPU3 2k real-online run should not be used as a
reducer-quality claim: `2000/4` with `tail-aware` map evidence has mean
coverage `0.3000` and minimum coverage `0.0000`, whereas `10000/8` with
`baseline-aware` reaches mean/min coverage `1.0000`. At larger scales,
`baseline-aware` keeps coverage at `1.0000` across 50k and 100k, while
`tail-aware` still has occasional misses.

The paper currently reports the tail-aware slice of the reproduced matrix run
with diagnostic comparison baselines:

```text
.sage/benchmarks/large_scale_analysis/20260702T-map-policy-10seed-thr098-paper-matrix/
```

The run used the `esage-vllm-hust-dev` conda environment and includes:

- `summary.csv`
- `summary.json`
- `aggregate.json`
- raw JSON reports for each reducer/size/seed configuration

Current tail-aware reducer comparison from
`aggregate.json.by_map_policy_reducer`:

| reducer | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: |
| map-only | `0.1990` | `0.6875` | `0.3075` |
| window-aggregate | `0.5696` | `0.9750` | `0.7129` |
| deterministic | `0.9500` | `0.9750` | `0.9579` |
| llm-stub | `0.9500` | `0.9750` | `0.9579` |

The `llm-stub` reducer intentionally matches the deterministic reducer because
it is a CI-safe placeholder, not a real LLM experiment.

The map-only and window-aggregate rows are diagnostic baselines that isolate the
benefit of incident-level semantic reduction. They are not full external-system
SOTA comparisons.

Representative seed-7 scale/timing checks from the same artifact:

| events | shards | top-k | precision | recall | F1 | throughput events/s | map ms | reduce ms | detected |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 50,000 | 16 | 12 | `1.0000` | `1.0000` | `1.0000` | `105,804.39` | `72.94` | `0.35` | `4/4` |
| 100,000 | 32 | 16 | `1.0000` | `1.0000` | `1.0000` | `101,601.48` | `169.61` | `0.31` | `4/4` |

These two rows are scale/timing sanity checks, not replacements for the
ten-seed quality matrix. They show that map/evidence extraction dominates the
local runtime while deterministic semantic reduction over compact candidates is
sub-millisecond in these runs.

An additional baseline-aware evidence-policy matrix was recorded after the
2026-07-08 NPU3 real-online run:

```text
.sage/benchmarks/large_scale_analysis/20260708T-baseline-aware-10seed-paper-matrix/
```

This policy compares each service/region window against a shard-local robust
latency baseline. It fixes low-baseline latency spikes such as router incidents
that the tail-aware policy can miss because the absolute latency is small and
the incident raises both p95 and the window mean.

| reducer | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: |
| map-only | `0.2260` | `0.7875` | `0.3500` |
| window-aggregate | `0.4693` | `1.0000` | `0.6366` |
| deterministic | `1.0000` | `1.0000` | `1.0000` |
| llm-stub | `1.0000` | `1.0000` | `1.0000` |

This is evidence for trace-guided evidence extraction plus incident reduction.
Live LLM-backed reducer claims should be made through the separate validated
candidate-edit experiments that measure accepted edits, rejected edits,
fallbacks, tokens, and latency under the same scorer.

### Semantic-Merge Workload Suite

The repository also includes a semantic-merge workload suite for the next
reducer claim:

```bash
PYTHONPATH=src python tools/benchmark_carrier/run_semantic_merge_matrix.py \
  --run-id 20260709T-semantic-merge-suite-with-ambiguous-overmerge-10seed
```

Artifact:

```text
.sage/benchmarks/semantic_merge_analysis/20260709T-semantic-merge-suite-with-ambiguous-overmerge-10seed/
```

The suite contains seven scenario families:

- `single-service`: sanity check where local alert-style reducers can recover
  the incident unit.
- `cascade`: one root service produces symptoms in dependent services.
- `shared-bottleneck`: a resource or queue bottleneck affects multiple services.
- `concurrent`: independent incidents overlap in time and region.
- `false-correlation`: unrelated symptoms are temporally correlated and should
  not be over-merged.
- `partial-evidence`: direct root evidence is missing for some incidents, so
  the reducer must use downstream evidence and upstream hints.
- `ambiguous-overmerge`: overlapping related incidents collapse into one graph
  candidate, so a reducer needs a safe split operation rather than another
  root hint.

These scenarios keep the generator, evidence schema, reducer contract, and
scorer fixed while varying the semantic merge challenge. This is more
representative than a single cross-service case: it includes a traditional
sanity workload, realistic cascade/shared-bottleneck cases, and adversarial
over-merge, missing-evidence, and candidate-splitting cases.

| reducer | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: |
| map-only | `0.0667` | `0.1429` | `0.0906` |
| service-local | `0.0685` | `0.1429` | `0.0922` |
| window-aggregate | `0.3457` | `0.6929` | `0.4531` |
| semantic-graph | `0.7907` | `0.7643` | `0.7696` |
| hybrid-hint | `0.8367` | `0.8143` | `0.8173` |
| llm-stub | `0.7907` | `0.7643` | `0.7696` |

The `llm-openai`, `llm-hybrid`, and `llm-hybrid-validated` reducer interfaces
are implemented for this workload. `llm-openai` asks the model to regroup
selected evidence rows from scratch. `llm-hybrid` first runs `semantic-graph`,
then asks the model only to keep, drop, edit, split, or merge compact incident candidates.
`llm-hybrid-validated` adds schema validation, evidence/hint consistency
checks, unsafe-drop suppression, and no-regression fallback to `hybrid-hint`.
The `hybrid-hint` reducer improves `partial-evidence` from `0.5761` to
`0.8878` mean F1 by adding upstream root hints to affected-service hypotheses;
this is a deterministic hybrid result, not a live LLM result. The
`ambiguous-overmerge` family adds a complementary stress case: evidence
coverage is complete, but the graph reducer can over-compress two related
incidents into one candidate. The 2026-07-10 stress extension adds two
merge-oriented blind spots, `ambiguous-disconnected-merge` and
`ambiguous-temporal-split`, where evidence coverage is complete but deterministic
graph/hybrid reducers fragment the incident. The LLM candidate-edit contract
therefore supports bounded `split` and `merge` actions, and the validated path
only accepts edits that cite existing evidence and pass consistency checks.

The latest ambiguous-candidate stress artifacts are:

```text
.sage/benchmarks/semantic_merge_analysis/20260710T-ambiguous-stress-offline-smoke/
.sage/benchmarks/real_online_semantic_merge/20260710T-npu3-ambiguous-candidate-stress/
```

Current interpretation: the offline mocked contract proves that an accepted
evidence-preserving merge can repair a covered hard case, but the NPU3
Qwen2.5-7B live run did not yet produce stable accepted merge edits. The
validated reducer preserves the `hybrid-hint` baseline by falling back on
invalid schema, while raw model edits regress. Treat this as evidence for the
structured-output and candidate-compression challenge, not as an online quality
win.

The follow-up constrained pairwise probe narrows the interface further:

```text
.sage/benchmarks/real_online_semantic_merge/20260710T-npu3-pairwise-constrained-v2-hardcases/
.sage/benchmarks/real_online_semantic_merge/20260710T-npu3-pairwise-validated-retry-disconnected/
```

`llm-pairwise` asks the model only to judge short candidate pairs as
`merge`/`keep`/`split` with copied evidence IDs. On
`ambiguous-disconnected-merge`, the live raw pairwise path accepts three
evidence-preserving merges and improves F1 from `0.7273` for `hybrid-hint` to
`1.0000` with 530 estimated tokens. This is a live accepted-edit gain, but not
yet a robust validated claim: independent `llm-pairwise-validated` calls still
fall back because the model sometimes omits the required `decisions` list even
after one retry, and `ambiguous-temporal-split` remains unsolved.

Full workload-suite documentation:

```text
docs/semantic-merge-workload-suite.md
```

Public replay candidates are tracked separately:

```text
docs/semantic-mapreduce-public-data-candidates.md
```

Current public-source probe artifact:

```text
.sage/benchmarks/public_semantic_mapreduce_sources/20260708T-public-source-probe/
```

This is a source-availability and integration-fit probe, not a reducer-quality
replay result.

Shared workload provenance:

```text
third_party/llm-serving-workloads
```

Reusable serving workload families should come from this pinned submodule when
possible. SAGE-specific Semantic MapReduce stress, negative, and ablation
workloads remain repo-local. Experiment manifests record both the repo-local
workload path and the pinned `llm-serving-workloads` commit when present.

The current shared-workload probe is:

```text
.sage/benchmarks/shared_llm_serving_workloads/20260708T-shared-workload-probe-3seed/
```

It uses `third_party/llm-serving-workloads` at commit
`79ed8e3469c0bcfccdf1cd0a66efa2db27156055` and records 23 generated shared
cases per seed, 2 skipped public/boundary cases, and 1,232 supported requests
per seed. This is a shared workload-source and adapter/probe artifact, not a
Semantic MapReduce reducer-quality result.

### Evidence Chain

The current experiment chain is:

1. Shared workload probe: validates that the pinned
   `llm-serving-workloads` submodule can generate canonical LLM-serving cases
   with provenance, separately from SAGE repo-local Semantic MR workloads.
2. Coverage gate: checks whether injected incidents appear in MapEvidence
   objects. The 10-seed coverage sweep shows `2000/4` tail-aware coverage is
   too low for reducer claims, while `10000/8+` with baseline-aware evidence is
   fully covered in this workload.
3. Reducer comparison: once coverage is sufficient, compares `map-only`,
   `window-aggregate`, `deterministic`, and `llm-stub` under the same generator
   and scorer. Current quality evidence supports semantic incident reduction,
   not live LLM superiority.
4. Single-NPU real-online smoke: validates the OpenAI-compatible reducer path,
   token accounting, latency, trace, and cleanup behavior. The current 2k
   real-online large-scale run has low recall because evidence coverage was
   low, so it demonstrates why coverage gates are part of the reducer contract.
5. Candidate-edit validation: the semantic-merge live matrix shows that raw
   full-evidence prompting and unconstrained candidate edits are unreliable,
   while validated candidate editing can reject malformed or unsafe edits and
   preserve the deterministic hybrid baseline.

### Offline Suite Runner

Use the suite runner for non-NPU regression and paper-artifact checks:

```bash
conda run -n esage-vllm-hust-dev \
  env PYTHONPATH=src \
  python tools/benchmark_carrier/run_semantic_mapreduce_offline_suite.py \
    --run-id 20260708T-offline-suite-smoke \
    --profile smoke
```

The suite runs the shared-workload probe, public-source probe, coverage sweep,
large-scale analysis matrix, and semantic-merge matrix, then writes a top-level
`suite_metadata.json`:

```text
.sage/benchmarks/semantic_mapreduce_offline_suite/20260708T-offline-suite-smoke/
```

Use `--profile paper` only when intentionally rerunning the larger offline
matrices. This still has evidence label `derived-artifact` or
`simulation/model`; it is not a real-online serving experiment.

Use `--skip-coverage-sweep` only for fast local debugging. Paper-quality
reducer results should keep the coverage sweep enabled so evidence extraction
failures remain separate from reducer failures.

Use `--skip-shared-workload-probe` only when iterating on repo-local Semantic
MR logic. Full artifact runs should leave it enabled so the paper records both
shared workload provenance and SAGE-specific Semantic MR mechanism evidence.

Each workload report now records:

- `reducer_trace`: reducer contract, input candidate counts, output hypothesis
  counts, and reducer-specific metadata.
- `workflow_trace`: operator sequence, matched/missed incident ids, shard-level
  candidate trace, and detected-incident evidence links.
- `cost_accounting`: zero-token offline fields for deterministic reducers and
  provider/estimated token fields for real LLM reducers.
- missed/false-positive failure taxonomy: per-incident labels that distinguish
  weak map evidence, reducer under-merge/filtering, wrong roots, incomplete
  affected-service sets, distractor evidence, and over-merged fragments.
- `manifest.json`: run id, command arguments, conda environment, Python
  executable, parent commit, branch, and dirty status for the matrix run.

### Environment Setup

On vLLM-HUST machines, prepare the source environment through
the SAGE-pinned `vllm-hust-dev-hub` submodule:

```bash
git submodule update --init --recursive external/vllm-hust-dev-hub
tools/benchmark_carrier/setup_esage_conda_env.sh \
  --source-env vllm-hust-dev \
  --target-env esage-vllm-hust-dev \
  --dev-hub "$PWD/external/vllm-hust-dev-hub" \
  --prepare-source-env
```

This delegates vLLM-HUST repository sync and editable installs to the pinned
dev-hub submodule:

```bash
bash "$PWD/external/vllm-hust-dev-hub/scripts/quickstart.sh" \
  --conda \
  --install \
  --install-mode refresh \
  --install-scope core \
  --env-name vllm-hust-dev \
  -y
```

The vLLM-Ascend-HUST compatibility patches used for NPU3 real-online readiness
are tracked as a SAGE submodule:

```bash
git submodule update --init --recursive \
  external/vllm-hust \
  external/vllm-ascend-hust \
  external/vllm-hust-dev-hub \
  third_party/ascend-runtime-manager
git submodule update --init external/triton-ascend-hust
```

The expected base vLLM-HUST checkout is `external/vllm-hust` at
`5de748bea122fb0917adc6117fbb37429b60aa24` on
`feature/sage-semantic-mapreduce-vllm-runtime`. The expected vLLM-Ascend-HUST commit is
`339b27ad69aa12b8f56bbd1885c046be4e53c945` on the project readiness branch.
The matching dev-hub branch is `feature/sage-semantic-mapreduce-dev-hub`,
pinned at `7ab74990d5bfc4953d7bb1f99dfb93720e2adc81`.
The dev-hub container helper is also pinned as
`third_party/ascend-runtime-manager` on
`feature/semantic-mapreduce-runtime-integration` at
`c5b0461aaecffe7e5011f8fab0944d32bedb1092`.
The matching Triton-Ascend runtime is pinned as
`external/triton-ascend-hust` on
`feature/sage-semantic-mapreduce-triton-runtime` at
`612d5772bcd4ee7a75ab4939aa3580d937147d83`.

Before launching a real NPU endpoint, validate the runtime branch and use the
printed dev-hub overrides:

```bash
SAGE_RUNTIME_FETCH=0 tools/benchmark_carrier/prepare_vllm_ascend_runtime_branch.sh
```

The validation step rejects runtime submodule paths that are symlinks to shared
home-directory checkouts. Real-online runs should use the independent
`external/*` submodules recorded by this repository. `SAGE_RUNTIME_FETCH=0`
keeps reproduction independent of GitHub SSH availability and validates the
already checked-out feature branches.

For the NPU3 real-online Semantic MapReduce experiment, prefer the one-command
launcher. It initializes the SAGE-pinned submodules, checks that NPU3 and port
18383 are free, starts vLLM-HUST through the dev-hub submodule with the
runtime-manager NPU-device whitelist, fails if any managed container process
appears outside NPU3 during startup, fails if Triton-Ascend is unavailable or
vLLM falls back to the V1 model runner, runs smoke and latency probes, runs the
LLM reducer workload, and records metadata under
`.sage/benchmarks/real_online_semantic_mapreduce/`:

```bash
tools/benchmark_carrier/run_npu3_semantic_mapreduce_experiment.sh
```

For manual endpoint replay work, start vLLM-HUST through the hub launcher
rather than by hand inside the container:

```bash
cd external/vllm-hust-dev-hub
VLLM_ENGINE_PORT=8000 \
VLLM_ENGINE_MODEL_PATH=/data/shared_models/modelscope_cache/Qwen/Qwen3-32B \
VLLM_ENGINE_SERVED_MODEL_NAME=qwen3-32b \
bash manage.sh foreground
```

The large-scale analysis results in this paper are synthetic and do not require
starting this endpoint.

### Real-Online vLLM-HUST Baseline

A small single-NPU real-online benchmark has also been recorded as a readiness
baseline for future LLM-backed reducers:

```text
.sage/benchmarks/real_online_vllm_hust/20260630T-qwen25-7b-npu4-c1/
.sage/benchmarks/real_online_vllm_hust/20260630T-qwen25-7b-npu4-c2/
```

Configuration:

- vLLM-HUST launched through `vllm-hust-dev-hub/manage.sh foreground`.
- Model: `/data/shared_models/Qwen2.5-7B-Instruct`.
- Device: one Ascend 910B2 NPU, device 4.
- TP=1, `max_model_len=1024`, `max_num_seqs=1`.
- Streaming `/v1/completions`, 2 warmups, 8 measured requests, `max_tokens=48`.

| concurrency | ok / total | mean TTFT ms | mean TPOT ms | mean latency ms | e2e completion tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8 / 8 | `117.69` | `70.18` | `1,591.52` | `13.82` |
| 2 | 8 / 8 | `1,494.64` | `70.24` | `2,969.69` | `13.883` |

This is not a SOTA performance comparison. It is a real-online readiness result
showing that the SAGE experiment environment can launch a vLLM-HUST endpoint,
issue authenticated streaming requests, measure TTFT/TPOT, and clean up the
service. The concurrency-2 TTFT increase is expected because the endpoint was
configured with `max_num_seqs=1`.

### Real LLM Reducer Readiness

The paper uses LLM-backed reducers as contract-stress tests: they exercise
structured output readiness, token/latency accounting, evidence references,
and fallback behavior under the same scorer as deterministic reducers. The
repository includes a successful NPU3 real-online sanity run for the
OpenAI-compatible `llm-openai` reducer. The reducer and JSON readiness probe
can be exercised with:

```bash
PYTHONPATH=src python tools/benchmark_carrier/probe_llm_json_readiness.py \
  --base-url http://127.0.0.1:<port> \
  --model <served-model-name> \
  --env-file "$HOME/vllm-hust-dev-hub/.env" \
  --endpoint-type chat \
  --structured-output
```

The 2026-07-01 real-online probes on Qwen2.5-7B and Qwen2.5-14B vLLM-HUST
endpoints reached the structured-output path but returned malformed or truncated
JSON when the schema included free-form explanation text. The reducer contract
now keeps the LLM output structural: it selects evidence ids, and the local
normalizer/reporting stage derives metadata and explanation from evidence
objects. A 2026-07-06 NPU3 run then completed the full one-command path:
Triton-Ascend import validation, vLLM-HUST health, smoke request, streaming
latency probe, and two reducer workloads.

```text
.sage/benchmarks/real_online_semantic_mapreduce/20260706T170917Z-npu3-semantic-mapreduce/
```

| run | events | shards | precision | recall | F1 | SemanticReduce ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LLM reducer smoke | 2,000 | 4 | 1.0 | 0.25 | 0.4 | 48,626.03 |
| LLM reducer sanity | 20,000 | 8 | 1.0 | 1.0 | 1.0 | 5,055.39 |

The same run records a successful `/v1/completions` smoke request
(`status=200`, 5,556.71 ms) and a streaming probe with 8/8 successful requests
(mean TTFT 68.63 ms, mean TPOT 19.88 ms, 45.23 completion tokens/s). These are
real-online sanity results, not a broad serving-performance or SOTA comparison:
they use one model, one NPU, one seed, and two workload sizes. The useful paper
claim is narrower: the live LLM reducer path is now operational under the same
evidence/scoring contract, and sparse evidence still limits recall.

For deterministic-vs-LLM comparison, use the guarded script below. The script
does not start a service by itself; first start vLLM-HUST through the
SAGE-pinned dev-hub submodule on NPU3, then opt in:

```bash
ALLOW_NPU3_REAL_ONLINE=1 \
SAGE_LSA_LLM_BASE_URL=http://127.0.0.1:18383 \
SAGE_LSA_LLM_MODEL=<served-model-name> \
tools/benchmark_carrier/run_npu3_llm_reducer_comparison.sh
```

The script fixes the seed/workload for deterministic and `llm-openai`, records
parent/submodule provenance, and writes `comparison_summary.json` with quality,
`SemanticReduce` latency, token counts, estimated cost, and missed incidents.

For the semantic-merge suite, use the candidate-level LLM comparison harness:

```bash
ALLOW_NPU3_REAL_ONLINE=1 \
SAGE_SMR_LLM_BASE_URL=http://127.0.0.1:18383 \
SAGE_SMR_LLM_MODEL=<served-model-name> \
tools/benchmark_carrier/run_npu3_semantic_merge_llm_comparison.sh
```

This compares `semantic-graph`, `hybrid-hint`, `llm-hybrid`,
`llm-hybrid-validated`, and `llm-openai` on the same seeds, scenarios,
evidence objects, and scorer. It
records token cost, latency, candidate counts, repair counts, split counts,
fallback counts, invalid JSON/schema counts, coverage, and support-evidence
recall. The quality claim for live LLM-backed reduction should be based on
accepted candidate edits that preserve the validation contract and improve over
the deterministic/hybrid baselines under the same scorer.

Current NPU3 semantic-merge matrix artifact:

```text
.sage/benchmarks/real_online_semantic_merge/20260709T161819Z-npu3-qwen25-7b-validated-smoke/
```

Summary:

- `partial-evidence` seed 7: `semantic-graph` F1=0.5, `hybrid-hint` F1=1.0,
  `llm-hybrid` F1=0.6667 after adding an extra fragment,
  `llm-hybrid-validated` F1=1.0 with fallback, and full-evidence
  `llm-openai` F1=0.4 with support-evidence recall 0.25.
- `false-correlation` seed 7: `semantic-graph`, `hybrid-hint`, and
  both candidate-level LLM reducers all reach F1=0.75; full-evidence
  `llm-openai` reaches F1=0.4 with support-evidence recall 0.25.
- `ambiguous-overmerge` seed 7: `semantic-graph` and `hybrid-hint` reach
  F1=0.8571. Raw `llm-hybrid` accepts a useful split and reaches F1=1.0.
  `llm-hybrid-validated` rejects invalid-schema output and preserves F1=0.8571
  with support-evidence recall 1.0. Full-evidence `llm-openai` reaches F1=0.4
  with support-evidence recall 0.25.

Interpretation: the supported claim is guarded semantic reduction. The split
operation is implemented and covered by unit tests; the live matrix shows both
the opportunity and the danger of model edits. Accepted model edits must pass
schema, evidence-reference, root/affected, and coverage validation before they
can improve beyond `hybrid-hint`.

The 2026-07-08 NPU3 fair comparison artifacts are:

```text
.sage/benchmarks/real_online_semantic_mapreduce/20260708T-npu3-smr-fair-baseline-server/
.sage/benchmarks/real_online_semantic_mapreduce/20260708T-npu3-fair-reducer-20k-seed7/
.sage/benchmarks/real_online_semantic_mapreduce/20260708T-npu3-fair-reducer-50k-seed23/
.sage/benchmarks/real_online_semantic_mapreduce/20260708T-npu3-fair-reducer-50k-seed23-baseline-aware/
.sage/benchmarks/real_online_semantic_mapreduce/20260708T-npu3-fair-reducer-50k-seed23-baseline-aware-t384/
```

Summary:

- 20k/seed7: deterministic and `llm-openai` both reach F1=1.0, but LLM
  `SemanticReduce` takes `53,459.30` ms and uses `1,148` tokens.
- 50k/seed23 tail-aware: both reducers miss `incident-3`; failure taxonomy
  identifies missing map evidence for the router incident.
- 50k/seed23 baseline-aware: the first LLM run fails the 2048-token context
  budget with 768 requested output tokens; the rerun with 384 max output tokens
  succeeds, but deterministic and `llm-openai` both reach F1=1.0 while LLM
  `SemanticReduce` takes `5,813.26` ms and uses `1,683` tokens.

## Adapter-Level Comparison

The paper also reports a local adapter-level comparison:

```text
.sage/benchmarks/large_scale_analysis_adapters/20260630T-adapter-comparison-steady/
```

Run command:

```bash
tools/benchmark_carrier/setup_esage_conda_env.sh \
  --source-env vllm-hust-dev \
  --target-env esage-vllm-hust-dev \
  --dev-hub "$HOME/vllm-hust-dev-hub" \
  --prepare-source-env \
  --with-adapter-comparison

conda run -n esage-vllm-hust-dev env PYTHONPATH=src python \
  tools/benchmark_carrier/run_large_scale_analysis_adapter_comparison.py \
  --sizes 50000:16:12,100000:32:16 \
  --seeds 7,11,13 \
  --adapters sage-local,ray-local,langgraph-local,llamaindex-docstore \
  --run-id 20260630T-adapter-comparison-steady \
  --continue-on-error
```

The setup script installs the `adapter-comparison` project extra automatically;
do not install Ray, LangGraph, or LlamaIndex-core manually for this experiment.

Current aggregate adapter comparison:

| adapter | mean F1 | mean throughput events/s | mean total ms |
| --- | ---: | ---: | ---: |
| SAGE local | `0.9392` | `58,594` | `1,301.33` |
| LangGraph local | `0.9392` | `60,051` | `1,257.80` |
| LlamaIndex docstore | `0.9392` | `61,519` | `1,230.84` |
| Ray local | `0.9392` | `39,739` | `1,870.75` |

This comparison fixes the generator, evidence schema, deterministic reducer, and
scorer. It therefore measures local wrapper/evidence-packaging overhead, not
semantic quality. The Ray row is especially diagnostic: the run emitted NPU
detection warnings because the optional `acl` Python module was absent, and the
host reported `/tmp/ray` space pressure. It should not be interpreted as tuned
Ray cluster performance.
