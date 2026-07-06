# SAGE Large-Scale Analysis Workload

This workload evaluates whether SAGE can act as the orchestration layer for
large-scale data analysis with LLM-style semantic reduction.

It is not a Spark/Hadoop replacement benchmark. The goal is to measure the
AI workflow layer: partitioning, local evidence extraction, global incident
fusion, and explanation generation.

## Scenario

A production LLM serving platform emits high-volume telemetry from NPU-backed
services:

- `prefill`
- `decode`
- `kv-cache`
- `scheduler`
- `router`
- `embedding`

Each event contains service, tenant, region, latency, error flag, NPU
utilization, and queue depth. The generator injects hidden incidents such as:

- latency spikes
- NPU saturation
- queue backlog

The workload asks the system to recover these incidents from the event stream.

## Pipeline

1. **Generate data**: synthesize an event stream and ground-truth incidents.
2. **Map**: split events into shards and compute local anomaly candidates per
   service, region, and time window.
3. **Reduce**: merge candidates across shards and cluster adjacent windows into
   incident-level hypotheses.
4. **Explain**: produce a concise natural-language summary for each incident.
5. **Score**: compare detected incidents against injected ground truth.

This mirrors a MapReduce-like SAGE workload: the expensive data scan is
partitionable, while the semantic reduce step fuses evidence into structured
insights.

## Metrics

- `precision`: fraction of reported incidents that match injected incidents.
- `recall`: fraction of injected incidents recovered.
- `f1`: harmonic mean of precision and recall.
- `evidence_coverage`: average evidence events per detected incident.
- `map_duration_ms`, `reduce_duration_ms`, `total_duration_ms`.
- `throughput_events_per_s`.
- `operator_duration_ms`: timing fields keyed by the standard Semantic
  MapReduce operators (`Shard`, `MapEvidence`, `Normalize`, `GroupEvidence`,
  `SemanticReduce`, `ReportTrace`). In the current baseline, `Normalize` and
  `GroupEvidence` may be fused into adjacent stages and therefore report `0.0`
  until those operators are split out.
- `reducer_name`: the reducer implementation used for the run.
- `seed` and `top_k`: reproducibility metadata for the run.
- `injected_incidents`, `detected_incidents`, and `missed_incidents`: structured
  incident records for audit and paper/report writing. Each detected incident
  includes `matched_incident_id` after scoring.

## Reducers

The workload now uses a pluggable reducer contract:

- `map-only`: a diagnostic alert-style baseline that reports shard-local
  candidates directly. It does not perform global deduplication or incident
  clustering.
- `window-aggregate`: a diagnostic windowed-analytics baseline that merges
  candidates within each service/region/window but does not cluster adjacent
  windows into incident-level hypotheses.
- `deterministic`: the default threshold-based reducer. This is the reproducible
  baseline used by CI and the benchmark numbers below.
- `llm-stub`: a CI-safe placeholder for a future LLM semantic reducer. It keeps
  deterministic evidence fusion but marks summaries as stubbed LLM outputs. It
  does not call an external model and must not be reported as an end-to-end LLM
  result.
- `llm-openai`: a real OpenAI-compatible semantic reducer. It sends compact
  window-level evidence to `/v1/chat/completions` or `/v1/completions`, requires
  JSON incident hypotheses, and can request an OpenAI-compatible JSON schema with
  `--llm-structured-output`. This reducer does not fall back to the deterministic
  reducer on endpoint or parse failure, so use the JSON readiness probe below
  before reporting LLM-backed workload results.

## eSAGE Experiment Environment

For eSAGE experiments that interact with vLLM-HUST or reuse vLLM benchmark
helpers, do not start from a bare Python or generic SAGE-only conda environment.
Create a clone of the vLLM-HUST development environment first, then install the
additional SAGE runtime, edge-serving, benchmark, and test dependencies into the
clone:

```bash
tools/benchmark_carrier/setup_esage_conda_env.sh \
  --source-env vllm-hust-dev \
  --target-env esage-vllm-hust-dev
```

The script also accepts `vllmhustdev` if that is the local environment name. It
does not modify the source vLLM-HUST environment. The cloned environment must
use Python 3.11 or newer because the SAGE package requires Python `>=3.11`.

On machines that use `vllm-hust-dev-hub`, prefer letting the hub prepare the
source environment first. This keeps vLLM-HUST repository sync, editable
installs, and Ascend Python-stack reconciliation in the hub instead of
duplicating that logic in SAGE:

```bash
tools/benchmark_carrier/setup_esage_conda_env.sh \
  --source-env vllm-hust-dev \
  --target-env esage-vllm-hust-dev \
  --dev-hub "$HOME/vllm-hust-dev-hub" \
  --prepare-source-env
```

Internally, `--prepare-source-env` delegates to:

```bash
bash "$HOME/vllm-hust-dev-hub/scripts/quickstart.sh" \
  --conda \
  --install \
  --install-mode refresh \
  --install-scope core \
  --env-name vllm-hust-dev \
  -y
```

After setup, run workload commands through the cloned environment:

```bash
conda run -n esage-vllm-hust-dev env PYTHONPATH=src python \
  tools/benchmark_carrier/run_large_scale_analysis_workload.py \
  --events 50000 \
  --shards 16 \
  --seed 7 \
  --top-k 12 \
  --reducer deterministic
```

The synthetic workload below can still run in any compatible SAGE development
environment. Real eSAGE/vLLM-HUST experiments should use the cloned
`esage-vllm-hust-dev` environment so SAGE dependencies are layered on top of the
same vLLM-HUST Python stack used by the serving runtime.

To reproduce the optional adapter comparison against Ray, LangGraph, and
LlamaIndex-core wrappers, include the extra setup flag. The setup script installs
the project extra `adapter-comparison`; do not manually `pip install` these
packages into the cloned environment:

```bash
tools/benchmark_carrier/setup_esage_conda_env.sh \
  --source-env vllm-hust-dev \
  --target-env esage-vllm-hust-dev \
  --with-adapter-comparison
```

Note that `openai_replay_carrier.py` reuses vLLM benchmark helper modules. If
`python -c "import vllm"` is not available in the cloned environment, rerun the
setup with `--prepare-source-env` so `vllm-hust-dev-hub` can refresh the
vLLM-HUST source environment. The synthetic workload in this document does not
require the `vllm` Python package.

For real vLLM-HUST endpoint replay experiments, start the model service through
the hub rather than launching vLLM by hand inside the container:

```bash
cd "$HOME/vllm-hust-dev-hub"

# Requires VLLM_HUST_API_KEY in .env or the caller environment.
VLLM_ENGINE_PORT=8000 \
VLLM_ENGINE_MODEL_PATH=/data/shared_models/modelscope_cache/Qwen/Qwen3-32B \
VLLM_ENGINE_SERVED_MODEL_NAME=qwen3-32b \
bash manage.sh foreground
```

The hub launcher manages the official Ascend container, vLLM-HUST Python path,
Ascend/runtime guardrails, and endpoint process cleanup. Stop the endpoint with:

```bash
cd "$HOME/vllm-hust-dev-hub"
VLLM_ENGINE_PORT=8000 bash manage.sh stop
```

### Real vLLM-HUST Smoke Probe

Before running a real-online experiment, check accelerator occupancy and choose
devices that have no NPU process:

```bash
npu-smi info
ps -eo pid,user,stat,pcpu,pmem,args | \
  rg -i 'vllm|VLLM|run_vllm|cleanup_vllm|benchmark'
ss -ltnp
```

On 2026-06-30, a smoke probe was run on NPU 4 while other long-running
experiments occupied NPU 0-3 and NPU 5/7. The first attempt used the local
Hugging Face cache for `Qwen2.5-1.5B-Instruct`, but that snapshot contained
configuration files without model weights, so vLLM-HUST failed before serving
traffic. The successful smoke used the complete local model directory
`/data/shared_models/Qwen2.5-7B-Instruct`:

```bash
cd "$HOME/vllm-hust-dev-hub"

VLLM_ENGINE_CONTAINER=sage-smoke-vllm-hust-21rc \
VLLM_ENGINE_NPU_DEVICES=4 \
ASCEND_RT_VISIBLE_DEVICES=4 \
ASCEND_VISIBLE_DEVICES=4 \
VLLM_ENGINE_PORT=18381 \
VLLM_ENGINE_TP_SIZE=1 \
VLLM_ENGINE_MODEL_PATH=/data/shared_models/Qwen2.5-7B-Instruct \
VLLM_ENGINE_SERVED_MODEL_NAME=qwen25-7b-sage-smoke \
VLLM_ENGINE_MAX_MODEL_LEN=1024 \
VLLM_ENGINE_MAX_NUM_BATCHED_TOKENS=1024 \
VLLM_ENGINE_MAX_NUM_SEQS=1 \
VLLM_ENGINE_GPU_MEM_UTIL=0.75 \
VLLM_ENGINE_ENFORCE_EAGER=1 \
VLLM_ENGINE_ENABLE_PREFIX_CACHING=0 \
VLLM_ENGINE_ENABLE_CHUNKED_PREFILL=0 \
VLLM_PLUGINS=ascend \
VLLM_ENGINE_PYTHONPATH=/workspace/SAGE/external/vllm-hust:/workspace/SAGE/external/vllm-ascend-hust \
bash manage.sh foreground
```

Once `/health` returns 200, send one OpenAI-compatible request without printing
the API key:

```bash
PYTHONPATH=src python tools/benchmark_carrier/run_vllm_hust_smoke_request.py \
  --base-url http://127.0.0.1:18381 \
  --model qwen25-7b-sage-smoke \
  --output .sage/benchmarks/real_online_smoke/20260630T-vllm-hust-npu4-smoke.json
```

The smoke produced HTTP 200 with 11 prompt tokens, 8 completion tokens, and
38,142.59 ms wall latency for the first request. Treat this as `real-online
smoke` evidence only: the latency includes cold-start/first-request overhead and
must not be reported as throughput or SOTA performance.

Cleanup:

```bash
cd "$HOME/vllm-hust-dev-hub"
VLLM_ENGINE_CONTAINER=sage-smoke-vllm-hust-21rc \
VLLM_ENGINE_PORT=18381 \
VLLM_ENGINE_AGGRESSIVE_CLEANUP=false \
bash manage.sh stop
```

### Real-Online Single-NPU Benchmark

After the smoke probe, a small formal real-online benchmark was run on the same
single-NPU configuration:

- Date: 2026-06-30.
- Provenance: `real-online`.
- Serving launch path: `vllm-hust-dev-hub/manage.sh foreground`.
- Model: `/data/shared_models/Qwen2.5-7B-Instruct`.
- Served model name: `qwen25-7b-sage-realonline`.
- Hardware: one Ascend 910B2 NPU, device 4.
- Isolation: NPU 4 had no process before launch; NPU 5/7 had unrelated
  long-running EngineCore processes and were not used.
- vLLM-HUST launch settings requested by the script: TP=1,
  `max_model_len=1024`, `max_num_seqs=1`, `gpu_memory_utilization=0.75`,
  and eager mode. Prefix caching and chunked prefill should be treated as
  effective-server settings and verified from the vLLM-HUST launch log for each
  run; do not infer them only from environment variables.
- Request workload: streaming `/v1/completions`, 2 warmup requests, 8 measured
  requests, `max_tokens=48`, `temperature=0`.

Run commands:

```bash
PYTHONPATH=src python tools/benchmark_carrier/run_vllm_hust_online_benchmark.py \
  --base-url http://127.0.0.1:18381 \
  --model qwen25-7b-sage-realonline \
  --max-tokens 48 \
  --requests 8 \
  --warmup-requests 2 \
  --concurrency 1 \
  --run-id 20260630T-qwen25-7b-npu4-c1

PYTHONPATH=src python tools/benchmark_carrier/run_vllm_hust_online_benchmark.py \
  --base-url http://127.0.0.1:18381 \
  --model qwen25-7b-sage-realonline \
  --max-tokens 48 \
  --requests 8 \
  --warmup-requests 2 \
  --concurrency 2 \
  --run-id 20260630T-qwen25-7b-npu4-c2
```

Artifacts:

```text
.sage/benchmarks/real_online_vllm_hust/20260630T-qwen25-7b-npu4-c1/
.sage/benchmarks/real_online_vllm_hust/20260630T-qwen25-7b-npu4-c2/
```

Summary:

| concurrency | ok / total | mean TTFT ms | mean TPOT ms | mean latency ms | e2e completion tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8 / 8 | 117.69 | 70.18 | 1,591.52 | 13.82 |
| 2 | 8 / 8 | 1,494.64 | 70.24 | 2,969.69 | 13.883 |

The concurrency-2 run has similar TPOT and end-to-end throughput but much larger
mean TTFT because the endpoint was intentionally launched with `max_num_seqs=1`.
The second concurrent request therefore waits behind the active decode. This is
a useful sanity check for the benchmark harness, but it is not a throughput
optimization result.

The benchmark uses streaming responses to estimate TTFT. Some vLLM streaming
events do not include final tokenizer `usage`, so the runner records
`completion_token_source` for each request and falls back to a completion-token
estimate from returned text when usage is absent. Use these numbers as a
systems-readiness baseline; a paper-grade latency study should increase request
count, fix tokenizer-based usage accounting, record the effective server
configuration from launch logs, and report multiple seeds or repeated trials.

### Real LLM Reducer Readiness

The `llm-openai` reducer is intended for real semantic-reduce experiments, but
the endpoint must first pass a structured-output readiness gate. A healthy model
server is not enough: the reducer requires parseable incident JSON, and malformed
or truncated model output must be treated as a failed experiment rather than as a
low-quality detection result. The current contract asks the LLM to select
structured evidence groups only; the normalization/reporting stages derive
service, region, time range, signals, and explanation from the selected evidence
objects.

For vLLM-HUST, start the endpoint through the hub's `manage.sh` entrypoint.
Use `manage.sh foreground` for an interactive paper/debug run and
`manage.sh start` / `manage.sh stop` / `manage.sh health` for the managed
systemd path. The example below uses one Ascend 910B2 NPU outside the reserved
0-3 range and does not print or store the API key:

```bash
cd "$HOME/vllm-hust-dev-hub"

VLLM_ENGINE_CONTAINER=sage-lsa-json-mode-probe-7b-20260702 \
VLLM_ENGINE_NPU_DEVICES=4 \
ASCEND_RT_VISIBLE_DEVICES=4 \
ASCEND_VISIBLE_DEVICES=4 \
VLLM_ENGINE_PORT=18386 \
VLLM_ENGINE_TP_SIZE=1 \
VLLM_ENGINE_MODEL_PATH=/data/shared_models/Qwen2.5-7B-Instruct \
VLLM_ENGINE_SERVED_MODEL_NAME=qwen25-7b-json-probe \
VLLM_ENGINE_MAX_MODEL_LEN=2048 \
VLLM_ENGINE_MAX_NUM_BATCHED_TOKENS=2048 \
VLLM_ENGINE_MAX_NUM_SEQS=1 \
VLLM_ENGINE_GPU_MEM_UTIL=0.75 \
VLLM_ENGINE_ENFORCE_EAGER=1 \
VLLM_ENGINE_ENABLE_PREFIX_CACHING=0 \
VLLM_ENGINE_ENABLE_CHUNKED_PREFILL=0 \
VLLM_PLUGINS=ascend \
VLLM_ENGINE_PYTHONPATH=/workspace/SAGE/external/vllm-hust:/workspace/SAGE/external/vllm-ascend-hust \
VLLM_ENGINE_EXTRA_ARGS_JSON='["--generation-config","vllm","--structured-outputs-config","{\"backend\":\"xgrammar\",\"disable_any_whitespace\":true}"]' \
bash manage.sh foreground
```

Run the readiness probe only after `/health` returns 200:

```bash
PYTHONPATH=src python tools/benchmark_carrier/probe_llm_json_readiness.py \
  --base-url http://127.0.0.1:18386 \
  --model qwen25-7b-json-probe \
  --env-file "$HOME/vllm-hust-dev-hub/.env" \
  --endpoint-type chat \
  --structured-output \
  --max-tokens 512 \
  --timeout-sec 180 \
  --output .sage/benchmarks/llm_json_readiness/20260702T-qwen25-7b-npu4-chat-structured-no-summary-signalfix.json
```

For endpoint-contract debugging, use `--simple-prompt` to ask for a minimal JSON
object before testing the incident schema:

```bash
PYTHONPATH=src python tools/benchmark_carrier/probe_llm_json_readiness.py \
  --base-url http://127.0.0.1:18386 \
  --model qwen25-7b-json-probe \
  --env-file "$HOME/vllm-hust-dev-hub/.env" \
  --endpoint-type chat \
  --simple-prompt \
  --max-tokens 64 \
  --timeout-sec 60 \
  --output .sage/benchmarks/llm_json_readiness/<run-id>-simple-json.json
```

If the probe returns `status: ok`, run a small LLM reducer workload:

```bash
PYTHONPATH=src python tools/benchmark_carrier/run_large_scale_analysis_workload.py \
  --events 2000 \
  --shards 4 \
  --seed 7 \
  --top-k 5 \
  --reducer llm-openai \
  --llm-base-url http://127.0.0.1:18386 \
  --llm-model qwen25-7b-json-probe \
  --llm-env-file "$HOME/vllm-hust-dev-hub/.env" \
  --llm-endpoint-type chat \
  --llm-structured-output \
  --llm-max-evidence 12 \
  --llm-max-tokens 512 \
  --llm-timeout-sec 240 \
  --output .sage/benchmarks/large_scale_analysis_llm_reducer/<run-id>/report.json
```

Cleanup:

```bash
cd "$HOME/vllm-hust-dev-hub"
VLLM_ENGINE_CONTAINER=sage-lsa-json-mode-probe-7b-20260702 \
VLLM_ENGINE_PORT=18386 \
VLLM_ENGINE_AGGRESSIVE_CLEANUP=false \
bash manage.sh stop
```

On 2026-07-01, the readiness gate was exercised on real vLLM-HUST endpoints:

| model | serving configuration | readiness status | artifact |
| --- | --- | --- | --- |
| Qwen2.5-7B-Instruct | chat, `--generation-config vllm` | error: non-JSON repeated tokens | `.sage/benchmarks/llm_json_readiness/20260701T-qwen25-7b-npu4-chat-generation-config-vllm.json` |
| Qwen2.5-7B-Instruct | chat, xgrammar structured output | error: malformed JSON after entering schema path | `.sage/benchmarks/llm_json_readiness/20260701T-qwen25-7b-npu4-chat-structured-xgrammar.json` |
| Qwen2.5-14B-Instruct | chat, xgrammar structured output, tight schema | error: schema-shaped but truncated/malformed JSON | `.sage/benchmarks/llm_json_readiness/20260701T-qwen25-14b-npu4-chat-structured-xgrammar-tight-schema-max4-512.json` |

The 2026-07-01 failures showed that free-form natural-language fields inside the
schema made the endpoint generate malformed or truncated JSON. The reducer
contract was therefore tightened: LLM output now selects evidence ids, while
metadata and explanations are derived from evidence objects. With that contract,
a 2026-07-02 real-online smoke on Qwen2.5-7B passed JSON readiness and completed
the workload:

| run | events | status | precision | recall | F1 | artifact |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| JSON readiness | n/a | ok | n/a | n/a | n/a | `.sage/benchmarks/llm_json_readiness/20260702T-qwen25-7b-npu4-chat-structured-no-summary-signalfix.json` |
| LLM reducer smoke | 2,000 | completed | 1.0 | 0.25 | 0.4 | `.sage/benchmarks/large_scale_analysis_llm_reducer/20260702T-qwen25-7b-npu4-structured-evidence-dedup/report.json` |
| LLM reducer smoke | 20,000 | completed | 1.0 | 0.25 | 0.4 | `.sage/benchmarks/large_scale_analysis_llm_reducer/20260702T-qwen25-7b-npu4-structured-evidence-dedup-20k/report.json` |

These are real-online smoke results, not paper-grade LLM reducer quality
results. They show that the endpoint can satisfy the structured reducer
contract and that the workload can run end to end with a live LLM. The first
smoke runs also exposed an important systems failure mode: the 7B model often
returned schema-valid but semantically degenerate JSON, repeatedly selecting
the first evidence id. The reducer now treats LLM output as a proposal and
applies two auditable runtime guardrails:

- `coverage repair`: add remaining high-score evidence groups that the model
  dropped or repeated.
- `consolidation`: merge adjacent or overlapping incidents for the same
  service and region after repair.

This should be reported as a guarded LLM reducer, not as raw LLM quality. The
guardrails are part of the SAGE-style orchestration layer: they preserve the
evidence contract and make failures visible instead of silently accepting a
malformed semantic reduce.

The same debugging pass found that the 100k deterministic miss was caused by
the map stage rather than by the semantic reducer: the injected scheduler
incident had high tail NPU utilization but lower mean utilization. `MapEvidence`
therefore now records `p95_npu_util` and marks NPU saturation when either mean
utilization is high or p95 utilization exceeds a stricter saturation threshold.
This recovers the scheduler incident without admitting the earlier low-support
tail-NPU false positives.

Final 2026-07-02 real-online smoke results on NPU4, using Qwen2.5-7B-Instruct
served through vLLM-HUST with xgrammar structured output:

| run | events | shards | precision | recall | F1 | artifact |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| guarded LLM reducer | 20,000 | 8 | 1.0 | 1.0 | 1.0 | `.sage/benchmarks/large_scale_analysis_llm_reducer/20260702T-qwen25-7b-npu4-structured-coverage-consolidate-20k/report.json` |
| guarded LLM reducer | 50,000 | 16 | 1.0 | 1.0 | 1.0 | `.sage/benchmarks/large_scale_analysis_llm_reducer/20260702T-qwen25-7b-npu4-structured-tailnpu-consolidate-50k/report.json` |
| guarded LLM reducer | 100,000 | 32 | 1.0 | 1.0 | 1.0 | `.sage/benchmarks/large_scale_analysis_llm_reducer/20260702T-qwen25-7b-npu4-structured-tailnpu-consolidate-100k/report.json` |

For comparison, the final tail-aware deterministic reducer also reaches
precision 1.0, recall 1.0, and F1 1.0 on the 100k/32-shard seed-7 workload:
`.sage/benchmarks/large_scale_analysis_llm_reducer/20260702T-map-tail-npu-strict-deterministic-100k.json`.
This is a useful correction to the workload baseline, and it means the paper
should not claim that the current guarded 7B reducer outperforms the
deterministic reducer on this seed. The stronger claim is that SAGE exposes the
right operator boundaries for finding and fixing both classes of failures:
map-stage signal loss and reducer-stage semantic degeneration.

### NPU3 Real-Online Bring-Up and Fix

On 2026-07-02, a follow-up attempt explicitly targeted NPU3 at the operator's
request. Preflight showed NPU3 had no running NPU process and port `18383` was
free. Three vLLM-HUST launches loaded model weights on NPU3 but failed during
EngineCore startup with `RuntimeError: Engine core initialization failed`. This
was recorded as a `real-online bring-up failure`, not as reducer quality or
serving-throughput evidence.

On 2026-07-05, NPU3 was tested again with the same isolation rule: only device 3
was made visible, port `18383` was used, and the service was launched through
`vllm-hust-dev-hub/manage.sh foreground`. The first successful startup still
failed generation readiness: it globally disabled Ascend custom kernels and
also disabled chunked prefill. The endpoint could return the first token for a
simple prompt, but subsequent decode tokens degenerated into repeated
`strugg`/`性价` text. A separate low-temperature probe exposed a missing
`aclnnApplyTopKTopPCustom` symbol in the local CANN/libopapi stack.

The fixed NPU3 configuration has three important properties:

1. keep `COMPILE_CUSTOM_KERNELS=1` and use selective fallback only for missing
   local CANN symbols (`aclnnAddRmsNormBias` and `aclnnApplyTopKTopPCustom`);
2. keep chunked prefill enabled for Qwen2.5, because disabling it caused
   incorrect multi-token decode;
3. use a large enough context window for structured-output reducer prompts. The
   20k workload used `max_model_len=2048`.

The required runtime patches are narrow compatibility patches in the
vLLM-HUST/vLLM-Ascend checkout, not SAGE workload logic. SAGE records the
vLLM-Ascend-HUST side as a submodule so the experiment can be reproduced from a
specific upstream feature branch:

- base vLLM-HUST submodule path: `external/vllm-hust`
- base vLLM-HUST branch: `feature/kvplane-prefix-cache-admission`
- base vLLM-HUST pinned commit:
  `ffa12e4a7a8e09433f1105d6511121f096fe88c5`
- submodule path: `external/vllm-ascend-hust`
- branch: `feature/sage-semantic-mapreduce-npu-readiness`
- pinned commit: `339b27ad69aa12b8f56bbd1885c046be4e53c945`
- upstream PR: `vLLM-HUST/vllm-ascend-hust#101`
- dev-hub submodule path: `external/vllm-hust-dev-hub`
- dev-hub branch: `feature/sage-semantic-mapreduce-dev-hub`
- dev-hub pinned commit: `32ca8c130f237efe6adcc225831810eca2ccfbd3`
- Ascend runtime manager submodule path: `external/ascend-runtime-manager`
- Ascend runtime manager branch: `feature/sage-semantic-mapreduce-runtime-manager`
- Ascend runtime manager pinned commit:
  `40a2afed0ae7896e004cf6d0f67c0d89e7e1582b`
- Triton-Ascend-HUST submodule path: `external/triton-ascend-hust`
- Triton-Ascend-HUST branch: `feature/sage-semantic-mapreduce-triton-runtime`
- Triton-Ascend-HUST pinned commit:
  `89263bb5b68b61707d7dcdd309615b84560ff5a3`

The submodule contains the following compatibility changes:

- `external/vllm-ascend-hust/vllm_ascend/ops/layernorm.py`: add
  `VLLM_ASCEND_DISABLE_ADD_RMS_NORM_BIAS_CUSTOM_OP=1` fallback to
  `torch_npu.npu_add_rms_norm` for the missing RMSNorm-bias custom op.
- `external/vllm-ascend-hust/vllm_ascend/sample/sampler.py`: add
  `VLLM_ASCEND_DISABLE_TOP_K_TOP_P_CUSTOM_OP=1` fallback to the PyTorch
  top-k/top-p path when the Python op exists but the `libopapi.so` symbol is
  absent.
- `external/vllm-ascend-hust/vllm_ascend/patch/platform/patch_balance_schedule.py`:
  accept the current vLLM scheduler arguments.
- `external/vllm-ascend-hust/vllm_ascend/platform.py`: skip the optional
  layer-sharding validator when the current vLLM platform base class does not
  expose that helper.
- `external/vllm-ascend-hust/vllm_ascend/worker/model_runner_v1.py`: restore
  the `pin_memory` attribute expected by the Ascend runner when paired with the
  current vLLM GPU runner.
- `external/vllm-ascend-hust/vllm_ascend/compilation/graph_fusion_pass_manager.py`
  and `external/vllm-ascend-hust/vllm_ascend/compilation/passes/norm_quant_fusion_pass.py`:
  make `VLLM_ASCEND_DISABLE_ADD_RMS_NORM_BIAS_CUSTOM_OP=1` also disable graph
  fusion registrations that require `_C_ascend.npu_add_rms_norm_bias`.
- `external/ascend-runtime-manager/src/hust_ascend_manager/container.py`: honor
  `HUST_ASCEND_CONTAINER_NPU_DEVICES` so the dev-hub container can mount only
  the requested `/dev/davinci*` device nodes.
- `external/triton-ascend-hust`: pin the Triton-Ascend runtime used by
  vLLM-Ascend. The NPU3 launcher treats missing Triton backends or V1 model
  runner fallback as a startup failure, not as a valid real-online experiment
  path.
- `external/vllm-hust/vllm/v1/core/kv_cache_manager.py` and
  `external/vllm-hust/vllm/knorm/manager.py`: align local KV-cache/Knorm method
  signatures with the current vLLM core.

Before launching dev-hub, validate the SAGE-pinned runtime branches:

```bash
tools/benchmark_carrier/prepare_vllm_ascend_runtime_branch.sh
```

For a reproducible NPU3 run based only on this SAGE checkout and its
feature-branch submodules, use the one-command launcher:

```bash
tools/benchmark_carrier/run_npu3_semantic_mapreduce_experiment.sh
```

The launcher checks that runtime dependencies are independent submodule
checkouts rather than symlinks to shared `$HOME` repositories, validates the
pinned commits, verifies that port `18383` and NPU3 are free, starts the
endpoint through `external/vllm-hust-dev-hub/manage.sh`, passes
`HUST_ASCEND_CONTAINER_NPU_DEVICES=3` to the runtime manager so the container
mounts only the requested NPU device, and fails fast if any managed container
process appears outside NPU3 while the service starts. It also scans the vLLM
startup log and fails if Triton-Ascend is unavailable or vLLM falls back to the
V1 model runner. It then runs a smoke request, runs a small online latency
probe, runs the LLM reducer workload, writes metadata and logs under
`.sage/benchmarks/real_online_semantic_mapreduce/`, and stops the service it
started unless `--keep-server` is passed.

For manual debugging, use the dev-hub launcher, not a manual container command:

```bash
cd external/vllm-hust-dev-hub

VLLM_ENGINE_CONTAINER=sage-lsa-npu3-qwen25-7b \
VLLM_ENGINE_RECREATE_CONTAINER=false \
VLLM_ENGINE_MODEL_PATH=/data/shared_models/Qwen2.5-7B-Instruct \
VLLM_ENGINE_SERVED_MODEL_NAME=qwen25-7b-lsa-npu3 \
VLLM_ENGINE_PORT=18383 \
VLLM_ENGINE_TP_SIZE=1 \
VLLM_ENGINE_NPU_DEVICES=3 \
ASCEND_RT_VISIBLE_DEVICES=3 \
ASCEND_VISIBLE_DEVICES=3 \
VLLM_ENGINE_MAX_MODEL_LEN=2048 \
VLLM_ENGINE_MAX_NUM_BATCHED_TOKENS=2048 \
VLLM_ENGINE_MAX_NUM_SEQS=1 \
VLLM_ENGINE_GPU_MEM_UTIL=0.70 \
VLLM_ENGINE_ENABLE_PREFIX_CACHING=0 \
VLLM_ENGINE_ENABLE_CHUNKED_PREFILL=1 \
VLLM_ENGINE_ENFORCE_EAGER=1 \
COMPILE_CUSTOM_KERNELS=1 \
VLLM_ASCEND_DISABLE_ADD_RMS_NORM_BIAS_CUSTOM_OP=1 \
VLLM_ASCEND_DISABLE_TOP_K_TOP_P_CUSTOM_OP=1 \
VLLM_KNORM_ENABLED=0 \
VLLM_KNORM_COMPRESSION_RATIO=1.0 \
VLLM_SEGMENT_REUSE_ENABLE=0 \
VLLM_ENGINE_EXTRA_ENV_PREFIXES=VLLM_KNORM_,VLLM_SEGMENT_REUSE_,VLLM_ASCEND_ \
VLLM_ENGINE_EXTRA_ARGS_JSON='["--generation-config","vllm","--structured-outputs-config","{\"backend\":\"xgrammar\",\"disable_any_whitespace\":true}"]' \
VLLM_PLUGINS=ascend \
VLLM_ENGINE_PYTHON=/workspace/vllm-hust-dev-container-env/bin/python \
VLLM_ENGINE_BIN=/workspace/vllm-hust-dev-container-env/bin/vllm \
VLLM_ENGINE_PYTHONPATH=/workspace/SAGE/external/triton-ascend-hust/python/triton_kernels:/workspace/SAGE/external/triton-ascend-hust/python:/workspace/SAGE/external/vllm-hust:/workspace/SAGE/external/vllm-ascend-hust \
bash manage.sh foreground
```

After startup, `/health` returned 200 and logs confirmed `visible_npus=[3]`.
The repaired endpoint passed both minimal JSON and structured incident JSON
readiness:

| probe | status | latency ms | artifact |
| --- | --- | ---: | --- |
| minimal JSON with `--simple-prompt` | ok | 618.12 | `.sage/benchmarks/llm_json_readiness/20260705T-npu3-qwen25-7b-fixed-chunked-simple-json.json` |
| incident JSON, xgrammar structured output | ok | 3,079.92 | `.sage/benchmarks/llm_json_readiness/20260705T-npu3-qwen25-7b-fixed-chunked-structured-output.json` |

The repaired NPU3 endpoint also completed real-online LLM reducer workloads:

| run | events | shards | max model len | precision | recall | F1 | SemanticReduce ms | artifact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| LLM reducer smoke | 2,000 | 4 | 1,024 | 1.0 | 0.25 | 0.4 | 3,281.30 | `.sage/benchmarks/large_scale_analysis_llm_reducer/20260705T-npu3-qwen25-7b-fixed-chunked-2k/report.json` |
| LLM reducer sanity | 20,000 | 8 | 2,048 | 1.0 | 1.0 | 1.0 | 13,560.25 | `.sage/benchmarks/large_scale_analysis_llm_reducer/20260705T-npu3-qwen25-7b-fixed-chunked-20k/report.json` |

Treat these as `real-online` NPU3 sanity results for the reducer integration.
They demonstrate that the live endpoint can satisfy the structured reducer
contract on NPU3 after the serving fixes. They are not a full paper-grade
serving performance study because they use one seed, one model, one NPU, and
eager execution.

Cleanup uses the dev-hub container cleanup path with the container and port
pinned:

```bash
cd external/vllm-hust-dev-hub
VLLM_ENGINE_CONTAINER=sage-lsa-npu3-qwen25-7b \
VLLM_ENGINE_PORT=18383 \
VLLM_ENGINE_AGGRESSIVE_CLEANUP=1 \
bash scripts/cleanup_vllm_hust_engine.sh
```

After cleanup, verify that `npu-smi info` shows no running process on NPU3 and
that `ss -ltnp` shows port `18383` free.

## Run

```bash
PYTHONPATH=src python tools/benchmark_carrier/run_large_scale_analysis_workload.py \
  --events 50000 \
  --shards 16 \
  --seed 7 \
  --top-k 12 \
  --reducer deterministic
```

For a larger smoke run:

```bash
PYTHONPATH=src python tools/benchmark_carrier/run_large_scale_analysis_workload.py \
  --events 100000 \
  --shards 32 \
  --seed 7 \
  --top-k 16 \
  --reducer deterministic
```

## Matrix Experiment

Use the matrix runner when collecting article/report evidence. It writes one raw
JSON file per run plus `summary.csv`, `summary.json`, and `aggregate.json`:

```bash
conda run -n esage-vllm-hust-dev env PYTHONPATH=src python \
  tools/benchmark_carrier/run_large_scale_analysis_matrix.py \
  --sizes 50000:16:12,100000:32:16 \
  --seeds 7,11,13 \
  --reducers map-only,window-aggregate,deterministic,llm-stub
```

By default, artifacts are written under:

```text
.sage/benchmarks/large_scale_analysis/<UTC_TIMESTAMP>/
```

The directory contains:

- `events*_*.json`: full raw report for each `(events, shards, seed, reducer)`
  configuration.
- `summary.csv`: compact table for spreadsheets and paper tables.
- `summary.json`: JSON version of the compact rows.
- `aggregate.json`: mean/min/max precision, recall, and F1 summaries.

You can pin a reproducible output directory name with `--run-id`:

```bash
conda run -n esage-vllm-hust-dev env PYTHONPATH=src python \
  tools/benchmark_carrier/run_large_scale_analysis_matrix.py \
  --run-id my-reproducible-run-id
```

## Baseline Result

On 2026-06-29, the initial deterministic baseline produced:

| events | shards | precision | recall | f1 | throughput events/s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 50,000 | 16 | 1.0000 | 1.0000 | 1.0000 | ~106k |
| 100,000 | 32 | 1.0000 | 0.7500 | 0.8571 | ~106k |

The 100k miss was later traced to mean-only NPU saturation detection in
`MapEvidence`, not to the global reduce stage. On 2026-07-02, adding
tail-aware `p95_npu_util` detection with a strict saturation threshold
(`p95_npu_util > 0.98`) recovered the missed scheduler incident while
preserving precision on the seed-7 100k/32-shard run.

## Current Paper Matrix

The paper matrix uses 10 seeds, two workload sizes, two `MapEvidence` policies,
and four reducer regimes:

```bash
PYTHONPATH=src python tools/benchmark_carrier/run_large_scale_analysis_matrix.py \
  --sizes 50000:16:12,100000:32:16 \
  --seeds 7,11,13,17,19,23,29,31,37,41 \
  --map-policies mean-only,tail-aware \
  --reducers map-only,window-aggregate,deterministic,llm-stub \
  --run-id 20260702T-map-policy-10seed-thr098-paper-matrix
```

Artifacts:

```text
.sage/benchmarks/large_scale_analysis/20260702T-map-policy-10seed-thr098-paper-matrix/
```

Tail-aware policy summary across 20 runs. The `outputs / true incident` column
is the semantic-efficiency metric used in Figure 1: lower values mean fewer
local/window fragments reach downstream explanation, LLM reduction, or human
review.

| reducer | mean precision | mean recall | mean F1 | mean detections | outputs / true incident |
| --- | ---: | ---: | ---: | ---: | ---: |
| map-only | 0.1990 | 0.6875 | 0.3075 | 14.00 | 3.50 |
| window-aggregate | 0.5696 | 0.9750 | 0.7129 | 7.05 | 1.76 |
| deterministic | 0.9500 | 0.9750 | 0.9579 | 4.15 | 1.04 |
| llm-stub | 0.9500 | 0.9750 | 0.9579 | 4.15 | 1.04 |

Map-policy ablation for the deterministic reducer:

| size | map policy | mean precision | mean recall | mean F1 | missed runs |
| --- | --- | ---: | ---: | ---: | ---: |
| 50k/16/12 | mean-only | 0.9200 | 0.9750 | 0.9413 | 1/10 |
| 50k/16/12 | tail-aware | 0.9200 | 0.9750 | 0.9413 | 1/10 |
| 100k/32/16 | mean-only | 0.9750 | 0.9250 | 0.9464 | 3/10 |
| 100k/32/16 | tail-aware | 0.9800 | 0.9750 | 0.9746 | 1/10 |

The main takeaway is not that tail-aware mapping always wins. A loose p95
threshold created false positives during tuning. The useful result is that the
operator boundary exposes where the failure occurs: mean-only mapping drops
some saturation evidence before the reducer can see it, while incident-level
reduction removes duplicate local/window alerts after evidence is preserved.

## Historical eSAGE Matrix Result

On 2026-06-30, the matrix runner was executed in the cloned
`esage-vllm-hust-dev` environment with:

```bash
conda run -n esage-vllm-hust-dev env PYTHONPATH=src python \
  tools/benchmark_carrier/run_large_scale_analysis_matrix.py \
  --sizes 50000:16:12,100000:32:16 \
  --seeds 7,11,13 \
  --reducers map-only,window-aggregate,deterministic,llm-stub \
  --run-id 20260630T-sota-proxy-baselines
```

The complete local artifacts are in:

```text
.sage/benchmarks/large_scale_analysis/20260630T-sota-proxy-baselines/
```

Summary:

| reducer | mean precision | mean recall | mean F1 | interpretation |
| --- | ---: | ---: | ---: | --- |
| map-only | 0.1459 | 0.5000 | 0.2250 | alert-style baseline; emits duplicate shard-local candidates |
| window-aggregate | 0.6432 | 0.9583 | 0.7600 | windowed analytics baseline; recovers incidents but over-reports windows |
| deterministic | 0.9333 | 0.9583 | 0.9392 | SAGE incident-level reducer; clusters adjacent evidence into incidents |
| llm-stub | 0.9333 | 0.9583 | 0.9392 | identical to deterministic fallback; not a real LLM result |

Across all six deterministic configurations, mean precision is 0.9333, mean
recall is 0.9583, and mean F1 is 0.9392. The `llm-stub` reducer has the same
scores because it intentionally delegates evidence fusion to the deterministic
baseline. These results should therefore be used to motivate a future real LLM
semantic reducer, not as evidence that an LLM reducer already improves quality.

The comparison baselines are diagnostic proxies, not full SOTA system
implementations. They are meant to isolate the value of semantic reduction under
the same generator, map outputs, evidence schema, and scorer. A full comparison
against Spark/Flink/Ray/LangGraph/LlamaIndex/AutoGen-style systems would require
adapters that feed those systems the same evidence objects and evaluate their
outputs with the same incident matcher.

## Historical Adapter-Level Comparison

The adapter comparison fixes the generator, evidence schema, deterministic
incident reducer, and scorer, then changes only the orchestration/product
wrapper:

- `sage-local`: the native local SAGE workload path.
- `ray-local`: Ray local tasks execute shard maps, then the same reducer scores
  the same incident schema.
- `langgraph-local`: a LangGraph `StateGraph` wraps generation, map, and reduce
  nodes.
- `llamaindex-docstore`: LlamaIndex-core `Document` objects and a
  `SimpleDocumentStore` package evidence before the same reducer runs.

Install optional dependencies through the setup script with
`--with-adapter-comparison`, then run the current 10-seed adapter baseline:

```bash
conda run -n esage-vllm-hust-dev env PYTHONPATH=src python \
  tools/benchmark_carrier/run_large_scale_analysis_adapter_comparison.py \
  --sizes 50000:16:12,100000:32:16 \
  --seeds 7,11,13,17,19,23,29,31,37,41 \
  --map-policy tail-aware \
  --reducer deterministic \
  --adapters sage-local,ray-local,langgraph-local,llamaindex-docstore \
  --run-id 20260702T-adapter-baselines-tailaware-10seed \
  --continue-on-error
```

Artifacts are in:

```text
.sage/benchmarks/large_scale_analysis_adapters/20260702T-adapter-baselines-tailaware-10seed/
```

Current 2026-07-02 10-seed tail-aware summary:

| adapter | mean F1 | mean throughput events/s | mean map ms | mean total ms |
| --- | ---: | ---: | ---: | ---: |
| sage-local | 0.9579 | 58,136 | 167.97 | 1,303.22 |
| langgraph-local | 0.9579 | 58,184 | 168.42 | 1,299.13 |
| llamaindex-docstore | 0.9579 | 57,868 | 172.53 | 1,304.96 |
| ray-local | 0.9579 | 39,100 | 800.61 | 1,917.48 |

All adapters have identical quality because this experiment intentionally fixes
the reducer and scorer. The comparison measures adapter/integration overhead,
not semantic quality and not tuned SOTA capability. Ray-local reported NPU
detection warnings (`acl` was unavailable in the conda environment) and
`/tmp/ray` space pressure warnings on this host, so its local overhead should be
used as diagnostic evidence only.

Historical 2026-06-30 adapter results are preserved in:

```text
.sage/benchmarks/large_scale_analysis_adapters/20260630T-adapter-comparison-steady/
```

The 2026-06-30 multi-seed result is useful historical evidence for claim
discipline:

- The 50k seed 11/13 cases show false positives, so the workload is not a
  guaranteed-perfect benchmark.
- The 100k seed 7 case shows a false negative (`incident-3`), so recall is not
  saturated.
- The deterministic and `llm-stub` equivalence confirms that `llm-stub` is only
  an integration placeholder.

## Positioning

This workload is meant to show that SAGE can sit above data systems as an
AI-native orchestration layer:

- external systems can do scans, joins, vector retrieval, or distributed compute;
- SAGE coordinates the map/reduce-style analysis stages;
- an LLM can be inserted at the reduce/explain stage to produce structured,
  auditable conclusions.
