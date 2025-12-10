# ICML System Track - Related Work Prompt# ICML System Track – Related Work Prompt

本文件提供撰写 Related Work（相关工作）部分的详细提示词，重点是系统视角和 SAGE 的定位。本文件提供撰写 Related Work（相关工作）部分的详细提示词，重点是系统视角和
SAGE 的定位。

______________________________________________________________________

## 3.1 相关工作分类与定位## 3.1 相关工作分类与定位

\*\*提示词（可直接复制）\*\***提示词（可直接复制）**

You are an ICML systems-track author responsible for the **Related Work** section of a paper about
**SAGE**, a framework for LLM/AI pipelines.You are an ICML systems-track author responsible for the
**Related Work** section of a paper about **SAGE**, a framework for LLM/AI pipelines.

--- System context (for positioning) ------ System context (for positioning) ---

- SAGE focuses on **system-level support for LLM/AI dataflow pipelines**, rather than general ML
  training.- SAGE focuses on **system-level support for LLM/AI dataflow pipelines**, rather than
  general ML training.

- Key system contributions include:- Key system contributions include:

  - A **6-layer architecture** with strict no-upward-dependency design. - A **6-layer architecture**
    with strict no-upward-dependency design.

  - **Declarative dataflow** for LLM/AI pipelines. - **Declarative dataflow** for LLM/AI pipelines.

  - A unified **LLM & embedding control plane** with hybrid scheduling and batching, exposed via an
    OpenAI-compatible gateway (`sage-gateway`). - A unified **LLM & embedding control plane** with
    hybrid scheduling and batching, exposed via an OpenAI-compatible gateway (`sage-gateway`).

  - Support for **CPU-only and GPU nodes** via `sage-kernel` (job management, node selection). -
    Support for **CPU-only and GPU nodes** via `sage-platform` (job management, node selection).

  - A **benchmark suite** (`sage-benchmark`) focusing on **agent capabilities** (tool selection,
    planning, timing) and **control-plane policies** (throughput, latency, SLO compliance). - A
    **benchmark suite** (`sage-benchmark`) focusing on **agent capabilities** (tool selection,
    planning, timing) and **control-plane policies** (throughput, latency, SLO compliance).

--- Detailed positioning against key systems (MUST address each) ------ Task ---

1. Propose a **taxonomy of related work** into 3–5 categories suitable for an ICML systems paper,
   for example (you may rename or adjust as needed):

**Category 1: LLM Serving Engines** - LLM serving and inference systems;

| System | Focus | SAGE Difference | - General ML workflow / MLOps and dataflow systems;

|--------|-------|-----------------| - Agent frameworks and tool-use systems;

| **vLLM** | Single-model continuous batching, PagedAttention for KV cache | SAGE uses vLLM as a
backend engine, adds cross-engine orchestration and embedding co-scheduling | - LLM evaluation and
benchmarking frameworks;

| **TensorRT-LLM** | NVIDIA-optimized inference, tensor parallelism | Hardware-specific
optimization; SAGE provides hardware-agnostic control plane above it | - Distributed systems /
resource management for ML workloads.

| **SGLang** | Structured generation, RadixAttention | Focus on generation efficiency; SAGE adds
pipeline composition and multi-workload scheduling |2. For each category:

| **Orca** | Iteration-level scheduling, selective batching | Pioneered fine-grained batching; SAGE
extends to multi-engine and embedding workloads | - Give 1–2 sentences summarizing **what this
category of work tries to achieve**, in terms of systems properties.

- Provide 2–3 sentences on **how SAGE differs** from typical works in this category, especially
  regarding:

Key contrast: These engines optimize **single-model inference**. SAGE operates at a **higher
abstraction level**, orchestrating multiple engines and embedding services under a unified control
plane. - multi-layer architecture for end-to-end LLM pipelines;

```
 - a **unified** LLM+embedding control plane (rather than just LLM serving);
```

**Category 2: ML Serving Frameworks** - benchmarks targeting **agent behavior** and **control-plane
scheduling**, not just model quality.

| System | Focus | SAGE Difference |3. Mark places where we should insert **specific citation
examples** (e.g., representative systems/papers in each category), but you do not need to name
specific papers unless you feel safe using well-known canonical examples.

|\--------|-------|-----------------|

| **Ray Serve** | General-purpose model serving, auto-scaling | Generic framework without
LLM-specific scheduling (no chat/embed distinction) |--- Output ---

| **KServe** | Kubernetes-native inference, model management | Deployment-focused; lacks LLM-aware
batching and scheduling policies |- A structured outline listing:

| **Triton Inference Server** | Multi-framework serving, dynamic batching | Model-centric; SAGE
provides pipeline-centric dataflow abstraction | - The proposed categories;

- For each category, a short paragraph summarizing it and briefly contrasting SAGE.

Key contrast: Generic serving frameworks lack **LLM-aware scheduling** (e.g., distinguishing chat
vs. generation vs. embedding, priority for interactive requests).- This outline should be detailed
enough that we could almost lift it directly into the paper, then refine names and add citations.

**Category 3: LLM Application Frameworks**---

| System | Focus | SAGE Difference |

|--------|-------|-----------------|## 3.2 完整 Related Work 草稿

| **LangChain** | Prompt chaining, agent orchestration | Application-level API; SAGE provides
underlying system infrastructure |

| **LlamaIndex** | Data indexing, RAG pipelines | Data-focused; SAGE provides execution runtime and
resource management |在 3.1 的基础上，你可以生成一版接近成品的 Related Work 文本。

| **DSPy** | Programmatic prompting, optimization | Prompt engineering focus; SAGE handles execution
and scheduling |

**提示词（可直接复制）**

Key contrast: These are **application-level orchestration** tools. SAGE provides **systems-level
infrastructure** (resource management, scheduling, execution) that such frameworks could build upon.

Now, using the taxonomy and short summaries we just designed for Related Work, please draft a **full
Related Work section** for our ICML systems paper on **SAGE**.

**Category 4: ML Workflow Platforms**

| System | Focus | SAGE Difference |Constraints and goals:

|--------|-------|-----------------|1. Organize the text into **subsections or logical paragraphs**,
one per category from the taxonomy.

| **MLflow** | Experiment tracking, model registry | Training-focused lifecycle management |2. For
each category:

| **Kubeflow** | K8s-based ML pipelines, training orchestration | Training pipeline focus, not
inference-optimized | - Start with 2–3 sentences summarizing the category and its main systems
concerns.

| **Airflow** | DAG-based workflow scheduling | Generic workflow; lacks ML-specific optimizations |
\- Then write 3–5 sentences positioning **SAGE** relative to this category, focusing on its
multi-layer architecture, unified control plane, declarative dataflow, and benchmarking suite.

- Include explicit phrases that emphasize **complementarity or orthogonality**, rather than
  dismissing prior work.

Key contrast: These focus on **training and experiment management**. SAGE focuses on **inference
pipelines** with real-time scheduling requirements.3. Throughout the text, clearly emphasize that
**SAGE is a systems contribution**: improved implementation and scalability, support for
heterogeneous hardware, resource management for LLM+embedding workloads, and comprehensive
evaluation infrastructure.

4. Leave **citation slots** in the form of `[REF: CATEGORY-KEY-EXAMPLE]` so that we can fill real
   references later.

**Category 5: LLM Benchmarks**

| System | Focus | SAGE Difference |Output:

|--------|-------|-----------------|- A 1.5–2 page (single-column equivalent) English draft of the
Related Work section, following the above structure.

| **AgentBench** | Agent task completion across environments | Task-level accuracy only, no system
metrics |- At the end, list all `[REF: ...]` slots you used, grouped by category, so we can map them
to actual papers later.

| **ToolBench** | Tool-use and API calling | API correctness focus, no scheduling evaluation | |
**HELM** | Holistic model evaluation | Model quality metrics, not system performance | | **vLLM
Benchmark** | Serving throughput/latency | Single-engine metrics, no control-plane policies |

Key contrast: Existing benchmarks focus on **task accuracy or single-engine metrics**. SAGE
benchmark evaluates **both agent capabilities AND system-level scheduling** (throughput, latency
distribution, SLO satisfaction, multi-tenant interference).

--- Task ---

1. Propose a **taxonomy of related work** into 4-5 categories based on the above, suitable for an
   ICML systems paper.
1. For each category:
   - Give 2-3 sentences summarizing **what this category of work tries to achieve**, in terms of
     systems properties.
   - Provide 3-5 sentences on **how SAGE differs** from typical works in this category, using the
     specific contrasts above.
   - Reference specific systems by name where appropriate.
1. Explicitly state the **gap that SAGE fills**: a unified control plane for LLM+embedding pipelines
   with declarative dataflow, sitting between low-level serving engines and high-level application
   frameworks.

--- Output ---

- A structured outline listing:
  - The proposed categories;
  - For each category, a short paragraph summarizing it and briefly contrasting SAGE.
- This outline should be detailed enough that we could almost lift it directly into the paper, then
  refine names and add citations.

______________________________________________________________________

## 3.2 完整 Related Work 草稿

在 3.1 的基础上，你可以生成一版接近成品的 Related Work 文本。

**提示词（可直接复制）**

Now, using the taxonomy and short summaries we just designed for Related Work, please draft a **full
Related Work section** for our ICML systems paper on **SAGE**.

Constraints and goals:

1. Organize the text into **subsections or logical paragraphs**, one per category from the taxonomy.
1. For each category:
   - Start with 2-3 sentences summarizing the category and its main systems concerns.
   - Name **specific representative systems** (vLLM, Ray Serve, LangChain, etc.) and briefly
     describe what they do.
   - Then write 3-5 sentences positioning **SAGE** relative to this category, focusing on:
     - Multi-layer architecture vs. monolithic design
     - Unified LLM+embedding control plane vs. single-workload focus
     - Declarative dataflow vs. imperative orchestration
     - System-level benchmark vs. task-only evaluation
   - Include explicit phrases that emphasize **complementarity** (e.g., "SAGE can use vLLM as a
     backend engine") rather than dismissing prior work.
1. Throughout the text, clearly emphasize that **SAGE is a systems contribution**: improved
   implementation and scalability, support for heterogeneous hardware, resource management for
   LLM+embedding workloads, and comprehensive evaluation infrastructure.
1. Include a **summary paragraph** at the end that synthesizes the positioning: SAGE fills the gap
   between low-level serving engines and high-level application frameworks.

Output:

- A 1.5-2 page (single-column equivalent) English draft of the Related Work section, following the
  above structure.
- Use actual system names rather than citation placeholders for well-known systems (vLLM, LangChain,
  Ray Serve, etc.).
