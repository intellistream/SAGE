# SAGE Systems Paper – Combined Writing Prompts

> This file aggregates the per-section prompts under `docs/01_*.md`–`08_*.md` in
> `benchmark_sage/docs/` so you can browse and search all SAGE paper prompts in one place.
>
> Each section below inlines the original Markdown file verbatim.

______________________________________________________________________

## 01_abstract.md

````markdown
# Abstract Prompt – SAGE Systems Paper

下面是为 SAGE 撰写 **系统论文摘要（Abstract）** 的提示词模版，你可以直接复制到对话中，并在标注位置补充信息。
默认面向顶级机器学习系统会议的系统 track（例如 ICML Machine Learning Systems track），但提示词本身不依赖具体会议名称。

______________________________________________________________________

## 提示词（可直接复制给大模型）

You are an experienced systems-track author. You help me write a **concise but technically rich abstract** for a paper about **SAGE**, a machine learning systems framework.

--- Context about the paper and the system ---

- Target venue: a **top-tier Machine Learning Systems track** (focus on implementation, scalability, hardware, libraries, distributed methods, etc.).
- System: **SAGE**, a Python 3.10+ framework for building **LLM/AI data processing pipelines** with **declarative dataflow**.
- Goal of the paper: present SAGE as a **full-stack dataflow-based ML system**, not just an LLM control plane.

Key architectural points (you should weave them naturally into the abstract, not list them mechanically):

- A strict **6-layer architecture (L1–L6)**: `sage-common`, `sage-platform`, `sage-kernel` / `sage-libs`, `sage-middleware`, `sage-apps` / `sage-benchmark`, `sage-cli` / `sage-studio` / `sage-tools` / `sage-gateway`, with **no upward dependencies** (each layer only depends on lower layers).
- **Declarative dataflow** for constructing LLM/AI pipelines: users declare high-level pipelines, while platform, kernel, and middleware layers compile them into an efficient execution plan across heterogeneous resources.
- A unified **LLM & embedding control plane** ("sageLLM"), exposed via an **OpenAI-compatible gateway** (`sage-gateway`), providing request classification, hybrid scheduling, batching, and resource sharing across multiple vLLM / embedding instances.
- **CPU-only and GPU node support**, with job management and node selection in `sage-kernel` (runtime, scheduler) and cluster configuration / services in `sage-platform`.
- A **comprehensive benchmark suite** (`sage-benchmark`) that evaluates both **agent capabilities** (tool selection, task planning, timing decisions) and **system-level behavior** (throughput, latency distribution, SLO compliance, interference) for different SAGE subsystems.
- Implementation characteristics that highlight systems engineering effort: C++ middleware operators (`sage-middleware`) with CMake-based build; unified CI and quality tools (Ruff, Mypy); reproducible quickstart scripts; XDG-based user paths and configuration.

--- Quantitative claims template (to be filled after experiments) ---

The abstract MUST include at least **one concrete quantitative claim**. You can use placeholders now and replace them with actual numbers later. Typical patterns include:

- **Performance / latency**:
  - "reduces p99 latency by [X]% compared to [baseline] under mixed LLM+embedding workloads".
  - "improves throughput by [Y]× over [baseline] while maintaining p95 latency below [Z] ms".
- **SLO and robustness**:
  - "achieves [A]% SLO satisfaction vs. [B]% for [baseline] under [workload] traffic patterns".
- **Resource efficiency / heterogeneity**:
  - "reduces resource utilization variance by [C]% across heterogeneous CPU/GPU nodes".
- **Agent / pipeline quality (if applicable)**:
  - "improves tool selection accuracy by [D]% on [benchmark]".
  - "reduces planning latency by [E]% while maintaining [F]% task success rate".
- **Scale**:
  - "evaluated on clusters with up to [G] GPU nodes and [H] concurrent clients".
  - "supports [I] requests per second with [J] backend engines".

After you draft the text, I will plug in actual experiment results to replace these placeholders.

--- Writing goals ---

Please draft a **150–200 word** English abstract that:

1. Starts with 2–3 sentences of **problem context**: complexity of modern LLM/AI pipelines, challenges in managing dataflow, heterogeneous resources, and multiple LLM / embedding services.
2. Gives a **high-level description of SAGE** as a systems contribution, emphasizing:
   - its **layered architecture** and separation of concerns;
   - the **declarative dataflow** interface and execution model;
   - the **unified control plane** and gateway for LLM / embedding workloads;
   - its role as a **general platform** for LLM-centric pipelines, not only a control-plane module.
3. Clearly states **2–4 concrete contributions** that a systems reviewer can check, such as:
   - a layered architecture that enables modular, scalable LLM/AI pipelines;
   - a control-plane design that improves utilization / latency across LLM and embedding services;
   - heterogeneous CPU/GPU support and reproducible tooling that simplify deployment;
   - a benchmark suite that probes both agent capabilities and system-level performance.
4. Ends with **quantitative experimental claims** using the placeholder format above (no vague "improves performance" statements).

--- Style constraints ---

- Use **academic, precise, neutral English** typical of top-tier systems papers.
- Avoid buzzwords and marketing language; focus on **what the system does**, **why it is needed**, and **how well it performs**.
- Clearly mark all quantitative placeholders as `[X]`, `[Y]`, etc., so we can later map them to specific experiments.
- If needed, you may slightly exceed 200 words in the first draft and then suggest where to cut.

--- Output format ---

1. Provide **one candidate abstract** with quantitative placeholders clearly marked.
2. List the **specific experiments needed** to fill each placeholder (e.g., mixed workload latency benchmark, scalability study, agent benchmark).
3. Provide **3–5 bullet-point suggestions** on how we might refine the abstract once we have concrete experimental numbers and finalized baselines.

---

## Example abstract structure（仅供参考）

```text
[Problem context – 2–3 sentences]
Modern LLM applications require complex pipelines that combine retrieval, tools, and multiple models across heterogeneous CPU/GPU clusters. Existing serving and MLOps systems either focus on single-model inference or generic workflows, and do not provide unified control or dataflow support for mixed LLM + embedding workloads.

[System description – 2–3 sentences]
We present SAGE, a framework that organizes LLM/AI pipelines into a layered architecture with declarative dataflow and a unified control plane for LLM and embedding services. SAGE integrates platform, kernel, middleware, and gateway components to execute pipelines efficiently across heterogeneous resources.

[Key contributions – 2–3 sentences]
Our main contributions are: (1) a six-layer architecture and declarative dataflow model for LLM-centric pipelines; (2) a unified LLM + embedding control plane that shares resources and improves tail latency; (3) systems support for heterogeneous CPU/GPU deployments and reproducible tooling; and (4) a benchmark suite that evaluates both agent behavior and system-level scheduling.

[Quantitative results – 1–2 sentences]
Experiments show that SAGE reduces p99 latency by [X]% and improves throughput by [Y]× compared to [baseline] on [workload], while achieving [Z]% SLO satisfaction and maintaining [A]% task success rate in representative agent pipelines.
```

````

______________________________________________________________________

## 02_introduction.md

```markdown
# Introduction Prompts – SAGE Systems Paper

本文件提供多轮使用的引言（Introduction）写作提示词模版，面向顶级机器学习系统会议的系统 track（例如 ICML Machine Learning Systems track）。
整体目标是：以 **完整的 SAGE 系统** 为主角，而不是只讲某个子模块（例如 control plane）。

______________________________________________________________________

## 2.1 生成引言整体结构

**提示词（可直接复制）**

You are a systems-track co-author. Help me design the **structure** of the Introduction for a paper about **SAGE**, a machine learning systems framework.

--- System context ---

- Target venue: a **top-tier Machine Learning Systems track**.
- System: **SAGE**, a Python 3.10+ framework for **LLM/AI data processing pipelines** with **declarative dataflow**.
- SAGE should be presented as a **full-stack system**, covering:
  - a strict **6-layer architecture (L1–L6)** with no upward dependencies, from `sage-common` and `sage-platform` up to `sage-cli`, `sage-studio`, `sage-tools`, and `sage-gateway`;
  - **declarative dataflow** for composing LLM/AI pipelines (e.g., retrieval, tools, LLM calls, post-processing);
  - a **unified LLM & embedding control plane** (sageLLM) exposed via `sage-gateway`;
  - **CPU-only and GPU deployments**, job management and node selection in `sage-kernel`, platform services in `sage-platform`;
  - **benchmark suites** in `sage-benchmark` for agents, scheduling policies, RAG, DB/time-series components, etc.

--- Positioning against existing systems (CRITICAL for novelty) ---

When structuring the Introduction, explicitly address how SAGE differs from **all** of the following (not only control-plane-level systems):

- **LLM serving engines** such as vLLM, TensorRT-LLM, SGLang: they optimize single-model inference; SAGE operates at a **higher abstraction level**, orchestrating multiple engines, embedding services, and full pipelines under a unified dataflow and control plane.
- **ML serving frameworks** such as Ray Serve, KServe, Triton Inference Server: they are generic serving or deployment platforms; SAGE provides **LLM-aware scheduling**, declarative pipelines, and end-to-end evaluation for LLM-centric workloads.
- **LLM application frameworks** such as LangChain, LlamaIndex, DSPy: they focus on application-level orchestration; SAGE is a **systems-level infrastructure** providing resource management, scheduling, and execution primitives that such frameworks could build upon.
- **ML workflow / MLOps platforms** such as MLflow, Kubeflow, Airflow: they emphasize training and generic workflows; SAGE focuses on **inference pipelines** with real-time scheduling, heterogeneous hardware, and LLM-specific concerns.
- **LLM benchmarks** such as AgentBench, ToolBench, HELM, single-engine vLLM benchmarks: they focus on task accuracy or single-engine metrics; SAGE adds **system-level benchmarks** that stress control-plane, dataflow, and heterogeneous deployments.

The key novelty claim should be: SAGE is a **full ML system** that combines a layered architecture, declarative dataflow, a unified LLM + embedding control plane, heterogeneous deployment support, and comprehensive benchmarks, filling the gap between low-level serving engines and high-level application frameworks.

--- Task ---

Design a **4–6 paragraph outline** (not full prose yet) for the Introduction that suits a top-tier systems paper on SAGE. For each paragraph:

1. State the **goal** of the paragraph (e.g., establish broader context of LLM/AI systems, articulate challenges in managing complex LLM pipelines, highlight gaps in existing systems, introduce SAGE, summarize contributions, preview experiments).
2. Provide a **bullet list of key points** that should appear in that paragraph, focusing on:
   - systems challenges (scalability, hardware heterogeneity, multiple LLM/embedding services, observability, configuration complexity, reproducibility);
   - why existing frameworks (generic MLOps, standalone LLM serving, ad-hoc scripts, application-level orchestrators) do not fully address these for **LLM-centric pipelines**;
   - how SAGE’s architecture, dataflow model, control plane, and benchmarks are designed around these challenges.
3. Mark where we should **present the main contributions** as a numbered list (usually at the end of the last or second-to-last paragraph).
4. Explicitly note any parts where you need more concrete details from me (e.g., workloads, cluster scale, baselines, key SAGE subsystems highlighted in experiments).

--- Output ---

- A paragraph-level outline (4–6 paragraphs), each with:
  - a short description of the paragraph goal;
  - bullet points of content to cover.
- Do **not** yet write the full paragraphs.

______________________________________________________________________

## 2.2 逐段写引言

在拿到 2.1 中的段落大纲后，你可以按段落逐个生成英文正文。

**提示词（可直接复制，每段都可以复用）**

We previously designed a paragraph-level outline for the Introduction of our systems paper on **SAGE**. Now we will write **paragraph X**.

Here is the outline for this paragraph (copied from the previous step):

[PASTE THE BULLET-POINT OUTLINE FOR PARAGRAPH X HERE]

--- System context reminders ---

- SAGE targets **LLM/AI pipelines**, not generic ML training.
- It offers **declarative dataflow** and a **multi-layer architecture** with no upward dependencies.
- It includes a **unified control plane** for LLM and embedding services, exposed via an OpenAI-compatible gateway.
- It provides **benchmarking** tools for agent capabilities, scheduling policies, and other subsystems (RAG, DB, TSDB, etc.).
- The paper is about the **whole SAGE system** (architecture + dataflow + control plane + benchmarks), not only a single module.

--- Task ---

Using only the above outline and the system context, write a full **English paragraph** (8–12 sentences) suitable for a top-tier systems-track Introduction.

Writing requirements:

1. Focus on **systems challenges and insights**, not just listing features.
2. Use **neutral, technical language**; avoid buzzwords or marketing tone.
3. Make the paragraph **self-contained**, but naturally connectible to the previous and next paragraphs.
4. It is acceptable for the first draft to be slightly longer; at the end, suggest 1–2 sentences that could be dropped if space is tight.

--- Output ---

1. The full paragraph in English.
2. A short bullet list of **possible trimming points** (sentences that could be removed if we need to shorten the Introduction).

你不需要在每一段里重复完整的系统描述，只要引用必要的关键信息即可，使整篇引言连贯、系统、而且覆盖整个 SAGE。

```

______________________________________________________________________

## 03_related_work.md

```markdown
# Related Work Prompts – SAGE Systems Paper

本文件提供撰写 Related Work（相关工作）部分的提示词，重点从 **系统视角** 对 SAGE 进行分类与定位，覆盖整个系统（分层架构、数据流、控制平面、benchmark），而不是只讨论某一个子模块。

______________________________________________________________________

## 3.1 相关工作分类与定位

**提示词（可直接复制）**

You are a systems-track author responsible for the **Related Work** section of a paper about **SAGE**, a framework for LLM/AI pipelines.

--- System context (for positioning) ---

SAGE focuses on **system-level support for LLM/AI dataflow pipelines**, rather than general ML training. Key system contributions include:

- A **6-layer architecture** with strict no-upward-dependency design, from `sage-common` and `sage-platform` to `sage-kernel` / `sage-libs`, `sage-middleware`, `sage-apps` / `sage-benchmark`, and user-facing tools (`sage-cli`, `sage-studio`, `sage-tools`, `sage-gateway`).
- **Declarative dataflow** for LLM/AI pipelines, mapping user-level pipeline descriptions to efficient execution on heterogeneous CPU/GPU clusters.
- A unified **LLM & embedding control plane** with hybrid scheduling and batching, exposed via an OpenAI-compatible gateway (`sage-gateway`).
- Systems support for **CPU-only and GPU nodes**, job management and node selection in `sage-kernel`, platform services in `sage-platform`.
- A **benchmark suite** (`sage-benchmark`) focusing on **agent capabilities** (tool selection, planning, timing) and **system-level scheduling** (throughput, latency distribution, SLO compliance, interference).

--- Task ---

1. Propose a **taxonomy of related work** into 4–5 categories suitable for a top-tier systems paper. A reasonable starting point is:
   - Category 1: LLM Serving Engines (e.g., vLLM, TensorRT-LLM, SGLang, Orca)
   - Category 2: ML Serving Frameworks and Workflow Platforms (e.g., Ray Serve, KServe, Triton, MLflow, Kubeflow, Airflow)
   - Category 3: LLM Application Frameworks and Agents (e.g., LangChain, LlamaIndex, DSPy, various agent tool-use frameworks)
   - Category 4: LLM Benchmarks and Evaluation Frameworks (e.g., AgentBench, ToolBench, HELM, vLLM benchmark)
   - (Optional) Category 5: Data & Storage Systems for AI Pipelines (e.g., vector DBs, TSDBs, dataflow systems that overlap with `sage.db`, `sage.tsdb`, `sage.flow`)

2. For each category:
   - Give 2–3 sentences summarizing **what this category of work tries to achieve**, in terms of systems properties (e.g., throughput, flexibility, observability, portability, fairness).
   - Provide 3–5 sentences on **how SAGE differs** from typical works in this category, explicitly referencing:
     - multi-layer architecture vs. monolithic designs;
     - **unified** LLM + embedding control plane vs. LLM-only serving;
     - declarative dataflow vs. imperative orchestration or ad-hoc scripts;
     - system-level benchmarks vs. task-only or single-engine benchmarks.
   - Mark where we should later insert **specific citation examples** (use placeholders like `[REF: VLLM]`, `[REF: RAY_SERVE]`, `[REF: LANGCHAIN]`).

3. Explicitly state the **gap that SAGE fills**: a unified, layered system for LLM+embedding dataflow pipelines with control-plane scheduling and comprehensive benchmarks, sitting between low-level serving engines and high-level application frameworks.

--- Output ---

- A structured outline listing:
  - The proposed categories;
  - For each category, a short paragraph summarizing it and briefly contrasting SAGE.
- The outline should be detailed enough that we could almost lift it directly into the paper, then refine names and add citations.

______________________________________________________________________

## 3.2 完整 Related Work 草稿

在 3.1 确定 taxonomy 和要点之后，你可以生成一版接近成品的 Related Work 文本。

**提示词（可直接复制）**

Now, using the taxonomy and short summaries we just designed for Related Work, please draft a **full Related Work section** for our systems paper on **SAGE**.

Constraints and goals:

1. Organize the text into **subsections or logical paragraphs**, one per category from the taxonomy.
2. For each category:
   - Start with 2–3 sentences summarizing the category and its main systems concerns.
   - Name **specific representative systems** (e.g., vLLM, TensorRT-LLM, SGLang, Ray Serve, KServe, Triton, MLflow, Kubeflow, LangChain, LlamaIndex, DSPy, AgentBench, ToolBench, HELM) and briefly describe what they do.
   - Then write 3–5 sentences positioning **SAGE** relative to this category, focusing on:
     - multi-layer architecture vs. monolithic or flat designs;
     - unified LLM+embedding control plane vs. single-workload focus;
     - declarative dataflow vs. imperative orchestration;
     - system-level benchmark and experimental testbed vs. task-only evaluation.
   - Include explicit phrases that emphasize **complementarity or orthogonality** (e.g., "SAGE can use vLLM as a backend engine"), not just replacement.
3. Throughout the text, clearly emphasize that **SAGE is a systems contribution**: improved implementation and scalability, support for heterogeneous hardware, unified resource management for LLM+embedding workloads, and comprehensive evaluation infrastructure.
4. Include a **summary paragraph** at the end that synthesizes the positioning: SAGE fills the gap between low-level serving engines, generic serving / workflow systems, and high-level LLM application frameworks by providing a unified dataflow-based platform and control plane with benchmarks.

--- Output ---

- A 1.5–2 page (single-column equivalent) English draft of the Related Work section, following the above structure.
- Use actual system names for well-known systems; use `[REF: ...]` placeholders where you need citations.
- At the end, list all `[REF: ...]` slots used, grouped by category, so we can map them to actual papers later.

```

______________________________________________________________________

## 04_system_and_method.md

```markdown
# System / Method Prompts – SAGE Systems Paper

本文件面向系统论文的 "System / Method" 章节，帮助你把 **整个 SAGE 系统** 的设计讲清楚，突出实现与可扩展性，而不是只强调 control plane。

______________________________________________________________________

## 4.1 设计 System 章节结构

**提示词（可直接复制）**

You are a systems-track co-author responsible for the **System Design / Method** section of a paper about **SAGE**.

--- System context ---

SAGE is a Python 3.10+ framework for building LLM/AI data processing pipelines. It targets **system-level issues** such as scalability, heterogeneous hardware, unified management of LLM and embedding workloads, and reproducible experimentation.

Key design aspects to consider:

- **Layered architecture (L1–L6)** with **no upward dependencies**:
  - L1: `sage-common` – foundational utilities, configuration, user paths (XDG), port management (`SagePorts`), shared components (e.g., `UnifiedInferenceClient`, control-plane core modules under `sageLLM/control_plane/`).
  - L2: `sage-platform` – platform services (storage, queuing, service management), cluster configuration via `config/cluster.yaml`.
  - L3: `sage-kernel`, `sage-libs` – core execution engine, **job management** (`runtime/job_manager`), **node selection** (`scheduler/node_selector`), algorithms, scheduling logic, CPU/GPU awareness.
  - L4: `sage-middleware` – C++ operators and performance-critical components, built via CMake.
  - L5: `sage-apps`, `sage-benchmark` – applications and benchmark suites.
  - L6: `sage-cli`, `sage-studio`, `sage-tools`, `sage-gateway` – user-facing interfaces, CLI, web studio, tools, and OpenAI-compatible gateway.
- **Declarative dataflow** abstraction for specifying pipelines, with compilation/execution over heterogeneous resources.
- **Unified LLM & embedding control plane** (sageLLM): `UnifiedInferenceClient`, `ControlPlaneManager`, `HybridSchedulingPolicy`, `EmbeddingExecutor` coordinating multiple vLLM and embedding backends via `sage-gateway`.
- **User paths and configuration** following XDG base directory spec; project-level `.sage/` directory for build artifacts and caches.
- **Deployment and CI** patterns (quickstart scripts, `sage-dev` tooling, pre-commit hooks) as concrete implementation and reproducibility choices.

--- Task ---

Design a **System / Method section outline** tailored for a top-tier systems paper. The section should likely include 3–5 main subsections, for example:

- System Overview and Design Goals;
- Layered Architecture;
- Declarative Dataflow and Execution Model;
- LLM & Embedding Control Plane (sageLLM) as one important subsystem;
- Implementation Details and Deployment.

For each proposed subsection:

1. Provide a bullet list of **key questions** it should answer from a systems-reviewer perspective (e.g., how the system scales, how it abstracts hardware differences, how it improves programmability without sacrificing performance, how it supports reproducibility and observability).
2. Map these questions to **specific SAGE components** or modules (e.g., `sage-platform` and `sage-kernel` for job management and node selection, `sage.common.components.sage_llm` for control plane, `sage-middleware` for C++ operators, `sage-benchmark` for evaluation workloads).
3. Suggest **figures or diagrams** that should accompany this subsection (e.g., architecture diagram, dataflow diagram, control-plane timeline), with 1–2 sentences per figure describing what it should convey.
4. Indicate which subsections are **core** for the main paper and which details can be moved to an appendix if page limits are tight.

--- Output ---

- A structured outline with subsections and bullet points answering the above.
- No full prose yet.

______________________________________________________________________

## 4.2 逐小节撰写 System 文本

有了 4.1 的大纲后，你可以对每个小节单独调用下面的提示词写正文。

**提示词（可直接复制，每个小节复用）**

We have designed an outline for the System / Method section of our systems paper on **SAGE**. Now we will write the subsection:

> [INSERT SUBSECTION TITLE HERE, e.g., "Layered Architecture"]

Here is the bullet-point outline for this subsection (from the previous step):

[PASTE THE BULLET-POINT OUTLINE HERE]

--- System reminders ---

- SAGE uses a **6-layer architecture (L1–L6)** with no upward dependencies.
- It exposes **declarative dataflow** to users, while deeper layers handle scheduling, optimization, and execution.
- It includes a **unified control plane** for LLM and embedding services, fronted by an OpenAI-compatible gateway.
- It targets **scalability, heterogeneity (CPU/GPU), and reproducibility**.
- The paper should emphasize the **whole system** (architecture + dataflow + control plane + benchmarks + deployment), not just one component.

--- Task ---

Please write a detailed English subsection for a systems paper that:

1. Answers the bullet-point questions with **systems-level explanations** rather than just listing APIs.
2. Emphasizes how SAGE’s design choices (e.g., layering, declarative dataflow, control plane, benchmark integration, tooling) address concrete systems challenges (resource utilization, latency, cluster heterogeneity, debuggability, ease of evolution, reproducibility).
3. Includes **references to SAGE components** (module or package names) only when they help clarify the design (e.g., mentioning `sage-kernel` for job management and node selection, `sage-platform` for cluster configuration and services, `sage-benchmark` for evaluation workloads).
4. Suggests where to place figures or tables, and provides a short candidate **figure caption** if appropriate.

--- Output ---

1. The full text of the subsection in English (approx. 1–2 single-column pages, depending on importance).
2. A short list of **potential figure captions** and where they should appear.
3. Optional notes on which parts could be shortened if page limits are tight.

______________________________________________________________________

## 4.3 控制平面技术细节（可选强化）

如果你希望在系统论文中 **重点强化控制平面（sageLLM）这一子模块的系统贡献**，可以单独用下面的提示词撰写一个专门小节。注意：控制平面是 SAGE 的一个重要子系统，但论文整体仍然需要覆盖完整系统。

**提示词（可直接复制）**

We want to dedicate a focused subsection to the **LLM & embedding control plane** in SAGE ("sageLLM"). This subsection should be particularly convincing for systems reviewers who care about **resource management, scheduling, and scalability**.

--- Control plane architecture (from actual implementation) ---

- The control plane classifies requests into chat / generation vs. embedding.
- It uses policies such as `HybridSchedulingPolicy` to batch and route requests across a pool of vLLM and embedding engines.
- It aims to improve **throughput, tail latency, and SLO compliance** while sharing resources across heterogeneous LLM and embedding workloads.
- It is integrated with `sage-gateway`, which exposes an OpenAI-compatible API on well-defined ports from `SagePorts`.

Key components (module paths):

- `ControlPlaneManager`: `sageLLM/control_plane/manager.py` – core orchestrator.
- `RequestClassifier`: `sageLLM/control_plane/request_classifier.py` – request type detection.
- `HybridSchedulingPolicy`: `sageLLM/control_plane/strategies/hybrid_policy.py` – scheduling decisions.
- `EmbeddingExecutor`: `sageLLM/control_plane/executors/embedding_executor.py` – batched embedding execution.

--- Scheduling algorithm details to explain ---

The prompt should guide the model to explain:

1. **Request classification** (how chat / generation / embedding are distinguished, and with what overhead).
2. **Scheduling policy options** (e.g., FIFO, priority, SLO-aware, hybrid) and how they trade off fairness, latency, and throughput.
3. **Batching strategy** for LLM vs. embedding workloads, and interaction with vLLM’s continuous batching.
4. **Load balancing** across multiple backend engines under mixed workloads.
5. **Interaction with vLLM**: SAGE does not replace vLLM’s internal scheduler but provides cross-engine and cross-workload scheduling via an OpenAI-compatible interface.

--- Task ---

Please draft a detailed English subsection (around 1–1.5 single-column pages) that:

1. Explains the **design goals** of the control plane (unified scheduling, resource sharing, SLO compliance).
2. Describes the **architecture** and key components and how they interact.
3. Details the **scheduling algorithm** with pseudocode or an algorithmic description for `HybridSchedulingPolicy`.
4. Explains how **batching** works differently for LLM vs. embedding workloads.
5. Clarifies the **relationship with vLLM** (complementary, not replacement).
6. Prepares the ground for experiments comparing different scheduling policies and baselines.

--- Output ---

1. Full subsection text with technical depth.
2. Pseudocode for the core scheduling algorithm (if appropriate).
3. Suggested figures:
   - Figure X: Control Plane Architecture (component diagram).
   - Figure Y: Request Timeline showing classification, queuing, batching, execution under mixed workloads.

______________________________________________________________________

## 4.4 与 vLLM 关系的澄清（重要补充）

审稿人可能会质疑 SAGE 与 vLLM（或其它 LLM 引擎）的关系。这里提供专门的澄清引导。

**提示词（可直接复制）**

A reviewer might ask: "How does SAGE relate to vLLM? Isn’t vLLM already a highly optimized LLM serving system?"

Please draft a **clarification paragraph** (3–5 sentences) that explains:

1. **Complementarity, not competition**: SAGE uses vLLM (or other engines) as backend serving components. vLLM handles single-model inference optimization (PagedAttention, continuous batching). SAGE handles cross-model orchestration and embedding co-scheduling.
2. **Abstraction level difference**:
   - vLLM = single-model inference engine (optimizes GPU memory, batch processing for one model).
   - SAGE = pipeline-level control plane and systems platform (orchestrates multiple models, handles embedding services, provides unified API, integrates with dataflow and benchmarks).
3. **What SAGE adds**:
   - multi-engine load balancing;
   - unified LLM + embedding scheduling;
   - request classification and SLO-aware routing;
   - declarative pipeline composition and system-level benchmarks.
4. **Concrete example**: e.g., a RAG pipeline needing an embedding service + an LLM service. Without SAGE, operators must manually manage two services and balance load; with SAGE, they declare the pipeline and the control plane plus dataflow engine handle resource allocation and scheduling.

This paragraph should be inserted in the System section after describing the control plane architecture, and should clearly state that the **paper evaluates SAGE as a full system built on top of such engines**.

```

______________________________________________________________________

## 05_experiments.md

````markdown
# Experiments Prompts – SAGE Systems Paper

本文件帮助你为系统论文的 Experiments 部分设计结构和写作提示词。
**关键更新**：本提示词已与 `sage-benchmark` 中的实际实验脚本（`exp_5_1` 至 `exp_5_5`）和画图工具（`plotting.py`）完全对齐。

______________________________________________________________________

## 5.1 设计实验章节结构 (Structure Design)

**提示词（可直接复制）**

You are the experiments lead for a systems-track paper about **SAGE**.

--- System and evaluation context ---

SAGE is a system for **LLM/AI pipelines** with a unified control plane, declarative dataflow, and support for heterogeneous hardware.
We have implemented a comprehensive benchmark suite (`sage-benchmark`) with 5 specific experiments.

--- Task ---

Design the **structure** of the Experiments section. It MUST follow this exact 5-subsection structure to match our experimental results:

### 5.1 End-to-End Pipeline Performance
- **Goal**: Demonstrate SAGE's efficiency in executing complex, multi-stage pipelines (specifically RAG: Embedding -> Retrieval -> Generation).
- **Workload**: Simulated RAG pipeline with concurrent users; mixed embedding and LLM calls.
- **Key Figure**: **Latency CDF** (Cumulative Distribution Function) showing the distribution of end-to-end pipeline latencies.
- **Key Figure**: **Request Timeline** (Waterfall plot) showing the interleaving of embedding and generation tasks.

### 5.2 Control Plane Effectiveness
- **Goal**: Prove that SAGE's unified control plane (co-scheduling LLM and Embeddings) outperforms separate services.
- **Workload**: Mixed traffic (e.g., 70% Chat, 30% Embedding) at varying request rates.
- **Key Figure**: **Throughput vs. Latency** curve comparing "Unified Control Plane" vs. "Separate Services".
- **Key Figure**: **Latency CDF** comparing tail latencies (p99) of the two approaches.

### 5.3 Isolation & Fairness
- **Goal**: Show SAGE's ability to protect latency-sensitive "Interactive" users from high-throughput "Batch" users (Noisy Neighbors).
- **Workload**: Two concurrent user groups: "Interactive" (low rate, high priority) and "Batch" (high rate, low priority).
- **Key Figure**: **Latency CDF** for the Interactive user, comparing "With SAGE Isolation" vs. "Without Isolation".

### 5.4 Scalability
- **Goal**: Demonstrate linear scaling of throughput as backend resources increase.
- **Workload**: High-concurrency traffic against 1, 2, 4, and 8 vLLM backend instances.
- **Key Figure**: **Scalability Bar Chart** showing Request/Second (RPS) vs. Number of GPUs.

### 5.5 Heterogeneous Hardware Support
- **Goal**: Validate the benefit of offloading Embedding tasks to CPU nodes to save GPU resources for LLM inference.
- **Workload**: Mixed workload running on "GPU-only" vs. "Hybrid (GPU for LLM + CPU for Embed)" configurations.
- **Key Figure**: **Resource Efficiency** comparison (or Latency CDF showing minimal degradation with CPU offloading).

--- Output ---

- A structured outline for the Experiments section.
- For each subsection, write a short paragraph describing the **experimental setup** (workload, metrics) and the **expected visual evidence** (the figures mentioned above).

______________________________________________________________________

## 5.2 撰写具体实验分析 (Detailed Analysis Prompts)

以下提示词用于指导大模型撰写具体的实验分析段落。

### 5.1 End-to-End Pipeline Analysis

**Prompt:**
"Write the analysis for Section 5.1 (End-to-End Pipeline Performance).
The experiment ran a simulated RAG pipeline (Embed -> Retrieve -> Generate).
Refer to **Figure 5.1(a) (Latency CDF)**, which shows a tight latency distribution with a p99 of [X] ms, indicating stable performance.
Refer to **Figure 5.1(b) (Request Timeline)**, which illustrates how SAGE's scheduler efficiently interleaves embedding and generation tasks, minimizing gaps and maximizing resource usage."

### 5.2 Control Plane Analysis

**Prompt:**
"Write the analysis for Section 5.2 (Control Plane Effectiveness).
Compare SAGE's unified scheduling against a baseline of separate services.
Refer to **Figure 5.2 (Throughput vs. Latency)**. Highlight that SAGE sustains [Y]% higher throughput before latency saturation.
Explain that by co-scheduling, SAGE utilizes idle GPU cycles (during LLM decoding gaps) for embedding tasks, as evidenced by the lower tail latency in the **Latency CDF**."

### 5.3 Isolation Analysis

**Prompt:**
"Write the analysis for Section 5.3 (Isolation & Fairness).
Describe the 'Noisy Neighbor' scenario with Interactive vs. Batch users.
Refer to **Figure 5.3**, showing that without isolation, the Interactive user's p99 latency spikes to [A] ms.
With SAGE's priority-aware scheduling, the Interactive user's latency curve remains close to the baseline, demonstrating effective performance isolation."

### 5.4 Scalability Analysis

**Prompt:**
"Write the analysis for Section 5.4 (Scalability).
Refer to **Figure 5.4 (Scalability Bar Chart)**.
Observe that throughput scales nearly linearly from 1 to 8 GPUs.
Calculate the scaling efficiency (e.g., '7.2x speedup on 8 GPUs'), proving that the SAGE control plane introduces minimal overhead."

### 5.5 Heterogeneity Analysis

**Prompt:**
"Write the analysis for Section 5.5 (Heterogeneous Hardware).
Discuss the trade-off of offloading embeddings to CPU.
State that while CPU embedding latency is slightly higher, the overall system throughput for LLM tokens increases significantly because GPU resources are freed up.
Conclude that SAGE's flexible node selection enables cost-efficient deployments."
   - Test with 1, 2, 4, 8 vLLM instances (and optionally multiple embedding servers).
   - Measure: throughput, speedup vs. single-engine baseline, control-plane overhead ratio.
2. **Load scaling (requests per second)**
   - Sweep request rate from light load up to and beyond saturation.
   - Measure: throughput curve, latency curve (especially tail), SLO hit rate.
3. **Concurrent clients**
   - Test with 1, 10, 50, 100 concurrent clients.
   - Measure: per-client latency, fairness, starvation or head-of-line blocking.
4. **Model size scaling**
   - Test with different model sizes (e.g., 7B, 13B, 70B) if available.
   - Measure: how control-plane overhead compares to model inference time.

--- Experimental setup checklist ---

Ask the model to force the following information to be specified:

```text
Hardware specification:
- GPU type: [e.g., A100 40GB, RTX 4090]
- Number of GPUs: [e.g., 4]
- CPU cores: [e.g., 64]
- Memory: [e.g., 256 GB]
- Network: [e.g., InfiniBand, 10GbE]

Software versions:
- SAGE version: [e.g., 0.5.0]
- vLLM version: [e.g., 0.4.0]
- CUDA version: [e.g., 12.1]
- Python version: [e.g., 3.11]

Workload specification:
- LLM model: [e.g., Qwen2.5-7B-Instruct]
- Embedding model: [e.g., BGE-M3]
- Input token length: [e.g., 512 tokens]
- Output token length: [e.g., 128 tokens]
- Request arrival: [e.g., Poisson, bursty, constant]
```

--- Expected result formats ---

Table: Throughput vs. Number of Backends

| Backends | Throughput (req/s) | Speedup | Control Plane Overhead |
|---------:|--------------------:|--------:|------------------------:|
| 1        | [baseline]          | 1.0×    | [X]%                   |
| 2        | [?]                 | [?]×    | [?]%                   |
| 4        | [?]                 | [?]×    | [?]%                   |
| 8        | [?]                 | [?]×    | [?]%                   |

Figure: Latency vs. Request Rate

- X-axis: request rate (req/s)
- Y-axis: latency (ms)
- Lines: p50, p95, p99
- Mark saturation point and discuss where SAGE’s control plane becomes the bottleneck (if at all)

--- Output ---

1. A detailed experimental plan with specific configurations.
2. Expected table/figure formats.
3. Key claims the scalability study should support (e.g., near-linear scaling up to N backends, negligible control-plane overhead for large models).

______________________________________________________________________

## 5.3 为每类实验撰写结果描述

在你实际拿到实验数据之后，可以用下面的提示词为每类实验写结果段落。

**提示词（可直接复制，每个子节可复用）**

We now have experimental results for the subsection:

> [INSERT EXPERIMENT SUBSECTION TITLE HERE, e.g., "End-to-End Pipeline Performance" or "Scalability Study"]

Here is the design of this subsection (goal, workloads, metrics, baselines):

[PASTE THE DESIGN OUTLINE FOR THIS SUBSECTION HERE]

Here are the preliminary results (tables, plots, or bullet points):

[PASTE YOUR NUMERIC OR QUALITATIVE RESULTS HERE]

--- Task ---

Write the **Results and Analysis** text for this subsection in English, targeting systems reviewers.

Requirements:

1. Start by restating **what the experiment tries to verify** (e.g., whether the control plane improves tail latency under mixed workloads, whether declarative dataflow leads to better resource utilization, whether heterogeneous deployment is practical).
2. Describe **key trends in the results**, referencing specific metrics (throughput, latency, SLO satisfaction, success rates, cost-performance, etc.).
3. Clearly explain **why SAGE behaves better or differently** than baselines, relating back to design choices (layering, control plane, dataflow, CPU-only support, benchmarks, tooling).
4. If results are mixed, be honest and propose plausible explanations or follow-up experiments.
5. Propose **candidate figure/table captions** for the plots or tables we have, and specify which should be in the main paper vs. appendix.

--- Output ---

1. A few paragraphs of result description and analysis for this subsection.
2. A list of suggested figure/table captions with a short description each.
3. If applicable, a short note on what additional experiments could strengthen this story.

______________________________________________________________________

## 5.4 Baseline 选择指南（SAGE 特化）

**为什么需要仔细选择 baseline：** 系统论文审稿人会严格审视 baseline 是否公平、是否代表了 state-of-the-art。

| SAGE Feature                 | Recommended Baseline                                       | Why This Baseline                               |
|-----------------------------|------------------------------------------------------------|-------------------------------------------------|
| Layered architecture + dataflow | Ad-hoc Python scripts or flat microservices                | Shows maintainability / complexity differences  |
| Unified control plane       | vLLM + separate embedding service (manual load balancing)  | Shows the benefit of unified scheduling         |
| Hybrid scheduling           | SAGE with FIFO policy                                      | Ablation showing scheduling policy matters      |
| Multi-engine support        | Single vLLM instance                                       | Shows horizontal scaling works                  |
| CPU-only support            | GPU-only deployment or naive CPU-only baseline             | Shows cost-effectiveness and feasibility        |
| System-level benchmark      | AgentBench / ToolBench / single-engine benchmark           | Shows SAGE’s broader system metrics vs. others  |

Baseline 实现要求：

1. 所有 baseline 必须使用相同或明确定义的硬件配置。
2. vLLM baseline 必须使用相同版本和参数。
3. 如果无法使用相同硬件，必须说明并尽量归一化结果（例如用吞吐/成本等指标）。
4. 必须报告 baseline 的最优合理配置（不能故意用明显较差的配置）。

______________________________________________________________________

## 5.5 实验结果的可重复性

**系统论文对可重复性要求很高。** 确保包含以下信息：

```markdown
### Reproducibility Checklist

- [ ] Hardware specification (GPU model, memory, CPU cores, network)
- [ ] Software versions (SAGE, vLLM, CUDA, Python, key dependencies)
- [ ] Model details (model name, size, quantization if any)
- [ ] Workload specification (input/output length distribution, arrival pattern)
- [ ] Warm-up procedure (how many requests before measurement?)
- [ ] Measurement duration (how long did you run each experiment?)
- [ ] Number of repetitions (how many times did you repeat? error bars?)
- [ ] Code availability (will you release experiment scripts?)
```

建议在论文附录或 supplementary material 中包含：

1. 完整的实验配置文件；
2. 用于生成图表的原始数据；
3. 运行实验的脚本（可基于 `sage-dev` 或 `sage.benchmark` 的 CLI）。

````

______________________________________________________________________

## 06_contributions_example.md

```markdown
# SAGE – Example Contributions List (Systems Track)

本文件提供一份面向顶级 **Machine Learning Systems** track 的示例 "Contributions" 列表草案，你可以直接在 Introduction 末尾或单独小节中使用/修改。
重点是把 **整个 SAGE 系统** 的贡献讲清楚：分层架构、数据流、控制平面、异构部署、benchmark。

______________________________________________________________________

## 1. Example Contributions (English Draft)

Below is an example contributions list tailored to SAGE as a **machine learning system** rather than a pure algorithm or application.

1. **A layered architecture for declarative LLM/AI pipelines.**

   We introduce SAGE, a framework that organizes LLM/AI data processing pipelines into a strict six-layer architecture, from foundational utilities (`sage-common`) and platform services (`sage-platform`), through kernel and middleware components (`sage-kernel`, `sage-libs`, `sage-middleware`), up to applications and user-facing tools (`sage-apps`, `sage-benchmark`, `sage-cli`, `sage-studio`, `sage-tools`, `sage-gateway`). By enforcing **no upward dependencies**, SAGE cleanly separates concerns between configuration, scheduling, execution, and user interfaces, enabling independent evolution of layers, easier testing, and simplified large-scale system maintenance.

2. **A unified control plane for LLM and embedding workloads.**

   We design and implement a **sageLLM control plane** that jointly manages LLM and embedding workloads across a shared pool of engines. The control plane classifies requests (chat/generation vs. embeddings), applies hybrid scheduling and batching policies (e.g., `HybridSchedulingPolicy`), and exposes an OpenAI-compatible API via `sage-gateway` on standardized ports from `SagePorts`. This unified design improves resource utilization and **reduces tail latency** for mixed LLM+embedding traffic compared to siloed vLLM + separate embedding setups, while preserving a familiar client-facing interface.

3. **Systems support for heterogeneous CPU/GPU deployments with reproducible tooling.**

   SAGE provides kernel-level mechanisms for **CPU-only and GPU nodes**, job management (`sage-kernel/runtime`), and node selection (`sage-kernel/scheduler`), along with platform services (`sage-platform`) for storage, queuing, and service management, and C++ operators in `sage-middleware` for performance-critical paths. Together with reproducible installation and quality pipelines (`quickstart.sh`, `manage.sh`, `sage-dev`, pre-commit tooling), the system lowers the barrier to deploying complex LLM pipelines on heterogeneous clusters and makes end-to-end experiments repeatable for both developers and researchers.

4. **A comprehensive benchmark suite and reusable testbed for LLM-centric systems.**

   To evaluate the system, we provide `sage-benchmark`, which instantiates a range of workloads for **agent behavior** (tool selection, multi-step planning, timing decisions) and **control-plane scheduling** under diverse traffic patterns, as well as additional suites targeting **retrieval, memory, DB/TSDB components, and scheduler behavior** in LLM-centric pipelines. The suite reports not only task- or model-level accuracy but also systems metrics such as throughput, latency distribution, SLO satisfaction, and resource utilization, and it exposes standard interfaces so that alternative agents, scheduling algorithms, or middleware components can be plugged in and compared on a common testbed built on top of SAGE’s layered architecture and unified control plane.

If space is tight, you may merge (3) and (4) into a single contribution on **end-to-end deployment and evaluation**.

______________________________________________________________________

## 2. Quantitative Claims Checklist

Each contribution should have at least one **quantitative** claim. After experiments are complete, fill in the placeholders below:

| Contribution      | Claim Template                                                                            | Experiment Needed                          |
|-------------------|-------------------------------------------------------------------------------------------|--------------------------------------------|
| Architecture (1)  | "enables [X]% faster development iteration" OR "reduces configuration complexity by [Y]%" | Developer study or configuration/LOC comparison |
| Control Plane (2) | "reduces p99 latency by [X]% compared to vLLM + separate embedding"                     | Mixed LLM+embedding workload latency benchmark |
| Control Plane (2) | "improves throughput by [Y]× while maintaining p95 < [Z] ms"                             | Throughput vs. latency saturation study    |
| Control Plane (2) | "achieves [A]% SLO satisfaction vs. [B]% for baseline"                                   | SLO compliance under varied load           |
| Heterogeneous (3) | "supports CPU-only nodes with [X]% of GPU performance for embedding-heavy workloads"      | CPU vs. GPU embedding / pipeline benchmark |
| Benchmark (4)     | "reveals [specific insight, e.g., FIFO degrades p99 by [C]× vs. hybrid policy"           | Comparative scheduling/agent evaluation    |

这些模板可以帮助你在写论文时，系统性地把实验结果映射到贡献点。

______________________________________________________________________

## 3. Positioning vs. Existing Systems (for reviewer FAQs)

You can also prepare short Q&A snippets for reviewers:

**Q: How does SAGE differ from vLLM?**

> vLLM is a single-model inference engine optimized for GPU memory management and continuous batching. SAGE uses vLLM as a backend engine and adds: (1) cross-engine load balancing, (2) embedding service co-scheduling, (3) declarative pipeline composition, (4) SLO-aware request routing, and (5) system-level benchmarks.

**Q: How does SAGE differ from Ray Serve or KServe?**

> Ray Serve and KServe are generic ML serving frameworks. SAGE provides LLM-specific scheduling (distinguishing chat vs. generation vs. embedding), workload-aware batching, declarative dataflow for pipelines, and an OpenAI-compatible API that simplifies migration from cloud LLM APIs, plus benchmarks that focus on LLM-centric systems behavior.

**Q: How does SAGE differ from LangChain / LlamaIndex?**

> LangChain and LlamaIndex are application-level orchestration frameworks for prompt chaining and agent logic. SAGE operates at the systems level, providing the underlying resource management, scheduling, execution, and benchmarking infrastructure that LangChain-like frameworks could build upon.

**Q: Why is a unified LLM+embedding control plane needed?**

> Modern RAG and agent applications interleave embedding (for retrieval) and LLM (for generation) calls. Without unified scheduling, operators must manually balance multiple services, leading to resource fragmentation and suboptimal latency. SAGE’s control plane treats them as a single resource pool with workload-aware policies, integrated into a broader dataflow and benchmarking framework.

______________________________________________________________________

## 4. Chinese Summary（供自己校对用）

- **分层架构 + declarative pipeline**：强调 6 层、无上行依赖、关注点分离与可维护性。
- **统一控制平面**：LLM + Embedding 统一调度，混合请求分类、批处理、SLO，API 走 OpenAI 兼容 gateway。
- **异构集群与工程工具链**：CPU/GPU 混部、job/node 管理、C++ 中间件、统一安装与质量工具，突出 "implementation & scalability"。
- **系统化 benchmark**：既评估 agent 能力，也评估调度策略和 pipeline 行为，关注 throughput/latency/SLO 等系统指标。

你可以根据最终实验结果，把 `[X]%`, `[Y]×` 等占位符替换成实际数字。

```

______________________________________________________________________

## 07_system_outline_example.md

```markdown
# SAGE – Example System / Method Outline (Systems Track)

本文件给出一份结合 SAGE 实际结构的 System / Method 章节详细纲要示例，可与 `04_system_and_method.md` 里的提示词配合使用，用来介绍 **整个 SAGE 系统**，而不仅仅是控制平面。

______________________________________________________________________

## 1. High-Level Section Structure (Example)

A possible structure for the System / Method section of the paper is:

1. **System Overview and Design Goals**
2. **Layered Architecture**
3. **Declarative Dataflow and Execution Model**
4. **LLM & Embedding Control Plane (sageLLM)**
5. **Implementation Details and Deployment**

You can merge or split sections depending on page limits (e.g., combine 2+3, or 4+5).

______________________________________________________________________

## 2. Section – System Overview and Design Goals

**Questions to answer (systems-reviewer perspective)**

- What concrete **problems** does SAGE target that existing LLM serving or MLOps systems do not fully solve? (e.g., complex multi-step LLM pipelines, mixed LLM+embedding workloads, CPU-only environments, end-to-end evaluation and reproducibility.)
- What are the **design goals**: scalability, heterogeneity support, programmability, debuggability, reproducibility, ease of evolution?
- How does SAGE sit in the ML systems ecosystem: is it a serving system, a workflow engine, a control plane, a benchmark framework, or a combination?

**SAGE components to mention**

- Overview of packages under `packages/`: `sage-common`, `sage-platform`, `sage-kernel`, `sage-libs`, `sage-middleware`, `sage-apps`, `sage-benchmark`, `sage-cli`, `sage-studio`, `sage-tools`, `sage-gateway`.
- High-level illustration of how a user goes from writing a pipeline (via CLI/Studio/examples) to executing it on a heterogeneous cluster using SAGE.

**Suggested figures/diagrams**

- **Figure 1: SAGE System Overview.**  A block diagram showing the layers and their roles: user interfaces at the top, control plane and platform services in the middle, execution engines and operators at the bottom. Caption: *"High-level view of the SAGE system, highlighting its layered architecture and main components for LLM/AI pipelines."*

______________________________________________________________________

## 3. Section – Layered Architecture

**Questions to answer**

- How are the six layers defined, and what responsibilities does each layer have?
- Why enforce **no upward dependencies**? How does this help modularity, testing, and independent evolution?
- How does this layering compare to monolithic or ad-hoc LLM orchestration scripts or flat microservice designs?

**Mapping to SAGE components**

- L1 – `sage-common`: configuration (`config/config.yaml`), user paths (XDG), `SagePorts` for port allocation, shared components including `UnifiedInferenceClient` and control-plane core (`sageLLM/control_plane/`).
- L2 – `sage-platform`: platform services for storage, queuing, and service management; integration with cluster configuration (`config/cluster.yaml`).
- L3 – `sage-kernel`, `sage-libs`: execution kernels, job management (`runtime/job_manager`), node selection (`scheduler/node_selector`), CPU/GPU awareness, algorithms, and scheduling primitives.
- L4 – `sage-middleware`: C++ operators and performance-critical components.
- L5 – `sage-apps`, `sage-benchmark`: concrete applications and benchmark scenarios.
- L6 – `sage-cli`, `sage-studio`, `sage-tools`, `sage-gateway`: CLI commands (e.g., `sage llm serve`, `sage gateway start`), web studio, tools, and OpenAI-compatible API.

**Suggested figures**

- **Figure 2: Layered Architecture.**  A stacked diagram (L1 at bottom to L6 at top) with arrows only going downward. Caption: *"SAGE enforces a strict layering discipline with no upward dependencies, which simplifies reasoning about responsibilities and allows lower layers to be reused across tools, applications, and benchmarks."*

______________________________________________________________________

## 4. Section – Declarative Dataflow and Execution Model

**Questions to answer**

- How do users **declare** LLM/AI pipelines (e.g., composition of retrieval, tools, LLM calls, post-processing)?
- How does SAGE translate these declarations into an executable plan over its layers?
- How does the execution model handle **batching**, **parallelism**, and **resource allocation** across CPU/GPU nodes?
- How does this improve over ad-hoc scripts in terms of maintainability, performance, and correctness?

**SAGE components to mention**

- High-level APIs and examples under `examples/apps` 和 `examples/tutorials` that construct dataflows.
- Kernel/platform interaction for executing these dataflows, including job scheduling and node selection.
- Role of `sage-middleware` operators when a dataflow step is performance-critical.

**Suggested figures**

- **Figure 3: Declarative Dataflow Example.**  A diagram of a concrete pipeline (data ingestion → embedding → retrieval → LLM generation → post-processing), annotated with which layers are involved at each step.
- **Figure 4: Execution Model.**  A schematic showing how a declarative graph is compiled into tasks over nodes, with batching and scheduling hooks.

______________________________________________________________________

## 5. Section – LLM & Embedding Control Plane (sageLLM)

**Questions to answer**

- What are the **goals** of the control plane? (e.g., share resources across LLM and embedding workloads, improve throughput and tail latency, respect SLOs.)
- How are requests classified and routed? What are the main scheduling/batching policies?
- How does the control plane interact with the gateway and backends?
- How does it differ from a single vLLM instance or simple load balancer?
- How does it fit into the broader SAGE system (dataflow, benchmarks, deployment tools)?

**Mapping to SAGE components**

- `sage.common.components.sage_llm.UnifiedInferenceClient` (with unified `create()` entry point) and related control-plane modules under `sageLLM/control_plane/` including `ControlPlaneManager`, `RequestClassifier`, `HybridSchedulingPolicy`, and `EmbeddingExecutor`.
- `sage-gateway` FastAPI app and routes for LLM and embedding.
- `SagePorts` (`GATEWAY_DEFAULT`, `LLM_DEFAULT`, `EMBEDDING_DEFAULT`, etc.) and WSL2-aware port selection.

**Suggested figures**

- **Figure 5: Control Plane Architecture.**  Components: request classifier, scheduling policy (HybridSchedulingPolicy), execution coordinators for LLM and embeddings, backend engine pool.
- **Figure 6: Request Timeline under Mixed Workloads.**  Show how chat and embedding requests are batched and routed over time, contrasted with a naive baseline.

______________________________________________________________________

## 6. Section – Implementation Details and Deployment

**Questions to answer**

- What are the key implementation choices that matter for systems reviewers? (language choices, C++ integration, build system, packaging.)
- How does SAGE support **CPU-only** as well as GPU deployments in practice?
- How do quickstart scripts and `sage-dev` tooling enable **reproducible experiments** and CI?
- What operational practices (logging, configuration, user paths) are built in to support real users?

**SAGE components to mention**

- C++ middleware build (`packages/sage-middleware/src/...`, CMake, `.sage/build/`).
- Installation scripts: `quickstart.sh`, `manage.sh`, CI install wrappers.
- `sage-dev` commands for test, quality, and examples; pytest configuration under `tools/pytest.ini`.
- XDG-based user paths and directories for logs, models, and cache.

**Suggested figures / tables**

- **Table 1: Implementation Summary.**  Columns: language/components, lines of code (approx.), main dependencies, build artifacts.
- **Figure 7: Deployment and Tooling Workflow.**  From cloning the repo to running `quickstart.sh`, starting `sage gateway` and `sage llm`, and launching experiments.

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

```

______________________________________________________________________

## 08_paper_outline_example.md

```markdown
# SAGE Systems Paper – ICML-Style Outline

下面是基于当前 prompts 跑出的一版 **完整 ICML 风格 SAGE 论文草稿结构**，只包含章节标题与每节 2–3 句英文说明，默认面向顶级 Machine Learning Systems track（例如 ICML）。

---

## 1 Introduction

Introduces the rise of complex LLM/AI applications that compose retrieval, tools, and multiple models over heterogeneous CPU/GPU clusters, and argues that existing serving and MLOps systems lack unified support for such pipelines. States the goals and design principles of SAGE as a dataflow-based ML system, positions it between low-level LLM serving engines and high-level application frameworks, and outlines the main challenges (scalability, heterogeneity, programmability, reproducibility). Summarizes the paper’s contributions as a numbered list covering the layered architecture, declarative dataflow, unified LLM+embedding control plane, heterogeneous deployment support, and benchmark suite.

## 2 Related Work

Reviews prior work across several categories: LLM serving engines (e.g., vLLM, TensorRT-LLM), generic serving and workflow frameworks (e.g., Ray Serve, KServe, MLflow, Kubeflow), LLM application frameworks (e.g., LangChain, LlamaIndex, DSPy), and LLM benchmarks (e.g., AgentBench, ToolBench, HELM). For each category, explains what systems properties they target and why they are insufficient as end-to-end platforms for LLM+embedding dataflow pipelines. Concludes by positioning SAGE as a unified system that complements these efforts by providing layered architecture, declarative dataflow, a control plane, and system-level benchmarks.

## 3 System Overview and Design Goals

Provides a high-level view of the SAGE system, introducing its role as a Python-based framework for LLM/AI data processing pipelines built on a strict six-layer architecture. Describes the main design goals—scalability, support for heterogeneous CPU/GPU environments, programmability via declarative dataflow, observability, and reproducibility—and how they shape the system’s interfaces and components. Walks through the lifecycle of a typical SAGE pipeline from user specification (CLI/Studio/examples) to deployment and execution on a cluster.

## 4 Layered Architecture

Details the responsibilities of each layer from `sage-common` and `sage-platform` through `sage-kernel`/`sage-libs`, `sage-middleware`, `sage-apps`/`sage-benchmark`, up to `sage-cli`, `sage-studio`, `sage-tools`, and `sage-gateway`. Explains the “no upward dependencies” constraint and how it enables modularity, testing, independent evolution of layers, and reuse of lower layers across tools, applications, and benchmarks. Compares this disciplined layering with ad-hoc scripting or flat microservice deployments commonly seen in LLM systems.

## 5 Declarative Dataflow and Execution Model

Introduces SAGE’s declarative dataflow abstraction for specifying LLM/AI pipelines (e.g., retrieval, tools, LLM calls, post-processing) and contrasts it with imperative orchestration code. Describes how the platform and kernel layers compile dataflow graphs into executable tasks, handling batching, parallelism, and placement over heterogeneous CPU/GPU nodes. Discusses how this execution model improves maintainability and performance, and how middleware operators are used for performance-critical stages.

## 6 LLM & Embedding Control Plane (sageLLM)

Presents the design goals of the sageLLM control plane: unified scheduling of LLM and embedding workloads, improved throughput and tail latency, and SLO-aware resource management across multiple backends. Describes the architecture, including the `UnifiedInferenceClient`, request classification, scheduling policies such as `HybridSchedulingPolicy`, embedding executors, and their integration with `sage-gateway` and vLLM instances. Clarifies SAGE’s relationship to vLLM and similar engines, emphasizing that SAGE builds a cross-engine, cross-workload control plane and API layer on top of them rather than replacing their single-model schedulers.

## 7 Implementation Details and Deployment

Summarizes key implementation choices: Python 3.10+, C++ middleware with CMake builds, internal directory layout, and the use of XDG-compliant user paths for configuration, logs, models, and caches. Describes installation and tooling (e.g., `quickstart.sh`, `manage.sh`, `sage-dev`, CI configuration) that enable reproducible builds, testing, and code quality enforcement. Explains how SAGE supports CPU-only and GPU deployments in practice, including configuration of ports via `SagePorts`, cluster configuration files, and operational practices for monitoring and debugging.

## 8 Experiments

Outlines the experimental methodology and setup: hardware and software environment, models, workloads (end-to-end pipelines, mixed LLM+embedding traffic, heterogeneous deployments), and measurement procedures following reproducibility best practices. States the main experimental questions: end-to-end pipeline performance vs. baselines, effectiveness of the unified control plane and scheduling policies, scalability with backends and load, benefits of heterogeneous deployments, and insights from agent and system benchmarks. Previews the structure of the section, with subsections on: (8.1) End-to-End Pipeline Performance, (8.2) Control Plane Effectiveness, (8.3) Scheduling Policy Comparison, (8.4) Scalability, (8.5) Heterogeneous Hardware & CPU-only Support, and (8.6) Agent Capability & Benchmarking (if claimed).

## 9 Discussion

Reflects on the practical implications of deploying SAGE in real-world environments, including trade-offs between flexibility and complexity, and lessons learned from building and operating a multi-layer ML system. Discusses limitations such as dependency on underlying serving engines, potential bottlenecks in the control plane, and scenarios where simpler solutions may suffice. Outlines promising directions for future extensions, such as richer dataflow optimizations, tighter integration with external data systems, or additional scheduling policies.

## 10 Conclusion

Recaps the motivation for SAGE and the key design elements: layered architecture, declarative dataflow, unified LLM+embedding control plane, heterogeneous deployment support, and benchmark suite. Summarizes the main experimental findings in terms of performance, scalability, SLO satisfaction, and insights into agent and scheduling behavior. Emphasizes SAGE’s role as a reusable platform and testbed for future research on LLM-centric systems and invites the community to build on its architecture and benchmarks.

```
