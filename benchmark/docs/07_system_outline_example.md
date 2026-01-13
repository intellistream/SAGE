# SAGE – Example System / Method Outline (Systems Track)

本文件给出一份结合 SAGE 实际结构的 System / Method 章节详细纲要示例，可与 `04_system_and_method.md` 里的提示词配合使用，用来介绍 **整个 SAGE
系统**，而不仅仅是控制平面。

______________________________________________________________________

## 1. High-Level Section Structure (Example)

A possible structure for the System / Method section of the paper is:

1. **System Overview and Design Goals**
1. **Layered Architecture**
1. **Declarative Dataflow and Execution Model**
1. **LLM & Embedding Control Plane (sageLLM)**
1. **Implementation Details and Deployment**

You can merge or split sections depending on page limits (e.g., combine 2+3, or 4+5).

______________________________________________________________________

## 2. Section – System Overview and Design Goals

**Questions to answer (systems-reviewer perspective)**

- What concrete **problems** does SAGE target that existing LLM serving or MLOps systems do not
  fully solve? (e.g., complex multi-step LLM pipelines, mixed LLM+embedding workloads, CPU-only
  environments, end-to-end evaluation and reproducibility.)
- What are the **design goals**: scalability, heterogeneity support, programmability, debuggability,
  reproducibility, ease of evolution?
- How does SAGE sit in the ML systems ecosystem: is it a serving system, a workflow engine, a
  control plane, a benchmark framework, or a combination?

**SAGE components to mention**

- Overview of packages under `packages/`: `sage-common`, `sage-platform`, `sage-kernel`,
  `sage-libs`, `sage-middleware`, `sage-apps`, `sage-benchmark`, `sage-cli`, `sage-studio`,
  `sage-tools`, `sage-gateway`.
- High-level illustration of how a user goes from writing a pipeline (via CLI/Studio/examples) to
  executing it on a heterogeneous cluster using SAGE.

**Suggested figures/diagrams**

- **Figure 1: SAGE System Overview.** A block diagram showing the layers and their roles: user
  interfaces at the top, control plane and platform services in the middle, execution engines and
  operators at the bottom. Caption: *"High-level view of the SAGE system, highlighting its layered
  architecture and main components for LLM/AI pipelines."*

______________________________________________________________________

## 3. Section – Layered Architecture

**Questions to answer**

- How are the six layers defined, and what responsibilities does each layer have?
- Why enforce **no upward dependencies**? How does this help modularity, testing, and independent
  evolution?
- How does this layering compare to monolithic or ad-hoc LLM orchestration scripts or flat
  microservice designs?

**Mapping to SAGE components**

- L1 – `sage-common`: configuration (`config/config.yaml`), user paths (XDG), `SagePorts` for port
  allocation, shared components.
- L2 – `sage-platform`: platform services for storage, queuing, and service management; integration
  with cluster configuration (`config/cluster.yaml`).
- L3 – `sage-kernel`, `sage-libs`: execution kernels, job management (`runtime/job_manager`), node
  selection (`scheduler/node_selector`), CPU/GPU awareness, algorithms, and scheduling primitives.
- L4 – `sage-middleware`: C++ operators and performance-critical components.
- L5 – `sage-cli`, `sage-tools`: CLI commands (e.g., `sage llm engine start`), development tools.

**Independent repositories** (not in core architecture):

- `sage-benchmark` – benchmark scenarios (PyPI: `isage-benchmark`)
- `sage-examples` – applications and tutorials
- `sageLLM` – LLM inference engine with control plane (PyPI: `isagellm`)

**Suggested figures**

- **Figure 2: Layered Architecture.** A stacked diagram (L1 at bottom to L5 at top) with arrows only
  going downward. Caption: *"SAGE enforces a strict layering discipline with no upward dependencies,
  which simplifies reasoning about responsibilities and allows lower layers to be reused across
  tools, applications, and benchmarks."*

______________________________________________________________________

## 4. Section – Declarative Dataflow and Execution Model

**Questions to answer**

- How do users **declare** LLM/AI pipelines (e.g., composition of retrieval, tools, LLM calls,
  post-processing)?
- How does SAGE translate these declarations into an executable plan over its layers?
- How does the execution model handle **batching**, **parallelism**, and **resource allocation**
  across CPU/GPU nodes?
- How does this improve over ad-hoc scripts in terms of maintainability, performance, and
  correctness?

**SAGE components to mention**

- High-level APIs and examples under `examples/apps` 和 `examples/tutorials` that construct
  dataflows.
- Kernel/platform interaction for executing these dataflows, including job scheduling and node
  selection.
- Role of `sage-middleware` operators when a dataflow step is performance-critical.

**Suggested figures**

- **Figure 3: Declarative Dataflow Example.** A diagram of a concrete pipeline (data ingestion →
  embedding → retrieval → LLM generation → post-processing), annotated with which layers are
  involved at each step.
- **Figure 4: Execution Model.** A schematic showing how a declarative graph is compiled into tasks
  over nodes, with batching and scheduling hooks.

______________________________________________________________________

## 5. Section – LLM & Embedding Control Plane (sageLLM)

**Questions to answer**

- What are the **goals** of the control plane? (e.g., share resources across LLM and embedding
  workloads, improve throughput and tail latency, respect SLOs.)
- How are requests classified and routed? What are the main scheduling/batching policies?
- How does the control plane interact with the gateway and backends?
- How does it differ from a single vLLM instance or simple load balancer?
- How does it fit into the broader SAGE system (dataflow, benchmarks, deployment tools)?

**Mapping to SAGE components**

- `sage.common.components.sage_llm.UnifiedInferenceClient` (with unified `create()` entry point) and
  related control-plane modules under `sageLLM/control_plane/` including `ControlPlaneManager`,
  `RequestClassifier`, `HybridSchedulingPolicy`, and `EmbeddingExecutor`.
- `sage-gateway` FastAPI app and routes for LLM and embedding.
- `SagePorts` (`GATEWAY_DEFAULT`, `LLM_DEFAULT`, `EMBEDDING_DEFAULT`, etc.) and WSL2-aware port
  selection.

**Suggested figures**

- **Figure 5: Control Plane Architecture.** Components: request classifier, scheduling policy
  (HybridSchedulingPolicy), execution coordinators for LLM and embeddings, backend engine pool.
- **Figure 6: Request Timeline under Mixed Workloads.** Show how chat and embedding requests are
  batched and routed over time, contrasted with a naive baseline.

______________________________________________________________________

## 6. Section – Implementation Details and Deployment

**Questions to answer**

- What are the key implementation choices that matter for systems reviewers? (language choices, C++
  integration, build system, packaging.)
- How does SAGE support **CPU-only** as well as GPU deployments in practice?
- How do quickstart scripts and `sage-dev` tooling enable **reproducible experiments** and CI?
- What operational practices (logging, configuration, user paths) are built in to support real
  users?

**SAGE components to mention**

- C++ middleware build (`packages/sage-middleware/src/...`, CMake, `.sage/build/`).
- Installation scripts: `quickstart.sh`, `manage.sh`, CI install wrappers.
- `sage-dev` commands for test, quality, and examples; pytest configuration under
  `tools/pytest.ini`.
- XDG-based user paths and directories for logs, models, and cache.

**Suggested figures / tables**

- **Table 1: Implementation Summary.** Columns: language/components, lines of code (approx.), main
  dependencies, build artifacts.
- **Figure 7: Deployment and Tooling Workflow.** From cloning the repo to running `quickstart.sh`,
  starting `sage gateway` and `sage llm`, and launching experiments.

______________________________________________________________________

## 7. How to Use This Outline

- 在写 System 章节时，可以把本文件作为“答案模板”，再配合 `04_system_and_method.md` 中的提示词：
  - 把这里的每个小节要点粘到提示词中的 `[PASTE THE BULLET-POINT OUTLINE HERE]` 位置；
  - 让模型基于这些要点生成英文小节；
  - 你再根据实际实现细节和实验配置进行微调。
- 如果篇幅吃紧，可以：
  - 把 System Overview + Layered Architecture 合并；
  - 把 Declarative Dataflow + Control Plane 合并；
  - 将部分 Implementation 细节移到附录，仅在正文保留最系统相关的要点。
