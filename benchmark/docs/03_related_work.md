# Related Work Prompts – SAGE Systems Paper

本文件提供撰写 Related Work（相关工作）部分的提示词，重点从 **系统视角** 对 SAGE
进行分类与定位，覆盖整个系统（分层架构、数据流、控制平面、benchmark），而不是只讨论某一个子模块。

______________________________________________________________________

## 3.1 相关工作分类与定位

**提示词（可直接复制）**

You are a systems-track author responsible for the **Related Work** section of a paper about
**SAGE**, a framework for LLM/AI pipelines.

--- System context (for positioning) ---

SAGE focuses on **system-level support for LLM/AI dataflow pipelines**, rather than general ML
training. Key system contributions include:

- A **5-layer architecture** with strict no-upward-dependency design, from `sage-common` and
  `sage-platform` to `sage-kernel` / `sage-libs`, `sage-middleware`, and user-facing tools
  (`sage-cli`, `sage-tools`). LLM inference is provided by independent `sageLLM` engine.
- **Declarative dataflow** for LLM/AI pipelines, mapping user-level pipeline descriptions to
  efficient execution on heterogeneous CPU/GPU clusters.
- A unified **LLM & embedding control plane** with hybrid scheduling and batching, exposed via an
  OpenAI-compatible gateway (in `sageLLM` independent package).
- Systems support for **CPU-only and GPU nodes**, job management and node selection in
  `sage-kernel`, platform services in `sage-platform`.
- A **benchmark suite** (`sage-benchmark`, independent repository) focusing on **agent
  capabilities** (tool selection, planning, timing) and **system-level scheduling** (throughput,
  latency distribution, SLO compliance, interference).

--- Task ---

1. Propose a **taxonomy of related work** into 4–5 categories suitable for a top-tier systems paper.
   A reasonable starting point is:

   - Category 1: LLM Serving Engines (e.g., vLLM, TensorRT-LLM, SGLang, Orca)
   - Category 2: ML Serving Frameworks and Workflow Platforms (e.g., Ray Serve, KServe, Triton,
     MLflow, Kubeflow, Airflow)
   - Category 3: LLM Application Frameworks and Agents (e.g., LangChain, LlamaIndex, DSPy, various
     agent tool-use frameworks)
   - Category 4: LLM Benchmarks and Evaluation Frameworks (e.g., AgentBench, ToolBench, HELM, vLLM
     benchmark)
   - (Optional) Category 5: Data & Storage Systems for AI Pipelines (e.g., vector DBs, TSDBs,
     dataflow systems that overlap with `sage.db`, `sage.tsdb`, `sage.flow`)

1. For each category:

   - Give 2–3 sentences summarizing **what this category of work tries to achieve**, in terms of
     systems properties (e.g., throughput, flexibility, observability, portability, fairness).
   - Provide 3–5 sentences on **how SAGE differs** from typical works in this category, explicitly
     referencing:
     - multi-layer architecture vs. monolithic designs;
     - **unified** LLM + embedding control plane vs. LLM-only serving;
     - declarative dataflow vs. imperative orchestration or ad-hoc scripts;
     - system-level benchmarks vs. task-only or single-engine benchmarks.
   - Mark where we should later insert **specific citation examples** (use placeholders like
     `[REF: VLLM]`, `[REF: RAY_SERVE]`, `[REF: LANGCHAIN]`).

1. Explicitly state the **gap that SAGE fills**: a unified, layered system for LLM+embedding
   dataflow pipelines with control-plane scheduling and comprehensive benchmarks, sitting between
   low-level serving engines and high-level application frameworks.

--- Output ---

- A structured outline listing:
  - The proposed categories;
  - For each category, a short paragraph summarizing it and briefly contrasting SAGE.
- The outline should be detailed enough that we could almost lift it directly into the paper, then
  refine names and add citations.

______________________________________________________________________

## 3.2 完整 Related Work 草稿

在 3.1 确定 taxonomy 和要点之后，你可以生成一版接近成品的 Related Work 文本。

**提示词（可直接复制）**

Now, using the taxonomy and short summaries we just designed for Related Work, please draft a **full
Related Work section** for our systems paper on **SAGE**.

Constraints and goals:

1. Organize the text into **subsections or logical paragraphs**, one per category from the taxonomy.
1. For each category:
   - Start with 2–3 sentences summarizing the category and its main systems concerns.
   - Name **specific representative systems** (e.g., vLLM, TensorRT-LLM, SGLang, Ray Serve, KServe,
     Triton, MLflow, Kubeflow, LangChain, LlamaIndex, DSPy, AgentBench, ToolBench, HELM) and briefly
     describe what they do.
   - Then write 3–5 sentences positioning **SAGE** relative to this category, focusing on:
     - multi-layer architecture vs. monolithic or flat designs;
     - unified LLM+embedding control plane vs. single-workload focus;
     - declarative dataflow vs. imperative orchestration;
     - system-level benchmark and experimental testbed vs. task-only evaluation.
   - Include explicit phrases that emphasize **complementarity or orthogonality** (e.g., "SAGE can
     use vLLM as a backend engine"), not just replacement.
1. Throughout the text, clearly emphasize that **SAGE is a systems contribution**: improved
   implementation and scalability, support for heterogeneous hardware, unified resource management
   for LLM+embedding workloads, and comprehensive evaluation infrastructure.
1. Include a **summary paragraph** at the end that synthesizes the positioning: SAGE fills the gap
   between low-level serving engines, generic serving / workflow systems, and high-level LLM
   application frameworks by providing a unified dataflow-based platform and control plane with
   benchmarks.

--- Output ---

- A 1.5–2 page (single-column equivalent) English draft of the Related Work section, following the
  above structure.
- Use actual system names for well-known systems; use `[REF: ...]` placeholders where you need
  citations.
- At the end, list all `[REF: ...]` slots used, grouped by category, so we can map them to actual
  papers later.
