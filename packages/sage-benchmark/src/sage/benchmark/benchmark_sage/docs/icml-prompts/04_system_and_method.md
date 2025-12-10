# ICML System Track - System / Method Prompts# ICML System Track – System / Method Prompts

本文件面向系统论文的"Method / System Design"部分，帮助你把 SAGE 的系统设计讲清楚，突出实现与可扩展性。本文件面向系统论文的“Method / System
Design”部分，帮助你把 SAGE 的系统设计讲清楚，突出实现与可扩展性。

______________________________________________________________________

## 4.1 设计 System 章节结构## 4.1 设计 System 章节结构

\*\*提示词（可直接复制）\*\***提示词（可直接复制）**

You are an ICML systems-track co-author responsible for the **System Design / Method** section of a
paper about **SAGE**.You are an ICML systems-track co-author responsible for the **System Design /
Method** section of a paper about **SAGE**.

--- System context ------ System context ---

SAGE is a Python 3.10+ framework for building LLM/AI data processing pipelines. It targets
**system-level issues** such as scalability, heterogeneous hardware, and unified management of LLM
and embedding workloads.SAGE is a Python 3.10+ framework for building LLM/AI data processing
pipelines. It targets **system-level issues** such as scalability, heterogeneous hardware, and
unified management of LLM and embedding workloads.

Key design aspects to consider:Key design aspects to consider:

- **Layered architecture (L1-L6)** with **no upward dependencies**:- **Layered architecture
  (L1–L6)** with **no upward dependencies**:

  - L1: `sage-common` - foundational utilities, configuration, user paths, port management
    (`SagePorts`), **Control Plane core** (`sageLLM/control_plane/`). - L1: `sage-common` –
    foundational utilities, configuration, user paths, port management (`SagePorts`).

  - L2: `sage-platform` - platform services for storage, queuing, and service management. - L2:
    `sage-platform` – platform services, job management, node selection, CPU/GPU node support.

  - L3: `sage-kernel`, `sage-libs` - core execution engine, **job management**
    (`runtime/job_manager`), **node selection** (`scheduler/node_selector`), algorithms, scheduling
    logic. - L3: `sage-kernel`, `sage-libs` – core execution engine, algorithms, scheduling logic.

  - L4: `sage-middleware` - C++ operators and performance-critical components, built via CMake. -
    L4: `sage-middleware` – C++ operators and performance-critical components, built via CMake.

  - L5: `sage-apps`, `sage-benchmark` - applications and benchmark suites. - L5: `sage-apps`,
    `sage-benchmark` – applications and benchmark suites.

  - L6: `sage-cli`, `sage-studio`, `sage-tools`, `sage-gateway` - user-facing interfaces and
    gateway. - L6: `sage-cli`, `sage-studio`, `sage-tools`, `sage-gateway` – user-facing interfaces
    and gateway.

- **Declarative dataflow** abstraction for specifying pipelines.- **Declarative dataflow**
  abstraction for specifying pipelines.

- **Unified LLM & embedding control plane**:- **Unified LLM & embedding control plane**:

  - `UnifiedInferenceClient.create()` as single entry point, `ControlPlaneManager`,
    `HybridSchedulingPolicy`; - `UnifiedInferenceClient`, ControlPlaneManager,
    HybridSchedulingPolicy;

  - LLM and embedding backends (vLLM instances, embedding services) as a shared resource pool; - LLM
    and embedding backends (vLLM instances, embedding services) as a shared resource pool;

  - OpenAI-compatible API via `sage-gateway` on well-defined ports (e.g., 8888 for gateway,
    8001/8901 for LLM, 8090 for embeddings, via `SagePorts`). - OpenAI-compatible API via
    `sage-gateway` on well-defined ports (e.g., 8888 for gateway, 8001/8901 for LLM, 8090 for
    embeddings, via `SagePorts`).

- **User paths and configuration** following XDG base directory spec; project-level `.sage/`
  directory for build artifacts.- **User paths and configuration** following XDG base directory
  spec; project-level `.sage/` directory for build artifacts.

- **Deployment and CI** patterns (quickstart scripts, `sage-dev` tooling) as supporting
  implementation details.- **Deployment and CI** patterns (quickstart scripts, `sage-dev` tooling)
  as supporting implementation details.

--- Task ------ Task ---

Design a **System / Method section outline** tailored for an ICML systems paper. The section should
likely include 3-5 main subsections, for example:Design a **System / Method section outline**
tailored for an ICML systems paper. The section should likely include 3–5 main subsections, for
example:

- System Overview / Goals;- System Overview / Goals;

- Layered Architecture;- Layered Architecture;

- Declarative Dataflow and Execution Model;- Declarative Dataflow and Execution Model;

- Control Plane for LLM and Embeddings;- Control Plane for LLM and Embeddings;

- Implementation Details and Deployment.- Implementation Details and Deployment.

For each proposed subsection:For each proposed subsection:

1. Provide a bullet list of **key questions** it should answer from a systems-reviewer perspective
   (e.g., how the system scales, how it abstracts hardware differences, how it improves
   programmability without sacrificing performance).1. Provide a bullet list of **key questions** it
   should answer from a systems-reviewer perspective (e.g., how the system scales, how it abstracts
   hardware differences, how it improves programmability without sacrificing performance).

1. Map these questions to **specific SAGE components** or modules (e.g., `sage-kernel` for job
   management and node selection, `sage.common.components.sage_llm` for control plane,
   `sage-middleware` for C++ operators).2. Map these questions to **specific SAGE components** or
   modules (e.g., `sage-platform` for node selection, `sage.common.components.sage_llm` for control
   plane, `sage-middleware` for C++ operators).

1. Suggest **figures or diagrams** that should accompany this subsection (e.g., architecture
   diagram, dataflow diagram, control-plane timeline), with 1-2 sentences per figure describing what
   it should convey.3. Suggest **figures or diagrams** that should accompany this subsection (e.g.,
   architecture diagram, dataflow diagram, control-plane timeline), with 1–2 sentences per figure
   describing what it should convey.

--- Output ------ Output ---

- A structured outline with subsections and bullet points answering the above.- A structured outline
  with subsections and bullet points answering the above.

- No full prose yet.- No full prose yet.

______________________________________________________________________

## 4.2 逐小节撰写 System 文本## 4.2 逐小节撰写 System 文本

有了 4.1 的大纲后，你可以对每个小节单独调用下面的提示词写正文。有了 4.1 的大纲后，你可以对每个小节单独调用下面的提示词写正文。

\*\*提示词（可直接复制，每个小节复用）\*\***提示词（可直接复制，每个小节复用）**

We have designed an outline for the System / Method section of our ICML systems paper on **SAGE**.
Now we will write the subsection:We have designed an outline for the System / Method section of our
ICML systems paper on **SAGE**. Now we will write the subsection:

> [INSERT SUBSECTION TITLE HERE, e.g., "Layered Architecture"]> \[INSERT SUBSECTION TITLE HERE,
> e.g., "Layered Architecture"\]

Here is the bullet-point outline for this subsection (from the previous step):Here is the
bullet-point outline for this subsection (from the previous step):

[PASTE THE BULLET-POINT OUTLINE HERE][PASTE THE BULLET-POINT OUTLINE HERE]

--- System reminders ------ System reminders ---

- SAGE uses a **6-layer architecture (L1-L6)** with no upward dependencies.- SAGE uses a **6-layer
  architecture (L1–L6)** with no upward dependencies.

- It exposes **declarative dataflow** to users, while deeper layers handle scheduling, optimization,
  and execution.- It exposes **declarative dataflow** to users, while deeper layers handle
  scheduling, optimization, and execution.

- It includes a **unified control plane** for LLM and embedding services, fronted by an
  OpenAI-compatible gateway.- It includes a **unified control plane** for LLM and embedding
  services, fronted by an OpenAI-compatible gateway.

- It targets **scalability, heterogeneity (CPU/GPU), and reproducibility**.- It targets
  **scalability, heterogeneity (CPU/GPU), and reproducibility**.

--- Task ------ Task ---

Please write a detailed English subsection for an ICML systems paper that:Please write a detailed
English subsection for an ICML systems paper that:

1. Answers the bullet-point questions with **systems-level explanations** rather than just listing
   APIs.1. Answers the bullet-point questions with **systems-level explanations** rather than just
   listing APIs.

1. Emphasizes how SAGE's design choices (e.g., layering, declarative dataflow, control plane)
   address concrete systems challenges (e.g., resource utilization, latency, cluster heterogeneity,
   ease of evolution).2. Emphasizes how SAGE’s design choices (e.g., layering, declarative dataflow,
   control plane) address concrete systems challenges (e.g., resource utilization, latency, cluster
   heterogeneity, ease of evolution).

1. Includes **references to SAGE components** (module or package names) only when they help clarify
   the design (e.g., mentioning `sage-kernel` when talking about job management and node
   selection).3. Includes **references to SAGE components** (module or package names) only when they
   help clarify the design (e.g., mentioning `sage-platform` when talking about node selection).

1. Suggests where to place figures or tables, and provides a short candidate **figure caption** if
   appropriate.4. Suggests where to place figures or tables, and provides a short candidate **figure
   caption** if appropriate.

--- Output ------ Output ---

1. The full text of the subsection in English (approx. 1-2 single-column pages, depending on
   importance).1. The full text of the subsection in English (approx. 1–2 single-column pages,
   depending on importance).

1. A short list of **potential figure captions** and where they should appear.2. A short list of
   **potential figure captions** and where they should appear.

1. Optional notes on which parts could be shortened if page limits are tight.3. Optional notes on
   which parts could be shortened if page limits are tight.

______________________________________________________________________

## 4.3 控制平面技术细节（CRITICAL - 必须包含）## 4.3 控制平面细化（可选强化）

这是系统论文的核心技术贡献，必须详细解释调度算法。如果你希望专门强化控制平面（sageLLM）的系统贡献，可以单独用下面的提示词：

\*\*提示词（可直接复制）\*\***提示词（可直接复制）**

We want to dedicate a focused subsection to the **LLM & embedding control plane** in SAGE
("sageLLM"). This subsection should be particularly convincing for ICML systems reviewers who care
about **resource management, scheduling, and scalability**.We want to dedicate a focused subsection
to the **LLM & embedding control plane** in SAGE ("sageLLM"). This subsection should be particularly
convincing for ICML systems reviewers who care about **resource management, scheduling, and
scalability**.

--- Control Plane Architecture (from actual implementation) ---Context:

- The control plane classifies requests into chat/generation vs. embedding.

\`\`\`- It uses policies such as `HybridSchedulingPolicy` to batch and route requests across a pool
of vLLM and embedding engines.

┌─────────────────────────────────────────────────────────────────────────┐- It aims to improve
**throughput, tail latency, and SLO compliance** while sharing resources across heterogeneous LLM
and embedding workloads.

│ UnifiedInferenceClient │- It is integrated with `sage-gateway`, which exposes an OpenAI-compatible
API on well-defined ports from `SagePorts`.

│ chat() | generate() | embed() │

│ ↓ (single entry: create()) │Task:

├─────────────────────────────────────────────────────────────────────────┤- Please draft a detailed
English subsection (around 1 single-column page) that:

│ sage-gateway (Port 8888) │ 1. Explains the **design goals** of the control plane;

│ (OpenAI-Compatible REST API + Control Plane) │ 2. Describes the **architecture** (key components
and how they interact);

│ /v1/chat/completions | /v1/embeddings | /v1/management/\* │ 3. Highlights the **scheduling and
batching strategies** and why they matter for LLM/embedding workloads;

├─────────────────────────────────────────────────────────────────────────┤ 4. Prepares the ground
for an experiments section that will compare different policies and baselines.

│ sageLLM Control Plane (Core) │- Explicitly mention **metrics** (throughput, mean/tail latency, SLO
hit rate) and **workload types** that are suitable for evaluation, even if we provide numbers later.

│ ┌─────────────────────────────────────────────────────────────────┐ │

│ │ RequestClassifier (LLM_CHAT / LLM_GENERATE / EMBEDDING) │ │Please also suggest 1–2 **figures**
that would best illustrate the control plane operation (e.g., a timeline, a request classification +
routing diagram), with tentative captions.

│ │ HybridSchedulingPolicy (request grouping, priority, batching) │ │ │ │ ExecutionCoordinator (LLM)
| EmbeddingExecutor (Embedding) │ │ │
└─────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤ │ Backend Engine Pool │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │ │ │ vLLM Instance │ │ vLLM Instance
│ │ Embedding Srv │ │ │ │ (LLM Only) │ │ (LLM+Embed) │ │ (Embed Only) │ │ │ └─────────────────┘
└─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

```

--- Key Components (actual module paths) ---
- `ControlPlaneManager`: `sageLLM/control_plane/manager.py` - Core orchestrator
- `RequestClassifier`: `sageLLM/control_plane/request_classifier.py` - Request type detection
- `HybridSchedulingPolicy`: `sageLLM/control_plane/strategies/hybrid_policy.py` - Scheduling decisions
- `EmbeddingExecutor`: `sageLLM/control_plane/executors/embedding_executor.py` - Batched embedding execution

--- Scheduling Algorithm Details (MUST explain) ---

The prompt should guide the model to explain:

1. **Request Classification**
   - How does `RequestClassifier` distinguish chat vs. generation vs. embedding?
   - What features are used (endpoint path, model name, request structure)?
   - What is the latency overhead of classification?

2. **Scheduling Policy Options**
   - `fifo`: Simple first-in-first-out for baseline comparison
   - `priority`: Interactive (chat) requests get higher priority than batch (generation)
   - `slo_aware`: Requests with tighter latency SLOs are prioritized
   - `hybrid`: Combines priority + SLO awareness + workload-specific batching

3. **Batching Strategy**
   - For LLM: How does it interact with vLLM's continuous batching?
   - For Embedding: How does `EmbeddingExecutor` aggregate requests across time windows?
   - What is the trade-off between batching efficiency and latency?

4. **Load Balancing**
   - How are requests distributed across multiple backend engines?
   - What metrics are used (queue depth, GPU utilization, response time)?
   - How does it handle engine failures or slow backends?

5. **Interaction with vLLM**
   - SAGE does NOT replace vLLM's internal scheduler
   - SAGE provides **cross-engine** scheduling and **embedding co-scheduling**
   - What API does SAGE use to communicate with vLLM (OpenAI-compatible)?

--- Task ---
Please draft a detailed English subsection (around 1.5 single-column pages) that:
1. Explains the **design goals** of the control plane (unified scheduling, resource sharing, SLO compliance);
2. Describes the **architecture** with the component diagram above;
3. Details the **scheduling algorithm** with pseudocode or algorithmic description for HybridSchedulingPolicy;
4. Explains how **batching** works differently for LLM vs. Embedding workloads;
5. Clarifies the **relationship with vLLM** (complementary, not replacement);
6. Prepares the ground for experiments comparing different policies.

--- Output ---
1. Full subsection text with technical depth
2. Pseudocode for scheduling algorithm (if appropriate)
3. Suggested figures:
   - Figure X: Control Plane Architecture (component diagram)
   - Figure Y: Request Timeline showing classification, queuing, batching, execution

---

## 4.4 与 vLLM 关系的澄清（重要补充）

审稿人可能会质疑 SAGE 与 vLLM 的关系。这里提供专门的澄清引导。

**提示词（可直接复制）**

A reviewer might ask: "How does SAGE relate to vLLM? Isn't vLLM already a highly optimized LLM serving system?"

Please draft a **clarification paragraph** (3-5 sentences) that explains:

1. **Complementarity, not competition**: SAGE uses vLLM (or other engines) as backend serving components. vLLM handles single-model inference optimization (PagedAttention, continuous batching). SAGE handles cross-model orchestration and embedding co-scheduling.

2. **Abstraction level difference**:
   - vLLM = single-model inference engine (optimizes GPU memory, batch processing for one model)
   - SAGE = pipeline-level control plane (orchestrates multiple models, handles embedding services, provides unified API)

3. **What SAGE adds**:
   - Multi-engine load balancing
   - LLM + Embedding unified scheduling
   - Request classification and SLO-aware routing
   - Declarative pipeline composition

4. **Concrete example**: A RAG pipeline needs: embedding service (for retrieval) + LLM service (for generation). Without SAGE, operators must manually manage two services and balance load. With SAGE, they declare the pipeline and the control plane handles resource allocation.

This paragraph should be inserted in the System section after describing the control plane architecture.
```
