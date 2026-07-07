# Semantic MapReduce Roadmap

Last updated: 2026-07-07.

## Current Status

The paper branch is `feature/semantic-mapreduce-paper`. The main technical
direction is to position SAGE as a Semantic MapReduce orchestration layer for
large-scale data analysis: shard local evidence extraction, normalize evidence
objects, group related evidence, reduce incidents semantically, and emit
auditable reports and workflow traces.

The ASPLOS-style paper draft has been reorganized around standard semantic
operators rather than a loose system narrative. The current framing is double
blind, avoids direct product-style claims, and treats SAGE as an orchestration
layer above data systems rather than a replacement for Spark, Flink, Ray, or
databases.

## Repository and Runtime State

SAGE now records the external runtime dependencies as submodules on project
feature branches:

- `external/vllm-hust`
  - branch: `feature/sage-semantic-mapreduce-vllm-runtime`
  - pinned commit: `5de748bea122fb0917adc6117fbb37429b60aa24`
- `external/vllm-hust-dev-hub`
  - branch: `feature/sage-semantic-mapreduce-dev-hub`
  - pinned commit: `7ab74990d5bfc4953d7bb1f99dfb93720e2adc81`
- `third_party/ascend-runtime-manager`
  - branch: `feature/semantic-mapreduce-runtime-integration`
  - pinned commit: `40a2afed0ae7896e004cf6d0f67c0d89e7e1582b`
- `external/vllm-ascend-hust`
  - branch: `feature/sage-semantic-mapreduce-npu-readiness`
  - pinned commit: `339b27ad69aa12b8f56bbd1885c046be4e53c945`
- `external/triton-ascend-hust`
  - branch: `feature/sage-semantic-mapreduce-triton-runtime`
  - pinned commit: `612d5772bcd4ee7a75ab4939aa3580d937147d83`

The reproducibility entry point is:

```bash
tools/benchmark_carrier/run_npu3_semantic_mapreduce_experiment.sh
```

The runtime preparation script now rejects symlinked runtime submodule paths.
The NPU3 experiment should depend on `external/*` submodules in this repository,
not on shared `$HOME/vllm-hust`, `$HOME/vllm-ascend-hust`, or
`$HOME/triton-ascend-hust` checkouts.

It prepares the pinned submodules, starts vLLM-HUST through the dev-hub
`manage.sh` path, targets port `18383`, and defaults to NPU3 only. The script
also writes metadata and runtime logs under:

```bash
.sage/benchmarks/real_online_semantic_mapreduce/
```

## Completed Engineering Work

The root partition was checked and lightly cleaned. The root filesystem is now
around 76% used. The largest remaining space consumer is Docker/containerd
state under `/var`, so further cleanup should avoid deleting active containers
or other users' services.

The dev-hub `.env` needed by the launcher was copied into the SAGE submodule
checkout at:

```bash
external/vllm-hust-dev-hub/.env
```

This file is ignored by the dev-hub repository and should not be committed.

The one-command experiment launcher now:

- refuses non-NPU3 runs unless explicitly overridden;
- checks that NPU3 and port `18383` are free before launch;
- passes `HUST_ASCEND_CONTAINER_NPU_DEVICES=3` so the runtime manager mounts
  only `/dev/davinci3` plus required control devices;
- records managed container PIDs and verifies that any managed NPU process is
  on NPU3;
- treats Triton-Ascend backend import failures or vLLM V1 model runner fallback
  as startup failures rather than acceptable experiment fallbacks;
- starts and stops the dev-hub service through `manage.sh`;
- records metadata, NPU snapshots, prepare logs, and startup logs.

The runtime-manager feature branch now supports
`HUST_ASCEND_CONTAINER_NPU_DEVICES`, which is necessary on shared machines
because the default container path mounts all `/dev/davinci*` devices.

Common runtime fixes discovered during this bring-up have also been upstreamed:

- `vLLM-HUST/vllm-hust#102` merged the source-tree Triton metadata fallback and
  Knorm `free()` signature compatibility fix.
- `vLLM-HUST/vllm-hust#103` merged the Ascend CI read-only checkout URL fix so
  self-hosted runners do not fail before tests on SSH host-key setup.
- `vLLM-HUST/vllm-hust-dev-hub#25` merged the override for the Ascend runtime
  manager source path.
- `vLLM-HUST/triton-ascend-hust#1` merged the Ascend-only Triton build/import
  compatibility fixes.

The vLLM-Ascend feature branch includes narrow compatibility fixes found during
real NPU bring-up:

- tolerate missing layer-sharding validator hooks in the paired vLLM base
  platform;
- restore the `pin_memory` attribute expected by the Ascend runner;
- make `VLLM_ASCEND_DISABLE_ADD_RMS_NORM_BIAS_CUSTOM_OP=1` also disable graph
  fusion registrations that require `_C_ascend.npu_add_rms_norm_bias`.

## Latest Real-Online Experiment

The latest attempted full bring-up run was:

```bash
.sage/benchmarks/real_online_semantic_mapreduce/20260705T173002Z-npu3-semantic-mapreduce
```

This run verified the improved device isolation:

- the dev-hub container mounted `/dev/davinci3` only;
- the managed NPU process appeared on NPU3;
- no paper-grade smoke, latency, or LLM-reducer artifacts were produced.

The service did not reach `/health` before the run was stopped. The output
directory contains startup metadata and NPU audit files, but no `smoke.json` or
LLM reducer result files. Treat this as a bring-up/debug artifact, not an
experimental result.

On 2026-07-06, the runtime was tightened so Triton-Ascend failures are no
longer accepted as an implicit fallback path. The current smoke bring-up was:

```bash
.sage/benchmarks/real_online_semantic_mapreduce/20260706T024144Z-npu3-semantic-mapreduce
```

This run validated the new failure policy: the script stopped the dev-hub
service after seeing Triton-Ascend import failure in the vLLM startup log. The
initial `triton_kernels.matmul_ogs` path issue was fixed by adding
`external/triton-ascend-hust/python/triton_kernels` to the runtime path and by
bootstrapping the Triton-Ascend runtime before launch. The next startup attempt
then failed on Triton active-driver detection (`0 active driver(s) found`),
which means the remaining issue is the Ascend Triton runtime/build environment,
not the Semantic MapReduce workload. This is also a debug artifact, not a paper
result.

Follow-up fix: `external/vllm-hust-dev-hub` commit
`7ab74990d5bfc4953d7bb1f99dfb93720e2adc81` now exports
`TRITON_NPU_COMPILER_PATH` inside the managed engine launcher after sourcing the
Ascend toolkit environment.

The first paper-usable NPU3 real-online run is:

```bash
.sage/benchmarks/real_online_semantic_mapreduce/20260706T170917Z-npu3-semantic-mapreduce
```

This run used only NPU3 through the repository submodules and produced:

- smoke request latency: 5556.71 ms;
- online probe: 8/8 successful requests, mean TTFT 68.63 ms, mean TPOT
  19.88 ms, 45.23 output tokens/s;
- 2k LLM reducer run: precision 1.0, recall 0.25, F1 0.4, reduce latency
  48626.03 ms;
- 20k LLM reducer run: precision 1.0, recall 1.0, F1 1.0, reduce latency
  5055.39 ms.

## Immediate Next Steps

1. Keep the NPU3 real-online path reproducible from repository submodules.
   Do not borrow runtime code or build artifacts from shared home-directory
   checkouts.

2. Repeat the real-online run across multiple seeds and event counts to separate
   reducer behavior from one-off endpoint variance.

3. Require these artifacts before claiming any new real-online result:
   - `smoke.json`;
   - online probe summaries;
   - LLM reducer workload JSON files;
   - `npu-smi-before.txt`, `npu-smi-current.txt`, and managed PID audit files;
   - copied vLLM service log.

4. Add a short troubleshooting section to the workload document with the known
   failure classes and their fixes:
   - wrong container mount root;
   - `.env` overriding batch-token defaults;
   - missing AddRMSNormBias custom op;
   - all-device container mounts on shared NPU hosts;
   - managed PID confinement versus whole-machine PID deltas.

5. After a successful NPU3 real-online run, update the ASPLOS draft with only
   validated claims. Do not describe the current NPU3 bring-up attempt as a
   completed experiment until smoke and reducer artifacts exist.

## Paper Roadmap

The paper should continue to focus on the operator abstraction:

- `Shard`: partition large telemetry, logs, traces, or documents into bounded
  analysis units;
- `MapEvidence`: extract local anomalies, summaries, and supporting snippets;
- `Normalize`: convert heterogeneous evidence into comparable evidence
  objects;
- `GroupEvidence`: cluster evidence that may refer to the same incident or
  hypothesis;
- `SemanticReduce`: merge, deduplicate, resolve conflicts, and rank incident
  hypotheses;
- `ReportTrace`: emit evidence-linked explanations and auditable workflow
  traces.

The next paper revision should reduce repeated prose, keep limitations concise,
and make the distinction from naive stitching visually obvious: naive stitching
connects data scripts to an agent and leaves incident equivalence unresolved,
whereas Semantic MapReduce makes evidence objects, semantic reduction, and trace
generation first-class workflow operators.

## Experiment Roadmap

The minimum useful experimental ladder is:

1. Deterministic reducer baseline on synthetic large-scale workload.
2. Adapter comparison where LangGraph, LlamaIndex, and Ray wrappers drive the
   same evidence/reducer contract, clearly labeled as adapter probes rather
   than full system evaluations.
3. Real-online NPU3 LLM reducer run through vLLM-HUST once the endpoint is
   healthy.
4. Side-by-side reducer comparison:
   deterministic reducer versus LLM reducer versus hybrid reducer.
5. Cost and latency accounting:
   map latency, reduce latency, total throughput, token usage, and evidence
   coverage.

The most important minimal enhancement remains a pluggable reducer interface
that can switch between deterministic, LLM, and hybrid reducers while sharing
the same scorer and trace format.
