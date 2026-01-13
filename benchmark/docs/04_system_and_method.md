# System / Method Prompts – SAGE Systems Paper

本文件面向系统论文的 "System / Method" 章节，帮助你把 **整个 SAGE 系统** 的设计讲清楚，突出实现与可扩展性，而不是只强调 control plane。

______________________________________________________________________

## 4.1 设计 System 章节结构

**提示词（可直接复制）**

You are a systems-track co-author responsible for the **System Design / Method** section of a paper
about **SAGE**.

--- System context ---

SAGE is a Python 3.10+ framework for building LLM/AI data processing pipelines. It targets
**system-level issues** such as scalability, heterogeneous hardware, unified management of LLM and
embedding workloads, and reproducible experimentation.

Key design aspects to consider:

- **Layered architecture (L1–L5)** with **no upward dependencies**:
  - L1: `sage-common` – foundational utilities, configuration, user paths (XDG), port management
    (`SagePorts`), shared components.
  - L2: `sage-platform` – platform services (storage, queuing, service management), cluster
    configuration via `config/cluster.yaml`.
  - L3: `sage-kernel`, `sage-libs` – core execution engine, **job management**
    (`runtime/job_manager`), **node selection** (`scheduler/node_selector`), algorithms, scheduling
    logic, CPU/GPU awareness.
  - L4: `sage-middleware` – C++ operators and performance-critical components, built via CMake.
  - L5: `sage-cli`, `sage-tools` – user-facing interfaces (CLI, development tools).
- **Independent repositories** (not in core architecture):
  - `sage-benchmark` – benchmark suites (PyPI: `isage-benchmark`)
  - `sage-examples` – applications and tutorials
  - `sageLLM` – LLM inference engine with control plane (PyPI: `isagellm`)
- **Declarative dataflow** abstraction for specifying pipelines, with compilation/execution over
  heterogeneous resources.
- **Unified LLM & embedding control plane** (sageLLM): `UnifiedInferenceClient`,
  `ControlPlaneManager`, `HybridSchedulingPolicy`, `EmbeddingExecutor` coordinating multiple vLLM
  and embedding backends via `isagellm.gateway`.
- **User paths and configuration** following XDG base directory spec; project-level `.sage/`
  directory for build artifacts and caches.
- **Deployment and CI** patterns (quickstart scripts, `sage-dev` tooling, pre-commit hooks) as
  concrete implementation and reproducibility choices.

--- Task ---

Design a **System / Method section outline** tailored for a top-tier systems paper. The section
should likely include 3–5 main subsections, for example:

- System Overview and Design Goals;
- Layered Architecture;
- Declarative Dataflow and Execution Model;
- LLM & Embedding Control Plane (sageLLM) as one important subsystem;
- Implementation Details and Deployment.

For each proposed subsection:

1. Provide a bullet list of **key questions** it should answer from a systems-reviewer perspective
   (e.g., how the system scales, how it abstracts hardware differences, how it improves
   programmability without sacrificing performance, how it supports reproducibility and
   observability).
1. Map these questions to **specific SAGE components** or modules (e.g., `sage-platform` and
   `sage-kernel` for job management and node selection, `sage.common.components.sage_llm` for
   control plane, `sage-middleware` for C++ operators, `sage-benchmark` for evaluation workloads).
1. Suggest **figures or diagrams** that should accompany this subsection (e.g., architecture
   diagram, dataflow diagram, control-plane timeline), with 1–2 sentences per figure describing what
   it should convey.
1. Indicate which subsections are **core** for the main paper and which details can be moved to an
   appendix if page limits are tight.

--- Output ---

- A structured outline with subsections and bullet points answering the above.
- No full prose yet.

______________________________________________________________________

## 4.2 逐小节撰写 System 文本

有了 4.1 的大纲后，你可以对每个小节单独调用下面的提示词写正文。

**提示词（可直接复制，每个小节复用）**

We have designed an outline for the System / Method section of our systems paper on **SAGE**. Now we
will write the subsection:

> [INSERT SUBSECTION TITLE HERE, e.g., "Layered Architecture"]

Here is the bullet-point outline for this subsection (from the previous step):

[PASTE THE BULLET-POINT OUTLINE HERE]

--- System reminders ---

- SAGE uses a **5-layer architecture (L1–L5)** with no upward dependencies.
- It exposes **declarative dataflow** to users, while deeper layers handle scheduling, optimization,
  and execution.
- It includes a **unified control plane** for LLM and embedding services (sageLLM, independent
  repo), fronted by an OpenAI-compatible gateway.
- It targets **scalability, heterogeneity (CPU/GPU), and reproducibility**.
- The paper should emphasize the **whole system** (architecture + dataflow + control plane +
  benchmarks + deployment), not just one component.

--- Task ---

Please write a detailed English subsection for a systems paper that:

1. Answers the bullet-point questions with **systems-level explanations** rather than just listing
   APIs.
1. Emphasizes how SAGE’s design choices (e.g., layering, declarative dataflow, control plane,
   benchmark integration, tooling) address concrete systems challenges (resource utilization,
   latency, cluster heterogeneity, debuggability, ease of evolution, reproducibility).
1. Includes **references to SAGE components** (module or package names) only when they help clarify
   the design (e.g., mentioning `sage-kernel` for job management and node selection, `sage-platform`
   for cluster configuration and services, `sage-benchmark` for evaluation workloads).
1. Suggests where to place figures or tables, and provides a short candidate **figure caption** if
   appropriate.

--- Output ---

1. The full text of the subsection in English (approx. 1–2 single-column pages, depending on
   importance).
1. A short list of **potential figure captions** and where they should appear.
1. Optional notes on which parts could be shortened if page limits are tight.

______________________________________________________________________

## 4.3 控制平面技术细节（可选强化）

如果你希望在系统论文中 **重点强化控制平面（sageLLM）这一子模块的系统贡献**，可以单独用下面的提示词撰写一个专门小节。注意：控制平面是 SAGE
的一个重要子系统，但论文整体仍然需要覆盖完整系统。

**提示词（可直接复制）**

We want to dedicate a focused subsection to the **LLM & embedding control plane** in SAGE
("sageLLM"). This subsection should be particularly convincing for systems reviewers who care about
**resource management, scheduling, and scalability**.

--- Control plane architecture (from actual implementation) ---

- The control plane classifies requests into chat / generation vs. embedding.
- It uses policies such as `HybridSchedulingPolicy` to batch and route requests across a pool of
  vLLM and embedding engines.
- It aims to improve **throughput, tail latency, and SLO compliance** while sharing resources across
  heterogeneous LLM and embedding workloads.
- It is integrated with `sage-gateway`, which exposes an OpenAI-compatible API on well-defined ports
  from `SagePorts`.

Key components (module paths):

- `ControlPlaneManager`: `sageLLM/control_plane/manager.py` – core orchestrator.
- `RequestClassifier`: `sageLLM/control_plane/request_classifier.py` – request type detection.
- `HybridSchedulingPolicy`: `sageLLM/control_plane/strategies/hybrid_policy.py` – scheduling
  decisions.
- `EmbeddingExecutor`: `sageLLM/control_plane/executors/embedding_executor.py` – batched embedding
  execution.

--- Scheduling algorithm details to explain ---

The prompt should guide the model to explain:

1. **Request classification** (how chat / generation / embedding are distinguished, and with what
   overhead).
1. **Scheduling policy options** (e.g., FIFO, priority, SLO-aware, hybrid) and how they trade off
   fairness, latency, and throughput.
1. **Batching strategy** for LLM vs. embedding workloads, and interaction with vLLM’s continuous
   batching.
1. **Load balancing** across multiple backend engines under mixed workloads.
1. **Interaction with vLLM**: SAGE does not replace vLLM’s internal scheduler but provides
   cross-engine and cross-workload scheduling via an OpenAI-compatible interface.

--- Task ---

Please draft a detailed English subsection (around 1–1.5 single-column pages) that:

1. Explains the **design goals** of the control plane (unified scheduling, resource sharing, SLO
   compliance).
1. Describes the **architecture** and key components and how they interact.
1. Details the **scheduling algorithm** with pseudocode or an algorithmic description for
   `HybridSchedulingPolicy`.
1. Explains how **batching** works differently for LLM vs. embedding workloads.
1. Clarifies the **relationship with vLLM** (complementary, not replacement).
1. Prepares the ground for experiments comparing different scheduling policies and baselines.

--- Output ---

1. Full subsection text with technical depth.
1. Pseudocode for the core scheduling algorithm (if appropriate).
1. Suggested figures:
   - Figure X: Control Plane Architecture (component diagram).
   - Figure Y: Request Timeline showing classification, queuing, batching, execution under mixed
     workloads.

______________________________________________________________________

## 4.4 与 vLLM 关系的澄清（重要补充）

审稿人可能会质疑 SAGE 与 vLLM（或其它 LLM 引擎）的关系。这里提供专门的澄清引导。

**提示词（可直接复制）**

A reviewer might ask: "How does SAGE relate to vLLM? Isn’t vLLM already a highly optimized LLM
serving system?"

Please draft a **clarification paragraph** (3–5 sentences) that explains:

1. **Complementarity, not competition**: SAGE uses vLLM (or other engines) as backend serving
   components. vLLM handles single-model inference optimization (PagedAttention, continuous
   batching). SAGE handles cross-model orchestration and embedding co-scheduling.
1. **Abstraction level difference**:
   - vLLM = single-model inference engine (optimizes GPU memory, batch processing for one model).
   - SAGE = pipeline-level control plane and systems platform (orchestrates multiple models, handles
     embedding services, provides unified API, integrates with dataflow and benchmarks).
1. **What SAGE adds**:
   - multi-engine load balancing;
   - unified LLM + embedding scheduling;
   - request classification and SLO-aware routing;
   - declarative pipeline composition and system-level benchmarks.
1. **Concrete example**: e.g., a RAG pipeline needing an embedding service + an LLM service. Without
   SAGE, operators must manually manage two services and balance load; with SAGE, they declare the
   pipeline and the control plane plus dataflow engine handle resource allocation and scheduling.

This paragraph should be inserted in the System section after describing the control plane
architecture, and should clearly state that the **paper evaluates SAGE as a full system built on top
of such engines**.
