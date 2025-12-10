# SAGE ICML Writing Prompts (System Track)

This directory hosts **writing prompts and experiment outlines** for ICML papers about the **SAGE
system**.

These prompts are intended for:

- the ICML *Machine Learning Systems* track;
- papers that treat SAGE as a **full dataflow-based ML systems platform**, not just an LLM control
  plane;
- work that leverages SAGE as a **benchmarking and experimentation testbed** (e.g.,
  `benchmark_agent`, `benchmark_control_plane`, `benchmark_db`, `benchmark_rag`, `benchmark_memory`,
  `benchmark_scheduler`, `benchmark_refiner`, `benchmark_libamm`, `benchmark_sage`).

> Note: SAGE is **not** only an LLM inference/control-plane engine. The control plane is one
> subsystem. SAGE also provides dataflow-oriented components such as `sage.db`, `sage.flow`,
> `sage.tsdb`, and other services that are connected via SAGE's declarative dataflow model.

The Markdown files in this directory (and under `docs/icml-prompts/` in the repo root) provide
per-section prompts for:

- Abstract, Introduction, Related Work, System/Method, Experiments, Discussion, Conclusion;
- contributions lists and concrete system-design outlines;
- experiment design prompts for different SAGE subsystems (control plane, dataflow pipelines,
  storage/DB, time-series DB, etc.).

You can either:

- use the root-level `docs/icml-prompts/` files directly, or
- copy/adapt them into paper-specific subfolders under `benchmark_sage/docs/` for particular ICML
  submissions.
