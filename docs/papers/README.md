# SAGE Paper And Artifact Index

This directory currently contains one formal paper line and several supporting
artifacts. Keep the distinction explicit: the repository is the SAGE core
framework, while the current paper-facing work is the Semantic MapReduce study.

## Formal Paper Drafts

| Paper line | Status | Main files | Scope |
| --- | --- | --- | --- |
| Semantic MapReduce | Active ASPLOS-style systems paper | `docs/papers/semantic_mapreduce/main.tex`, `docs/papers/semantic_mapreduce/main.pdf`, `docs/papers/semantic_mapreduce/README.md` | SAGE as an orchestration layer for large-scale LLM-native data analysis: shard evidence extraction, semantic incident reduction, audit traces, and real-online reducer readiness. |

There are no other first-class LaTeX paper directories under `docs/papers/` at
the moment. If a new paper starts from SAGE, give it its own directory here and
add a row to this table before adding experiment-specific code.

## Supporting Article Drafts

| Artifact | Role | Notes |
| --- | --- | --- |
| `docs/semantic-mapreduce-article.md` | Chinese/English technical article draft and slide outline | Use as framing material for talks or internal writing. It is not the canonical submission source. Keep claims aligned with the evidence recorded by the paper README and workload document. |
| `roadmap.md` | Current execution roadmap for the Semantic MapReduce paper branch | Tracks NPU3 runtime bring-up, paper-ready evidence, and next engineering steps. Treat it as operational planning, not a paper artifact. |
| `docs/large-scale-analysis-workload.md` | Workload and reproduction guide | Describes the synthetic workload, reducer ladder, adapter probes, real-online reducer runs, and evidence boundaries. This is the main companion document for experiment interpretation. |

## Code Ownership Map

| Code area | Owned paper line | Purpose | Notes |
| --- | --- | --- | --- |
| `src/sage/workloads/large_scale_analysis.py` | Semantic MapReduce | Synthetic NPU-backed LLM serving telemetry workload, reducer implementations, scoring, and CLI entrypoint. | This is the core paper workload code. The `llm-stub` reducer is CI-safe only; the `llm-openai` reducer is the real OpenAI-compatible reducer path. |
| `tools/benchmark_carrier/run_large_scale_analysis_workload.py` | Semantic MapReduce | Thin CLI wrapper around the workload module. | Use for single workload runs. |
| `tools/benchmark_carrier/run_large_scale_analysis_matrix.py` | Semantic MapReduce | Multi-seed, multi-scale reducer matrix runner. | Produces `.sage/benchmarks/large_scale_analysis/...` artifacts. |
| `tools/benchmark_carrier/run_large_scale_analysis_adapter_comparison.py` | Semantic MapReduce | Adapter comparison harness for SAGE-local, Ray-local, LangGraph-local, and LlamaIndex docstore wrappers. | These are adapter probes, not full external-system comparisons. |
| `tools/benchmark_carrier/probe_llm_json_readiness.py` | Semantic MapReduce | OpenAI-compatible JSON readiness probe for real LLM reducers. | Use before reporting `llm-openai` reducer results. |
| `tools/benchmark_carrier/run_npu3_semantic_mapreduce_experiment.sh` | Semantic MapReduce | One-command NPU3 real-online launcher. | Starts the pinned vLLM-HUST stack, runs smoke/probe/reducer workloads, records provenance, and confines the run to NPU3 by default. |
| `tools/benchmark_carrier/openai_replay_carrier.py` and `run_vllm_hust_online_benchmark.py` | Semantic MapReduce support | Real endpoint replay and baseline serving probes. | These support readiness and cost accounting; do not describe them as the primary paper contribution. |
| `tools/benchmark_carrier/setup_esage_conda_env.sh` | Semantic MapReduce support | Builds the `esage-vllm-hust-dev` experiment environment on top of the vLLM-HUST development stack. | Do not create local virtualenvs for SAGE. |
| `tools/benchmark_carrier/bootstrap_triton_ascend_runtime.sh` and `prepare_vllm_ascend_runtime_branch.sh` | Semantic MapReduce runtime support | Validate and prepare the pinned Ascend/vLLM runtime submodules. | Runtime fixes belong in the corresponding submodules, not in shared home-directory checkouts. |
| `src/tests/test_large_scale_analysis_workload.py` | Semantic MapReduce | Unit coverage for workload generation, reducer behavior, scoring, and OpenAI-compatible reducer parsing. | Run after workload or reducer changes. |
| `src/tests/test_benchmark_carrier_stub.py` and `src/tests/test_openai_replay_carrier.py` | Semantic MapReduce support | Coverage for benchmark carrier wiring and replay helpers. | Run after carrier script changes. |

## Runtime Submodules

The Semantic MapReduce NPU3 path depends on repository-pinned runtime submodules:

| Submodule | Role |
| --- | --- |
| `external/vllm-hust` | vLLM-HUST runtime source used by the paper-facing serving path. |
| `external/vllm-ascend-hust` | Ascend runtime integration for vLLM-HUST. |
| `external/vllm-hust-dev-hub` | Managed launcher and environment preparation entrypoint. |
| `external/triton-ascend-hust` | Triton-Ascend runtime required by the NPU path. |
| `third_party/ascend-runtime-manager` | Container/device/CANN/torch_npu runtime management. |

Do not replace these with symlinks to shared checkouts. If a runtime fix is
needed for the paper, port it into the appropriate submodule feature branch and
then advance the parent repository's submodule pointer.

## Result Artifact Classes

| Artifact root | Paper line | Evidence level | Commit policy |
| --- | --- | --- | --- |
| `.sage/benchmarks/large_scale_analysis/` | Semantic MapReduce | Synthetic reducer matrix results. | Usually local/generated; commit only curated summaries or explicitly requested reproduction artifacts. |
| `.sage/benchmarks/large_scale_analysis_adapters/` | Semantic MapReduce | Adapter-probe results with fixed reducer/scorer. | Treat as diagnostic evidence, not SOTA comparison data. |
| `.sage/benchmarks/large_scale_analysis_llm_reducer/` | Semantic MapReduce | Real `llm-openai` reducer runs against OpenAI-compatible endpoints. | Record provenance before citing. Commit only curated paper artifacts. |
| `.sage/benchmarks/real_online_semantic_mapreduce/` | Semantic MapReduce | NPU3 end-to-end readiness and reducer runs. | Paper-ready only when smoke, online probe, reducer JSON, NPU audit, and service logs are present. |

## Non-Semantic-MapReduce Code

The core SAGE package also contains general framework code that is not owned by
the current paper line:

- `src/sage/foundation/`: foundation contracts, config, logging, and shared utilities.
- `src/sage/stream/`: dataflow/stream API surface.
- `src/sage/runtime/`: local and FlowNet-backed runtime integration.
- `src/sage/serving/`: serving integration contracts and gateway surfaces.
- `src/sage/edge/`: edge-facing application/server utilities.

These modules may be cited by the Semantic MapReduce paper as system substrate,
but changes there should be justified as SAGE framework work, not paper-specific
experiment code.

## Adding A New Paper Line

When a second SAGE paper line becomes active:

1. Create `docs/papers/<paper_slug>/` with the paper source and README.
2. Add the paper to the Formal Paper Drafts table above.
3. Add code ownership rows for any new workload, benchmark carrier, tests, and runtime submodules.
4. Keep generated `.sage/benchmarks/...` output out of Git unless it is a curated artifact for a specific claim.
5. State the evidence boundary before writing paper claims.