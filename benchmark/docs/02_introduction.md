# Introduction Prompts – SAGE Systems Paper

本文件提供多轮使用的引言（Introduction）写作提示词模版，面向顶级机器学习系统会议的系统 track（例如 ICML Machine Learning Systems track）。
整体目标是：以 **完整的 SAGE 系统** 为主角，而不是只讲某个子模块（例如 control plane）。

______________________________________________________________________

## 2.1 生成引言整体结构

**提示词（可直接复制）**

You are a systems-track co-author. Help me design the **structure** of the Introduction for a paper
about **SAGE**, a machine learning systems framework.

--- System context ---

- Target venue: a **top-tier Machine Learning Systems track**.
- System: **SAGE**, a Python 3.10+ framework for **LLM/AI data processing pipelines** with
  **declarative dataflow**.
- SAGE should be presented as a **full-stack system**, covering:
  - a strict **6-layer architecture (L1–L6)** with no upward dependencies, from `sage-common` and
    `sage-platform` up to `sage-cli`, `sage-studio`, `sage-tools`, and `sage-gateway`;
  - **declarative dataflow** for composing LLM/AI pipelines (e.g., retrieval, tools, LLM calls,
    post-processing);
  - a **unified LLM & embedding control plane** (sageLLM) exposed via `sage-gateway`;
  - **CPU-only and GPU deployments**, job management and node selection in `sage-kernel`, platform
    services in `sage-platform`;
  - **benchmark suites** in `sage-benchmark` for agents, scheduling policies, RAG, DB/time-series
    components, etc.

--- Positioning against existing systems (CRITICAL for novelty) ---

When structuring the Introduction, explicitly address how SAGE differs from **all** of the following
(not only control-plane-level systems):

- **LLM serving engines** such as vLLM, TensorRT-LLM, SGLang: they optimize single-model inference;
  SAGE operates at a **higher abstraction level**, orchestrating multiple engines, embedding
  services, and full pipelines under a unified dataflow and control plane.
- **ML serving frameworks** such as Ray Serve, KServe, Triton Inference Server: they are generic
  serving or deployment platforms; SAGE provides **LLM-aware scheduling**, declarative pipelines,
  and end-to-end evaluation for LLM-centric workloads.
- **LLM application frameworks** such as LangChain, LlamaIndex, DSPy: they focus on
  application-level orchestration; SAGE is a **systems-level infrastructure** providing resource
  management, scheduling, and execution primitives that such frameworks could build upon.
- **ML workflow / MLOps platforms** such as MLflow, Kubeflow, Airflow: they emphasize training and
  generic workflows; SAGE focuses on **inference pipelines** with real-time scheduling,
  heterogeneous hardware, and LLM-specific concerns.
- **LLM benchmarks** such as AgentBench, ToolBench, HELM, single-engine vLLM benchmarks: they focus
  on task accuracy or single-engine metrics; SAGE adds **system-level benchmarks** that stress
  control-plane, dataflow, and heterogeneous deployments.

The key novelty claim should be: SAGE is a **full ML system** that combines a layered architecture,
declarative dataflow, a unified LLM + embedding control plane, heterogeneous deployment support, and
comprehensive benchmarks, filling the gap between low-level serving engines and high-level
application frameworks.

--- Task ---

Design a **4–6 paragraph outline** (not full prose yet) for the Introduction that suits a top-tier
systems paper on SAGE. For each paragraph:

1. State the **goal** of the paragraph (e.g., establish broader context of LLM/AI systems,
   articulate challenges in managing complex LLM pipelines, highlight gaps in existing systems,
   introduce SAGE, summarize contributions, preview experiments).
1. Provide a **bullet list of key points** that should appear in that paragraph, focusing on:
   - systems challenges (scalability, hardware heterogeneity, multiple LLM/embedding services,
     observability, configuration complexity, reproducibility);
   - why existing frameworks (generic MLOps, standalone LLM serving, ad-hoc scripts,
     application-level orchestrators) do not fully address these for **LLM-centric pipelines**;
   - how SAGE’s architecture, dataflow model, control plane, and benchmarks are designed around
     these challenges.
1. Mark where we should **present the main contributions** as a numbered list (usually at the end of
   the last or second-to-last paragraph).
1. Explicitly note any parts where you need more concrete details from me (e.g., workloads, cluster
   scale, baselines, key SAGE subsystems highlighted in experiments).

--- Output ---

- A paragraph-level outline (4–6 paragraphs), each with:
  - a short description of the paragraph goal;
  - bullet points of content to cover.
- Do **not** yet write the full paragraphs.

______________________________________________________________________

## 2.2 逐段写引言

在拿到 2.1 中的段落大纲后，你可以按段落逐个生成英文正文。

**提示词（可直接复制，每段都可以复用）**

We previously designed a paragraph-level outline for the Introduction of our systems paper on
**SAGE**. Now we will write **paragraph X**.

Here is the outline for this paragraph (copied from the previous step):

[PASTE THE BULLET-POINT OUTLINE FOR PARAGRAPH X HERE]

--- System context reminders ---

- SAGE targets **LLM/AI pipelines**, not generic ML training.
- It offers **declarative dataflow** and a **multi-layer architecture** with no upward dependencies.
- It includes a **unified control plane** for LLM and embedding services, exposed via an
  OpenAI-compatible gateway.
- It provides **benchmarking** tools for agent capabilities, scheduling policies, and other
  subsystems (RAG, DB, TSDB, etc.).
- The paper is about the **whole SAGE system** (architecture + dataflow + control plane +
  benchmarks), not only a single module.

--- Task ---

Using only the above outline and the system context, write a full **English paragraph** (8–12
sentences) suitable for a top-tier systems-track Introduction.

Writing requirements:

1. Focus on **systems challenges and insights**, not just listing features.
1. Use **neutral, technical language**; avoid buzzwords or marketing tone.
1. Make the paragraph **self-contained**, but naturally connectible to the previous and next
   paragraphs.
1. It is acceptable for the first draft to be slightly longer; at the end, suggest 1–2 sentences
   that could be dropped if space is tight.

--- Output ---

1. The full paragraph in English.
1. A short bullet list of **possible trimming points** (sentences that could be removed if we need
   to shorten the Introduction).

你不需要在每一段里重复完整的系统描述，只要引用必要的关键信息即可，使整篇引言连贯、系统、而且覆盖整个 SAGE。
