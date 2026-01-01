# Abstract Prompt – SAGE Systems Paper

下面是为 SAGE 撰写 **系统论文摘要（Abstract）** 的提示词模版，你可以直接复制到对话中，并在标注位置补充信息。 默认面向顶级机器学习系统会议的系统 track（例如 ICML
Machine Learning Systems track），但提示词本身不依赖具体会议名称。

______________________________________________________________________

## 提示词（可直接复制给大模型）

You are an experienced systems-track author. You help me write a **concise but technically rich
abstract** for a paper about **SAGE**, a machine learning systems framework.

--- Context about the paper and the system ---

- Target venue: a **top-tier Machine Learning Systems track** (focus on implementation, scalability,
  hardware, libraries, distributed methods, etc.) of ICML conference.
- System: **SAGE**, a Python 3.10+ framework for building **LLM/AI data processing pipelines** with
  **declarative dataflow**.
- Goal of the paper: present SAGE as a **full-stack dataflow-based ML system**, not just an LLM
  control plane.

Key architectural points (you should weave them naturally into the abstract, not list them
mechanically):

- A strict **6-layer architecture (L1–L6)**: `sage-common`, `sage-platform`, `sage-kernel` /
  `sage-libs`, `sage-middleware`, `sage-apps` / `sage-benchmark`, `sage-cli` / `sage-studio` /
  `sage-tools` / `sage-gateway`, with **no upward dependencies** (each layer only depends on lower
  layers).
- **Declarative dataflow** for constructing LLM/AI pipelines: users declare high-level pipelines,
  while platform, kernel, and middleware layers compile them into an efficient execution plan across
  heterogeneous resources.
- A unified **LLM & embedding control plane** ("sageLLM"), exposed via an **OpenAI-compatible
  gateway** (`sage-gateway`), providing request classification, hybrid scheduling, batching, and
  resource sharing across multiple vLLM / embedding instances.
- **CPU-only and GPU node support**, with job management and node selection in `sage-kernel`
  (runtime, scheduler) and cluster configuration / services in `sage-platform`.
- A **comprehensive benchmark suite** (`sage-benchmark`) that evaluates both **agent capabilities**
  (tool selection, task planning, timing decisions) and **system-level behavior** (throughput,
  latency distribution, SLO compliance, interference) for different SAGE subsystems.
- Implementation characteristics that highlight systems engineering effort: C++ middleware operators
  (`sage-middleware`) with CMake-based build; unified CI and quality tools (Ruff, Mypy);
  reproducible quickstart scripts; XDG-based user paths and configuration.

--- Quantitative claims template (to be filled after experiments) ---

The abstract MUST include at least **one concrete quantitative claim**. You can use placeholders now
and replace them with actual numbers later. Typical patterns include:

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

1. Starts with 2–3 sentences of **problem context**: complexity of modern LLM/AI pipelines,
   challenges in managing dataflow, heterogeneous resources, and multiple LLM / embedding services.
1. Gives a **high-level description of SAGE** as a systems contribution, emphasizing:
   - its **layered architecture** and separation of concerns;
   - the **declarative dataflow** interface and execution model;
   - the **unified control plane** and gateway for LLM / embedding workloads;
   - its role as a **general platform** for LLM-centric pipelines, not only a control-plane module.
1. Clearly states **2–4 concrete contributions** that a systems reviewer can check, such as:
   - a layered architecture that enables modular, scalable LLM/AI pipelines;
   - a control-plane design that improves utilization / latency across LLM and embedding services;
   - heterogeneous CPU/GPU support and reproducible tooling that simplify deployment;
   - a benchmark suite that probes both agent capabilities and system-level performance.
1. Ends with **quantitative experimental claims** using the placeholder format above (no vague
   "improves performance" statements).

--- Style constraints ---

- Use **academic, precise, neutral English** typical of top-tier systems papers.
- Avoid buzzwords and marketing language; focus on **what the system does**, **why it is needed**,
  and **how well it performs**.
- Clearly mark all quantitative placeholders as `[X]`, `[Y]`, etc., so we can later map them to
  specific experiments.
- If needed, you may slightly exceed 200 words in the first draft and then suggest where to cut.

--- Output format ---

1. Provide **one candidate abstract** with quantitative placeholders clearly marked.
1. List the **specific experiments needed** to fill each placeholder (e.g., mixed workload latency
   benchmark, scalability study, agent benchmark).
1. Provide **3–5 bullet-point suggestions** on how we might refine the abstract once we have
   concrete experimental numbers and finalized baselines.

______________________________________________________________________

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
