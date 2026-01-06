# SAGE Systems-Paper Writing Prompts

This directory hosts **writing prompts and experiment outlines** for papers about the **SAGE
system** targeting top-tier machine learning systems venues (for example, the Machine Learning
Systems tracks at major conferences such as ICML).

These prompts are intended for papers that:

- treat SAGE as a **full dataflow-based ML systems platform**, not just an LLM control plane;
- cover the **entire SAGE stack**: layered architecture, declarative dataflow, storage/DB and
  time-series components, LLM & embedding control plane, heterogeneous deployment, and benchmarking;
- leverage SAGE as a **benchmarking and experimentation testbed**, including `benchmark_agent`,
  `benchmark_control_plane`, `benchmark_db`, `benchmark_rag`, `benchmark_scheduler`,
  `benchmark_refiner`, `benchmark_libamm`, `benchmark_sage` (memory benchmarks now live in the
  Neuromem repository).

> Note: SAGE is **not** only an LLM inference / control-plane engine. The control plane is one
> subsystem. SAGE also provides dataflow-oriented components such as `sage.db`, `sage.flow`,
> `sage.tsdb`, and other services that are connected via SAGE's declarative dataflow model, as well
> as platform, kernel, and middleware layers.

The Markdown files in this directory (and under `docs/icml-prompts/` in the repo root) provide
per-section prompts for a full systems paper:

- Abstract, Introduction, Related Work, System / Method, Experiments, Discussion, Conclusion;
- contributions lists and concrete system-design outlines for the **whole SAGE system**;
- experiment design prompts for different SAGE subsystems (control plane, dataflow pipelines,
  storage/DB, time-series DB, agent layer, scheduler, etc.).

You can either:

- use the root-level `docs/icml-prompts/` files directly, or
- copy/adapt them into paper-specific subfolders under `benchmark_sage/docs/` for particular
  submissions about SAGE.
