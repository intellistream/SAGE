# Abstract Prompt – SAGE as a Dataflow-Centric Platform

Use this prompt when you want the ICML abstract to emphasize SAGE as a **dataflow-centric ML systems
platform** that unifies LLM/embedding control, storage, and monitoring.

______________________________________________________________________

You are an experienced ICML systems-track author. Help me write an abstract for a paper about
**SAGE**, a dataflow-based ML systems platform.

--- System context ---

- Venue: ICML – Machine Learning Systems track.
- System: SAGE, a Python 3.10+ framework organized into six layers and built around a declarative
  **dataflow model** that connects multiple subsystems:
  - `sage.flow` for constructing and running ML/LLM pipelines;
  - `sage.db` for storage and retrieval within these pipelines;
  - `sage.tsdb` for logging, monitoring, and time-series analysis;
  - an LLM & embedding control plane (`sage.common.components.sage_llm`, `sage-gateway`) managing
    inference workloads;
  - middleware and operators (`sage-middleware`), platform services (`sage-platform`), and
    user-facing tools (`sage-cli`, `sage-studio`, `sage-tools`).

--- Writing goals --- Please draft a 150–200 word English abstract that:

1. Frames the **problem** as managing complex ML/LLM pipelines that span data processing, storage,
   inference, and monitoring, not just single-model serving.
1. Describes SAGE as a **dataflow platform** that:
   - offers a declarative way to compose `sage.flow`, `sage.db`, `sage.tsdb`, and control-plane
     components;
   - provides system-level support for heterogeneous CPU/GPU deployments;
   - exposes consistent interfaces for building and experimenting with ML/LLM applications.
1. States 2–4 **systems contributions**, for example:
   - a layered, dataflow-based architecture that unifies multiple subsystems;
   - an extensible control plane that is one instance of the dataflow model;
   - benchmark suites (including `benchmark_sage`) that treat SAGE as a reusable testbed for
     platform-level experiments.
1. Mentions **experimental evidence** that covers multiple subsystems (e.g., end-to-end pipelines
   that use `sage.flow` + `sage.db` + `sage.tsdb`
   - the control plane), reporting throughput/latency, resource utilization, and
     observability/monitoring overhead.

Style constraints:

- ICML-style academic English, neutral and technical.
- Keep the focus on SAGE as a **platform**; the control plane is a key example but not the whole
  story.
