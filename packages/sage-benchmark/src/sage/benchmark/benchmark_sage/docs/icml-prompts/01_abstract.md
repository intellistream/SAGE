# ICML System Track - Abstract Prompt# ICML System Track – Abstract Prompt

下面是为 SAGE 撰写 ICML System track 摘要（Abstract）的提示词模版，你可以直接复制到对话中，并在标注位置补充信息。下面是为 SAGE 撰写 ICML System
track 摘要（Abstract）的提示词模版，你可以直接复制到对话中，并在标注位置补充信息。

______________________________________________________________________

\*\*提示词（可直接复制）\*\***提示词（可直接复制）**

You are an experienced ICML systems-track author. You help me write a **concise but technically rich
abstract** for a paper about **SAGE**, a machine learning systems framework.You are an experienced
ICML systems-track author. You help me write a **concise but technically rich abstract** for a paper
about **SAGE**, a machine learning systems framework.

--- Context about the paper and the system ------ Context about the paper and the system ---

- Target venue: **ICML - Machine Learning Systems track** (focus on improved implementation and
  scalability, hardware, libraries, distributed methods, etc.).- Target venue: **ICML – Machine
  Learning Systems track** (focus on improved implementation and scalability, hardware, libraries,
  distributed methods, etc.).

- System: **SAGE**, a Python 3.10+ framework for building LLM/AI data processing pipelines with
  declarative dataflow.- System: **SAGE**, a Python 3.10+ framework for building LLM/AI data
  processing pipelines with declarative dataflow.

- Key architectural points (you should weave them naturally into the abstract, not list them
  mechanically):- Key architectural points (you should weave them naturally into the abstract, not
  list them mechanically):

  - A strict **6-layer architecture (L1-L6)**: `sage-common`, `sage-platform`,
    `sage-kernel`/`sage-libs`, `sage-middleware`, `sage-apps`/`sage-benchmark`,
    `sage-cli`/`sage-studio`/`sage-tools`/`sage-gateway`, with **no upward dependencies** (each
    layer only depends on lower layers). - A strict **6-layer architecture (L1–L6)**: `sage-common`,
    `sage-platform`, `sage-kernel`/`sage-libs`, `sage-middleware`, `sage-apps`/`sage-benchmark`,
    `sage-cli`/`sage-studio`/`sage-tools`/`sage-gateway`, with **no upward dependencies** (each
    layer only depends on lower layers).

  - **Declarative dataflow** for constructing LLM/AI pipelines: users specify high-level dataflow,
    the platform/kernel/middleware layers handle optimized execution. - **Declarative dataflow** for
    constructing LLM/AI pipelines: users specify high-level dataflow, the platform/kernel/middleware
    layers handle optimized execution.

  - A unified **LLM & embedding control plane** ("sageLLM") exposed via an **OpenAI-compatible
    gateway** (`sage-gateway`), providing request classification, hybrid scheduling, batching,
    resource sharing across multiple vLLM / embedding instances. - A unified **LLM & embedding
    control plane** ("sageLLM") exposed via an **OpenAI-compatible gateway** (`sage-gateway`),
    providing request classification, hybrid scheduling, batching, resource sharing across multiple
    vLLM / embedding instances.

  - Support for **CPU-only and GPU nodes**, job management and node selection via `sage-kernel`. -
    Support for **CPU-only and GPU nodes**, job management and node selection via `sage-platform`.

  - A **benchmark suite** (`sage-benchmark`) for both **agent capabilities** (tool selection, task
    planning, timing decisions) and **control-plane scheduling policies** (throughput, latency, SLO
    compliance). - A **benchmark suite** (`sage-benchmark`) for both **agent capabilities** (tool
    selection, task planning, timing decisions) and **control-plane scheduling policies**
    (throughput, latency, SLO compliance).

- Implementation characteristics (you may mention them briefly if they help emphasize the systems
  contribution):- Implementation characteristics (you may mention them briefly if they help
  emphasize the systems contribution):

  - C++ middleware operators (`sage-middleware`) with CMake-based build. - C++ middleware operators
    (`sage-middleware`) with CMake-based build.

  - Unified CI, quality tools (Ruff, Mypy), and reproducible quickstart scripts. - Unified CI,
    quality tools (Ruff, Mypy), and reproducible quickstart scripts.

--- Quantitative Claims Template (CRITICAL - fill in after experiments) ---I will later plug in
exact experiment results; for now, you can use **qualitative placeholders** like "we demonstrate
improvements in throughput and tail latency over baselines".

The abstract MUST include quantitative claims. Use these placeholders and replace with actual
numbers:--- Writing goals ---

Please draft a **150–200 word** English abstract that:

````1. Starts with 2–3 sentences of **problem context**: complexity of LLM/AI pipelines, challenges in managing dataflow, heterogeneous resources, and multiple LLM/embedding services.

Performance claims (choose 2-3 most impactful):2. Then gives a **high-level description of SAGE** as a systems contribution, emphasizing:

- "reduces p99 latency by [X]% compared to [baseline] under mixed LLM+embedding workloads"   - its **layered architecture** and separation of concerns;

- "improves throughput by [Y]x over [baseline] while maintaining [Z]ms p95 latency SLO"   - the **declarative dataflow** interface;

- "achieves [A]% SLO satisfaction rate vs. [B]% for [baseline] under [workload] traffic"   - the **unified control plane** and gateway for LLM/embedding workloads.

- "reduces resource utilization variance by [C]% across heterogeneous CPU/GPU nodes"3. Clearly states **2–4 concrete contributions** that an ICML systems reviewer can check, such as:

   - an architecture that enables modular, scalable LLM pipelines;

Agent capability claims (if applicable):   - a control-plane design that improves utilization/latency across LLM and embedding services;

- "improves tool selection accuracy by [D]% on [benchmark]"   - an evaluation suite that probes both agent capabilities and control-plane performance.

- "reduces planning latency by [E]% while maintaining [F]% task success rate"4. Ends with 1–2 sentences summarizing **experimental evidence**, using placeholders if needed, e.g., mentioning improvements in throughput, latency, SLO satisfaction, and/or agent task success on representative workloads and benchmarks.



Scale claims:--- Style constraints ---

- "evaluated on clusters with up to [G] GPU nodes and [H] concurrent requests"- ICML-style academic English, **precise and neutral**, no marketing language.

- "supports [I] requests per second with [J] backend engines"- Avoid buzzwords; focus on **what the system does, why it is needed, and how well it performs**.

```- If needed, slightly exceed 200 words in the first draft and then propose where to cut.



--- Writing goals ------ Output format ---

Please draft a **150-200 word** English abstract that:1. Provide **one candidate abstract**.

1. Starts with 2-3 sentences of **problem context**: complexity of LLM/AI pipelines, challenges in managing dataflow, heterogeneous resources, and multiple LLM/embedding services.2. Then list **3–5 bullet-point suggestions** on how we might refine it once we have concrete experimental numbers and more precise baseline descriptions.

2. Then gives a **high-level description of SAGE** as a systems contribution, emphasizing:
   - its **layered architecture** and separation of concerns;
   - the **declarative dataflow** interface;
   - the **unified control plane** and gateway for LLM/embedding workloads.
3. Clearly states **2-4 concrete contributions** that an ICML systems reviewer can check, such as:
   - an architecture that enables modular, scalable LLM pipelines;
   - a control-plane design that improves utilization/latency across LLM and embedding services;
   - an evaluation suite that probes both agent capabilities and control-plane performance.
4. Ends with **quantitative experimental claims** using the placeholder format above. This is CRITICAL - vague statements like "improves performance" are not acceptable.

--- Style constraints ---
- ICML-style academic English, **precise and neutral**, no marketing language.
- Avoid buzzwords; focus on **what the system does, why it is needed, and how well it performs**.
- Include at least ONE specific quantitative claim (with placeholder) in the abstract.
- If needed, slightly exceed 200 words in the first draft and then propose where to cut.

--- Output format ---
1. Provide **one candidate abstract** with quantitative placeholders clearly marked as [X], [Y], etc.
2. List the **specific experiments needed** to fill each placeholder.
3. Then list **3-5 bullet-point suggestions** on how we might refine it once we have concrete experimental numbers.

---

## Example Abstract Structure

````

[Problem context - 2-3 sentences] Modern LLM applications require complex pipelines combining...
However, existing approaches...

[System description - 2-3 sentences]\
We present SAGE, a framework that... SAGE introduces a unified control plane that...

[Key contributions - 2-3 sentences] Our main contributions are: (1) a layered architecture that...;
(2) a control plane with...; (3) a benchmark suite that...

[Quantitative results - 1-2 sentences] Experiments show SAGE reduces p99 latency by [X]% and
improves throughput by [Y]x compared to [baseline] on [workload], while achieving [Z]% SLO
satisfaction.

```
```
