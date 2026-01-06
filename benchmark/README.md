# benchmark_sage – SAGE System-Level Benchmarks and ICML Artifacts

`benchmark_sage` is a home for **system-level benchmarks and artifacts** that focus on SAGE as a
complete ML systems platform.

Key points:

- SAGE is **more than an LLM control plane**. The LLM/embedding control plane is one subsystem. SAGE
  also includes components such as `sage.db`, `sage.flow`, `sage.tsdb`, and others, all orchestrated
  via a common **declarative dataflow model**.
- `packages/sage-benchmark` already contains multiple benchmark suites (agents, control-plane
  scheduling, DB, retrieval, memory, schedulers, refiner, libamm, etc.). `benchmark_sage` can
  aggregate **cross-cutting experiments** that involve several SAGE subsystems together.
- This folder may also store **ICML writing prompts and experiment templates** for the SAGE system
  track papers, under `docs/`.

Suggested uses:

- End-to-end experiments that span `sage.flow` pipelines, `sage.db` storage, `sage.tsdb` time-series
  monitoring, and the LLM/embedding control plane.
- Configs (`config/*.yaml`) for system-track experiments described in an ICML paper.
- Notebook or script entry points that reproduce figures/tables.

At the repo root, `docs/icml-prompts/` contains reusable writing prompts. You can either reference
them directly or copy customized versions into this folder when preparing a specific ICML
submission.
