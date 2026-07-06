# Semantic MapReduce Paper Draft

This directory contains the systems-conference LaTeX draft for the SAGE
large-scale analysis workload and Semantic MapReduce framing.

## Venue Choice

Recommended style target: **ASPLOS full paper**.

Rationale:

- The user asked for a traditional systems-conference long-paper target rather
  than an ML systems paper.
- ASPLOS is a closer fit than MLSys for the current framing because the paper
  emphasizes system abstraction, runtime/orchestration boundaries, workload
  design, and careful claim discipline around LLM-serving integration.
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

## Experiment Artifact

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
`40a2afed0ae7896e004cf6d0f67c0d89e7e1582b`.
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

The paper does not yet use LLM-backed incident precision/recall as the main
quality result, but the repository now includes a successful NPU3 real-online
sanity run for the OpenAI-compatible `llm-openai` reducer. The reducer and JSON
readiness probe can be exercised with:

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
