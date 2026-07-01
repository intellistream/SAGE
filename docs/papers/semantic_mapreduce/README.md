# Semantic MapReduce Paper Draft

This directory contains the systems-conference LaTeX draft for the SAGE
large-scale analysis workload and Semantic MapReduce framing.

## Venue Choice

Recommended style target: **ACM SIGOPS ATC long paper**.

Rationale:

- The user asked for a more traditional systems-conference long-paper format
  rather than an ML systems paper.
- ATC 2026 long submissions are capped at 12 pages excluding references and
  appendices, matching the desired "12-page systems paper" shape.
- The ATC/SIGOPS format is a better fit for the current artifact than MLSys:
  the draft is about workflow/runtime boundaries, evidence reduction, workload
  design, and careful systems claims.
- SOSP/OSDI are plausible future targets after the prototype has a real
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

The paper currently reports the reproduced matrix run with diagnostic
comparison baselines:

```text
.sage/benchmarks/large_scale_analysis/20260630T-sota-proxy-baselines/
```

The run used the `esage-vllm-hust-dev` conda environment and includes:

- `summary.csv`
- `summary.json`
- `aggregate.json`
- raw JSON reports for each reducer/size/seed configuration

Current aggregate reducer comparison:

| reducer | mean precision | mean recall | mean F1 |
| --- | ---: | ---: | ---: |
| map-only | `0.1459` | `0.5000` | `0.2250` |
| window-aggregate | `0.6432` | `0.9583` | `0.7600` |
| deterministic | `0.9333` | `0.9583` | `0.9392` |
| llm-stub | `0.9333` | `0.9583` | `0.9392` |

The `llm-stub` reducer intentionally matches the deterministic reducer because
it is a CI-safe placeholder, not a real LLM experiment.

The map-only and window-aggregate rows are diagnostic baselines that isolate the
benefit of incident-level semantic reduction. They are not full external-system
SOTA comparisons.

### Environment Setup

On vLLM-HUST machines, prepare the source environment through
`vllm-hust-dev-hub` and let SAGE clone it:

```bash
tools/benchmark_carrier/setup_esage_conda_env.sh \
  --source-env vllm-hust-dev \
  --target-env esage-vllm-hust-dev \
  --dev-hub "$HOME/vllm-hust-dev-hub" \
  --prepare-source-env
```

This delegates vLLM-HUST repository sync and editable installs to:

```bash
bash "$HOME/vllm-hust-dev-hub/scripts/quickstart.sh" \
  --conda \
  --install \
  --install-mode refresh \
  --install-scope core \
  --env-name vllm-hust-dev \
  -y
```

For real endpoint replay work, start vLLM-HUST through the hub launcher rather
than by hand inside the container:

```bash
cd "$HOME/vllm-hust-dev-hub"
VLLM_ENGINE_PORT=8000 \
VLLM_ENGINE_MODEL_PATH=/data/shared_models/modelscope_cache/Qwen/Qwen3-32B \
VLLM_ENGINE_SERVED_MODEL_NAME=qwen3-32b \
bash scripts/run_vllm_hust_engine.sh
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

- vLLM-HUST launched through `vllm-hust-dev-hub/scripts/run_vllm_hust_engine.sh`.
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
