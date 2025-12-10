# System / Method Prompts – SAGE as a Unified Dataflow Platform

Use these prompts to write the System/Method section of an ICML paper that presents SAGE as a
unified **dataflow platform**.

______________________________________________________________________

## 4.1 Platform-Oriented System Overview

You are an ICML systems-track co-author. Help me design the **System** section for a paper about
SAGE as a dataflow-centric ML systems platform.

--- Platform context ---

- SAGE is organized into six layers with no upward dependencies, but the central abstraction that
  ties layers and subsystems together is a **declarative dataflow model**.
- Key subsystems that plug into this model include:
  - `sage.flow` for pipeline construction and orchestration;
  - `sage.db` for persistent storage and retrieval within flows;
  - `sage.tsdb` for time-series monitoring, metrics, and observability;
  - the LLM & embedding control plane for inference workloads;
  - middleware operators and platform services for scheduling and execution.

Task:

- Propose a System section outline that explicitly:
  1. Introduces the **dataflow abstraction** and how it spans `sage.flow`, `sage.db`, `sage.tsdb`,
     and the control plane;
  1. Explains how the layered architecture supports this abstraction;
  1. Details how flows are compiled, scheduled, and monitored across heterogeneous resources;
  1. Highlights extensibility points where new subsystems can be plugged into the dataflow (e.g.,
     new storage engines, monitoring backends, or inference services).

Output:

- A subsection outline (3–5 subsections) with bullet points focused on the platform-wide dataflow
  story, not just the control plane.

## 4.2 Writing Subsections (Dataflow-Aware)

When writing each subsection, remind the model that:

- The **control plane** is a concrete instance of SAGE's design, but the same dataflow and platform
  mechanisms also apply to `sage.db`, `sage.flow`, `sage.tsdb`, and other services.
- Experiments and examples should, where possible, involve **end-to-end flows** that cross subsystem
  boundaries (e.g., ingest → store → retrieve → infer → log/monitor).

You can reuse the generic prompts from `docs/icml-prompts/04_system_and_method.md` by pasting this
dataflow-centric context before them.
