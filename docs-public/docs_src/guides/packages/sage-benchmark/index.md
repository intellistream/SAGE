# sage-benchmark

Performance & evaluation suites for the SAGE framework (Layer L5).

> Use these benchmarks to validate RAG pipelines, memory services, LibAMM kernels, and scheduler
> configurations. All suites live under `packages/sage-benchmark/src/sage/benchmark/` and share the
> `sage.benchmark` namespace.

## Overview

| Suite               | Module                               | Focus                                                                           | Typical Commands                                                                                                                              |
| ------------------- | ------------------------------------ | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| RAG Benchmark       | `sage.benchmark.benchmark_rag`       | Retrieval-Augmented Generation pipelines (dense / sparse / hybrid / multimodal) | `python -m sage.benchmark.benchmark_rag.evaluation.pipeline_experiment`<br>`python -m ...implementations.pipelines.qa_dense_retrieval_milvus` |
| Memory Benchmark    | `sage.benchmark.benchmark_memory`    | SAGE Memory Service throughput / latency experiments                            | `python -m sage.benchmark.benchmark_memory.experiment.run_memory_experiment`                                                                  |
| LibAMM Benchmark    | `sage.benchmark.benchmark_libamm`    | C++ Approximate Matrix Multiplication micro-benchmarks                          | `cmake .. && cmake --build .`<br>`python pythonTest.py`                                                                                       |
| Scheduler Benchmark | `sage.benchmark.benchmark_scheduler` | Scheduler policy comparison (local vs Ray)                                      | `python -m sage.benchmark.benchmark_scheduler.scheduler_comparison`                                                                           |

All suites depend on the shared data repository `packages/sage-benchmark/src/sage/data/` (git
submodule). Make sure you run `./quickstart.sh --dev --yes` or
`./tools/maintenance/sage-maintenance.sh submodule init` before executing benchmarks.

## Installation

```bash
pip install -e packages/sage-benchmark
# Optional extras
pip install -e "packages/sage-benchmark[dev]"      # tooling + CI deps
pip install -e "packages/sage-benchmark[video]"    # CLIP / vision deps (RAG multimodal)
pip install -e "packages/sage-benchmark[milvus]"   # Milvus client + pymilvus
```

## RAG Benchmark (`benchmark_rag`)

- **Structure**: `implementations/` (individual pipelines), `evaluation/` (orchestrated
  experiments), `config/` (YAML settings), `data/` (queries + knowledge base).
- **Features**:
  - Dense / sparse / hybrid retrieval for Milvus, ChromaDB, FAISS
  - Multimodal fusion (`qa_multimodal_fusion.py`)
  - Experiment harness (`evaluation/pipeline_experiment.py`, `evaluate_results.py`)
- **Quick start**:

```bash
# Build local Chroma index
python -m sage.benchmark.benchmark_rag.implementations.tools.build_chroma_index

# Run dense retrieval pipeline
python -m sage.benchmark.benchmark_rag.implementations.pipelines.qa_dense_retrieval_milvus

# Execute full benchmark suite
python -m sage.benchmark.benchmark_rag.evaluation.pipeline_experiment --config evaluation/config/experiment_config.yaml
```

- **Data** lives under `packages/sage-benchmark/src/sage/data/qa/`. The repo ships sample
  `queries.jsonl` and `qa_knowledge_base.*` files; you can swap them by editing the config files.

## Memory Benchmark (`benchmark_memory`)

- **Goal**: Measure SAGE Memory Service performance (read/write latency, retention window, TTL
  behaviour).
- **Layout**: `experiment/` (drivers & configs), `evaluation/` (parsers, plotters).
- **Command**:

```bash
python -m sage.benchmark.benchmark_memory.experiment.run_memory_experiment --config experiment/configs/default.yaml
```

- **Status**: README placeholder exists; contribute experiment docs by logging scenarios (dataset,
  load profile, target metrics) back into `docs/dev-notes/l5-benchmark/` and linking here.

## LibAMM Benchmark (`benchmark_libamm`)

- **Goal**: Benchmark *Library for Approximate Matrix Multiplication* kernels.
- **Prerequisites**: `cmake`, `g++`, BLAS/LAPACK (OpenBLAS recommended), plus the `libamm-benchmark`
  datasets from the `sageData` submodule
  (`packages/sage-benchmark/src/sage/data/libamm-benchmark/`).
- **Workflow**:

```bash
cd packages/sage-benchmark/src/sage/benchmark/benchmark_libamm
mkdir -p build && cd build
cmake ..
cmake --build .
./benchmark_amm  # example binary
# Or python helper
python ../pythonTest.py --config ../config.csv
```

- **Artifacts**: plots in `figures/`, configuration permutations in `perfLists/`, raw CSV metrics in
  `perfListEvaluation.csv`.

## Scheduler Benchmark (`benchmark_scheduler`)

- **Purpose**: Compare scheduling strategies (local queue vs remote Ray, etc.) using shared code
  with `examples/tutorials/L2-platform/scheduler`.
- **Entry**:

```bash
python -m sage.benchmark.benchmark_scheduler.scheduler_comparison --runs 5 --mode ray
```

- **Extending**: Add new strategies in the module and update `docs/dev-notes/l5-benchmark/README.md`
  with a short summary + test tags.

## Testing & Metadata

- Use `@test_category: benchmark`, `@test_speed: slow`, and `@test_skip_ci: true` annotations at the
  top of long-running scripts.
- Smoke tests can be registered in `packages/sage-benchmark/tests/` and opt into CI by lowering
  dataset sizes.

## Related Documentation

- Internal notes: `docs/dev-notes/l5-benchmark/README.md`
- Tutorials (L5 Apps): `examples/tutorials/L5-apps/`
- Data repo: `packages/sage-benchmark/src/sage/data/`
- Contribution guide: `CONTRIBUTING.md`
