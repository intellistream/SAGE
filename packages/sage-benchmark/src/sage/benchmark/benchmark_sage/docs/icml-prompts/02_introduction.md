# ICML System Track - Introduction Prompts# ICML System Track – Introduction Prompts

本文件提供多轮使用的引言（Introduction）写作提示词模版，更偏系统论文/实现与可扩展性视角。本文件提供多轮使用的引言（Introduction）写作提示词模版，更偏系统论文/实现与可扩展性视角。

______________________________________________________________________

## 2.1 生成引言整体结构## 2.1 生成引言整体结构

\*\*提示词（可直接复制）\*\***提示词（可直接复制）**

You are an ICML systems-track co-author. Help me design the **structure** of the Introduction for a
paper about **SAGE**, a machine learning systems framework.You are an ICML systems-track co-author.
Help me design the **structure** of the Introduction for a paper about **SAGE**, a machine learning
systems framework.

--- System context ------ System context ---

- Venue: ICML - Machine Learning Systems track.- Venue: ICML – Machine Learning Systems track.

- System: SAGE, a Python 3.10+ framework for **LLM/AI data processing pipelines** with **declarative
  dataflow**.- System: SAGE, a Python 3.10+ framework for **LLM/AI data processing pipelines** with
  **declarative dataflow**.

- Key systems aspects (you should keep them in mind for structuring the story):- Key systems aspects
  (you should keep them in mind for structuring the story):

  - Strict **6-layer architecture (L1-L6)** with no upward dependencies, separating concerns from
    common utilities (`sage-common`), to platform services (`sage-platform`), kernel and libraries
    (`sage-kernel`, `sage-libs`), C++ middleware operators (`sage-middleware`), applications &
    benchmarks, and finally user-facing interfaces (CLI, Studio, tools, OpenAI-compatible gateway).
    \- Strict **6-layer architecture (L1–L6)** with no upward dependencies, separating concerns from
    common utilities (`sage-common`), to platform services (`sage-platform`), kernel and libraries
    (`sage-kernel`, `sage-libs`), C++ middleware operators (`sage-middleware`), applications &
    benchmarks, and finally user-facing interfaces (CLI, Studio, tools, OpenAI-compatible gateway).

  - A unified **LLM & embedding control plane** that manages multiple vLLM and embedding backends,
    provides hybrid scheduling, batching, and SLO-aware policies, and is exposed via `sage-gateway`.
    \- A unified **LLM & embedding control plane** that manages multiple vLLM and embedding backends,
    provides hybrid scheduling, batching, and SLO-aware policies, and is exposed via `sage-gateway`.

  - Support for **CPU-only and GPU nodes**, job management (`sage-kernel/runtime`), node selection
    (`sage-kernel/scheduler`), and cluster configuration via `config/cluster.yaml`. - Support for
    **CPU-only and GPU nodes**, job management, node selection, and cluster configuration via
    `config/cluster.yaml` and `sage-platform`.

  - A **benchmark suite** in `sage-benchmark` to evaluate both **agent capabilities** and
    **control-plane policies**. - A **benchmark suite** in `sage-benchmark` to evaluate both **agent
    capabilities** and **control-plane policies**.

--- Positioning against existing systems (CRITICAL for novelty) ------ Task ---

When structuring the Introduction, explicitly address how SAGE differs from:Design a **4–6 paragraph
outline** (not full prose yet) for the Introduction that suits an ICML systems paper. For each
paragraph:

- **vLLM / TensorRT-LLM / SGLang**: These are single-model serving engines optimized for throughput
  via continuous batching. SAGE operates at a **higher abstraction level**, orchestrating multiple
  such engines plus embedding services under a unified control plane with cross-workload
  scheduling.1. State the **goal** of the paragraph (e.g., establish the broader context of LLM/AI
  systems, articulate challenges in managing complex LLM pipelines, highlight gaps in existing
  systems, introduce SAGE, summarize contributions).

- **Ray Serve / KServe**: Generic ML serving frameworks without LLM-specific optimizations. SAGE
  provides **LLM-aware scheduling** (e.g., distinguishing chat vs. generation vs. embedding,
  priority for interactive requests, SLO-aware batching).2. Provide a **bullet list of key points**
  that should appear in that paragraph, focusing on:

- **LangChain / LlamaIndex**: Application-level orchestration frameworks. SAGE is a **systems-level
  infrastructure** providing resource management, scheduling, and execution primitives that such
  frameworks could build upon. - systems challenges (scalability, heterogeneity of hardware,
  multiple LLM/embedding services, observability, configuration complexity);

- **MLflow / Kubeflow**: Training and experiment management platforms. SAGE focuses on **inference
  pipelines** with real-time scheduling requirements. - why existing frameworks (generic MLOps,
  standalone LLM serving, ad‑hoc scripts) do not fully address these for **LLM-centric pipelines**;

  - how SAGE’s architecture and control plane are designed around these challenges.

The key novelty claim should be: SAGE is the first system to provide a **unified control plane**
that jointly schedules LLM and embedding workloads with **declarative dataflow** abstractions and
**heterogeneous hardware support**, filling a gap between low-level serving engines and high-level
application frameworks.3. Mark where we should **mention the main contributions** as a numbered list
(e.g., at the end of the last paragraph of the Introduction).

4. Explicitly note any parts where you need more concrete details from me (e.g., particular
   workloads, cluster scale, or baseline systems).

--- Task ---

Design a **4-6 paragraph outline** (not full prose yet) for the Introduction that suits an ICML
systems paper. For each paragraph:--- Output ---

1. State the **goal** of the paragraph (e.g., establish the broader context of LLM/AI systems,
   articulate challenges in managing complex LLM pipelines, highlight gaps in existing systems,
   introduce SAGE, summarize contributions).- Output only the **paragraph-level outline** and bullet
   points.

1. Provide a **bullet list of key points** that should appear in that paragraph, focusing on:- Do
   **not** yet write the full paragraphs.

   - systems challenges (scalability, heterogeneity of hardware, multiple LLM/embedding services,
     observability, configuration complexity);

   - why existing frameworks (generic MLOps, standalone LLM serving, ad-hoc scripts) do not fully
     address these for **LLM-centric pipelines**;---

   - how SAGE's architecture and control plane are designed around these challenges.

1. **Include a "gap" paragraph** that explicitly contrasts SAGE with existing systems (vLLM, Ray
   Serve, LangChain, etc.) and articulates the specific niche SAGE fills.## 2.2 逐段写引言

1. Mark where we should **mention the main contributions** as a numbered list (e.g., at the end of
   the last paragraph of the Introduction).

1. Explicitly note any parts where you need more concrete details from me (e.g., particular
   workloads, cluster scale, or baseline systems).在拿到 2.1 中的“段落大纲”后，你可以逐段写作。下面是通用段落写作提示词模版。

--- Output ---**提示词（可直接复制，每段都可以复用）**

- Output only the **paragraph-level outline** and bullet points.

- Do **not** yet write the full paragraphs.We previously designed a paragraph-level outline for the
  Introduction of our ICML systems paper on **SAGE**. Now we will write **paragraph X**.

---Here is the outline for this paragraph (copied from the previous step):

## 2.2 逐段写引言[PASTE THE BULLET-POINT OUTLINE FOR PARAGRAPH X HERE]

在拿到 2.1 中的"段落大纲"后，你可以逐段写作。下面是通用段落写作提示词模版。--- Task ---

Using only the above outline and the following system context, write a full **English paragraph**
(8–12 sentences) suitable for an ICML systems-track Introduction.

**提示词（可直接复制，每段都可以复用）**

System context reminders (do not over-explain common knowledge, but use them to ground the text):

We previously designed a paragraph-level outline for the Introduction of our ICML systems paper on
**SAGE**. Now we will write **paragraph X**.- SAGE targets **LLM/AI pipelines**, not generic ML
training.

- It offers **declarative dataflow** and a **multi-layer architecture** with no upward dependencies.

Here is the outline for this paragraph (copied from the previous step):- It integrates a **unified
control plane** for LLM and embedding services, exposed via an OpenAI-compatible gateway.

- It provides **benchmarking** tools for both agent capabilities and control-plane policies.

[PASTE THE BULLET-POINT OUTLINE FOR PARAGRAPH X HERE]

Writing requirements:

--- Task ---1. Focus on **systems challenges and insights**, not just listing features.

Using only the above outline and the following system context, write a full **English paragraph**
(8-12 sentences) suitable for an ICML systems-track Introduction.2. Use **neutral, technical
language**; avoid buzzwords or marketing tone.

3. Make the paragraph **self-contained** but smoothly connectible to the previous and next
   paragraphs.

System context reminders (do not over-explain common knowledge, but use them to ground the text):4.
It is acceptable for the first draft to be slightly longer; at the end, suggest 1–2 sentences that
could be dropped if space is tight.

- SAGE targets **LLM/AI pipelines**, not generic ML training.

- It offers **declarative dataflow** and a **multi-layer architecture** with no upward
  dependencies.--- Output ---

- It integrates a **unified control plane** for LLM and embedding services, exposed via an
  OpenAI-compatible gateway.1. The full paragraph in English.

- It provides **benchmarking** tools for both agent capabilities and control-plane policies.2. A
  short bullet list of **possible trimming points** for later shortening.

Writing requirements:You do not need to restate the entire system description; just use what is
necessary to achieve the paragraph’s goal.

1. Focus on **systems challenges and insights**, not just listing features.
1. Use **neutral, technical language**; avoid buzzwords or marketing tone.
1. Make the paragraph **self-contained** but smoothly connectible to the previous and next
   paragraphs.
1. It is acceptable for the first draft to be slightly longer; at the end, suggest 1-2 sentences
   that could be dropped if space is tight.

--- Output ---

1. The full paragraph in English.
1. A short bullet list of **possible trimming points** for later shortening.

You do not need to restate the entire system description; just use what is necessary to achieve the
paragraph's goal.
