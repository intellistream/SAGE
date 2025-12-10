# ICML System Track – SAGE-as-a-Platform Prompt Overview

This folder provides **ICML Machine Learning Systems track** prompts that treat SAGE explicitly as a
**full dataflow-based ML systems platform**, not only as an LLM/embedding control plane.

Key reminders for all prompts in this folder:

- SAGE includes multiple subsystems that are orchestrated by a declarative **dataflow model**:
  - `sage.flow` – dataflow / pipeline construction and orchestration;
  - `sage.db` – storage / retrieval components integrated into SAGE pipelines;
  - `sage.tsdb` – time-series database / monitoring components;
  - LLM & embedding **control plane** (`sage.common.components.sage_llm`, `sage-gateway`) as one
    important but not exclusive subsystem;
  - additional middleware and services that plug into the same dataflow.
- The goal of the paper is to present SAGE as an **end-to-end systems platform** where these
  components can be composed, scheduled, observed, and benchmarked in a unified way.

The subsequent markdown files define per-section prompts (Abstract, Introduction, System,
Experiments, etc.) that:

- emphasize SAGE's *dataflow model* and its role in wiring together `sage.flow`, `sage.db`,
  `sage.tsdb`, and the control plane;
- treat benchmark suites (including `benchmark_sage` and other `sage-benchmark` subpackages) as
  **testbeds** for a *family* of systems experiments, not only control-plane scheduling;
- encourage experiment designs that span multiple subsystems.
