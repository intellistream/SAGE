# SAGE - Example Contributions List (ICML Machine Learning Systems Track)# SAGE – Example Contributions List (ICML Machine Learning Systems Track)

> 本文件提供一份面向 ICML **Machine Learning Systems** track 的示例"Contributions"列表草案，你可以直接在 Introduction
> 末尾或单独小节中使用/修改。> 本文件提供一份面向 ICML **Machine Learning Systems** track 的示例“Contributions”列表草案，你可以直接在
> Introduction 末尾或单独小节中使用/修改。

## 1. Example Contributions (English Draft)## 1. Example Contributions (English Draft)

Below is an example contributions list tailored to SAGE as a **machine learning system** rather than
a pure algorithm or application.Below is an example contributions list tailored to SAGE as a
**machine learning system** rather than a pure algorithm or application.

1. **A layered architecture for declarative LLM/AI pipelines.** 1. **A layered architecture for
   declarative LLM/AI pipelines.**

   We introduce SAGE, a framework that organizes LLM/AI data processing pipelines into a strict
   six-layer architecture, from foundational utilities (`sage-common`) and platform services
   (`sage-platform`), through kernel and middleware components (`sage-kernel`, `sage-libs`,
   `sage-middleware`), up to applications and user-facing tools (`sage-apps`, `sage-benchmark`,
   `sage-cli`, `sage-studio`, `sage-tools`, `sage-gateway`). By enforcing **no upward
   dependencies**, SAGE cleanly separates concerns between configuration, scheduling, execution, and
   interfaces, enabling independent evolution of layers and simplifying large-scale system
   maintenance. We introduce SAGE, a framework that organizes LLM/AI data processing pipelines into
   a strict six-layer architecture, from foundational utilities (`sage-common`) and platform
   services (`sage-platform`), through kernel and middleware components (`sage-kernel`, `sage-libs`,
   `sage-middleware`), up to applications and user-facing tools (`sage-apps`, `sage-benchmark`,
   `sage-cli`, `sage-studio`, `sage-tools`, `sage-gateway`). By enforcing **no upward
   dependencies**, SAGE cleanly separates concerns between configuration, scheduling, execution, and
   interfaces, enabling independent evolution of layers and simplifying large-scale system
   maintenance.

1. **A unified control plane for LLM and embedding workloads.** 2. **A unified control plane for LLM
   and embedding workloads.**

   We design and implement a **sageLLM control plane** that jointly manages LLM and embedding
   workloads across a shared pool of engines. The control plane classifies requests (chat/generation
   vs. embeddings), applies hybrid scheduling and batching policies (`HybridSchedulingPolicy`), and
   exposes an OpenAI-compatible API via `sage-gateway`. This unified design **reduces p99 latency by
   \[X\]%** and **improves throughput by [Y]x** for mixed LLM+embedding traffic compared to siloed
   vLLM+separate-embedding setups, while achieving **[Z]% SLO satisfaction** under [workload]
   traffic patterns. We design and implement a **sageLLM control plane** that jointly manages LLM
   and embedding workloads across a shared pool of engines. The control plane classifies requests
   (chat/generation vs. embeddings), applies hybrid scheduling and batching policies, and exposes an
   OpenAI-compatible API via `sage-gateway` on standardized ports defined in `SagePorts`. This
   unified design improves resource utilization and **reduces tail latency** for mixed LLM+embedding
   traffic compared to siloed serving setups, while preserving a familiar client-facing interface.

1. **Systems support for heterogeneous CPU/GPU deployments with reproducible tooling.** 3. **Systems
   support for heterogeneous CPU/GPU deployments with reproducible tooling.**

   SAGE provides kernel-level mechanisms for **CPU-only and GPU nodes**, job management
   (`sage-kernel/runtime`), and node selection (`sage-kernel/scheduler`) along with platform
   services (`sage-platform`) for storage and queuing, as well as C++ operators in `sage-middleware`
   for performance-critical paths. Together with reproducible installation and quality pipelines
   (`quickstart.sh`, `sage-dev`, pre-commit tooling), the system lowers the barrier to deploying
   complex LLM pipelines on heterogeneous clusters and makes end-to-end experiments repeatable for
   both developers and researchers. SAGE provides kernel-level mechanisms for **CPU-only and GPU
   nodes**, job management (`sage-kernel/runtime`), and node selection (`sage-kernel/scheduler`)
   along with platform services (`sage-platform`) for storage and queuing, as well as C++ operators
   in `sage-middleware` for performance-critical paths. Together with reproducible installation and
   quality pipelines (`quickstart.sh`, `sage-dev`, pre-commit tooling), the system lowers the
   barrier to deploying complex LLM pipelines on heterogeneous clusters and makes end-to-end
   experiments repeatable for both developers and researchers.

1. **A comprehensive benchmark suite that evaluates both agent capabilities and system
   performance.** 4. **A comprehensive benchmark suite and reusable testbed for LLM-centric
   systems.**

   Unlike existing LLM benchmarks that focus solely on task accuracy (e.g., AgentBench, ToolBench)
   or single-engine throughput (e.g., vLLM benchmark), `sage-benchmark` provides workloads that
   stress-test **both agent-level correctness AND system-level scheduling**. It includes: To
   evaluate the system, we provide `sage-benchmark`, which instantiates a range of workloads for
   **agent behavior** (tool selection, multi-step planning, timing) and **control-plane scheduling**
   under diverse traffic patterns, as well as additional suites targeting **retrieval, memory, and
   scheduler components** in LLM-centric pipelines. The suite reports not only task- or model-level
   accuracy but also systems metrics such as throughput, latency distribution, SLO satisfaction, and
   resource utilization, and it exposes standard interfaces so that alternative agents, scheduling
   algorithms, or middleware components can be plugged in and compared on a common testbed built on
   top of SAGE’s layered architecture and unified control plane.

   - **Agent capability evaluation**: tool selection accuracy, multi-step planning quality, timing
     decisions;

   - **Control-plane scheduling evaluation**: throughput under mixed workloads, latency distribution
     (p50/p95/p99), SLO satisfaction rates, multi-tenant interference;You can reduce the list to **3
     bullets** if space is tight, for example by merging contributions (3) and (4) into a single
     "end-to-end deployment & evaluation" point.

   - **Pluggable interfaces**: alternative scheduling policies, agent strategies, and middleware
     components can be evaluated on a common testbed.

   ## 2. Chinese Summary (for your own reference)

   Our benchmark reveals that \[specific insight, e.g., "naive FIFO scheduling degrades p99 latency
   by [A]x under bursty traffic, while SAGE's hybrid policy maintains [B]% SLO compliance"\].

- **分层架构 + declarative pipeline**：强调 6 层、无上行依赖、关注点分离与可维护性。

You can reduce the list to **3 bullets** if space is tight, for example by merging contributions (3)
and (4) into a single "end-to-end deployment & evaluation" point.- **统一控制平面**：LLM + Embedding
统一调度，混合请求分类、批处理、SLO，API 走 OpenAI 兼容 gateway。

- **异构集群与工程工具链**：CPU/GPU 混部、job/node 管理、C++ 中间件、统一安装与质量工具，突出“implementation & scalability”。

---- **系统化 benchmark**：既评估 agent 能力，也评估调度策略，关注 throughput/latency/SLO 等系统指标。

## 2. Quantitative Claims Checklist你可以根据最终实验结果，把“改善 tail latency / utilization”等字眼改成更具体的 quantitative 描述。

**每个贡献点都应有可量化的声明。实验完成后填入以下占位符：**

| Contribution      | Claim Template                                                                            | Experiment Needed                 |
| ----------------- | ----------------------------------------------------------------------------------------- | --------------------------------- |
| Architecture (1)  | "enables [X]% faster development iteration" OR "reduces configuration complexity by [Y]%" | Developer study or LOC comparison |
| Control Plane (2) | "reduces p99 latency by [X]% compared to vLLM+separate embedding"                         | Mixed workload latency benchmark  |
| Control Plane (2) | "improves throughput by [Y]x while maintaining p95 < [Z]ms"                               | Throughput saturation test        |
| Control Plane (2) | "achieves [A]% SLO satisfaction vs [B]% for baseline"                                     | SLO compliance under varied load  |
| Heterogeneous (3) | "supports CPU-only nodes with [X]% of GPU performance for embedding-heavy workloads"      | CPU vs GPU embedding benchmark    |
| Benchmark (4)     | "reveals [specific insight about scheduling/agent behavior]"                              | Comparative policy evaluation     |

______________________________________________________________________

## 3. Positioning vs. Existing Systems (for reviewer FAQs)

**Q: How does SAGE differ from vLLM?**

> vLLM is a single-model inference engine optimized for GPU memory management and continuous
> batching. SAGE uses vLLM as a backend engine and adds: (1) cross-engine load balancing, (2)
> embedding service co-scheduling, (3) declarative pipeline composition, (4) SLO-aware request
> routing.

**Q: How does SAGE differ from Ray Serve?**

> Ray Serve is a generic ML serving framework. SAGE provides LLM-specific scheduling (distinguishing
> chat vs. generation vs. embedding), workload-aware batching, and an OpenAI-compatible API that
> simplifies migration from cloud LLM APIs.

**Q: How does SAGE differ from LangChain?**

> LangChain is an application-level orchestration framework for prompt chaining and agent logic.
> SAGE operates at the systems level, providing the underlying resource management, scheduling, and
> execution infrastructure that LangChain-like frameworks could build upon.

**Q: Why is a unified LLM+embedding control plane needed?**

> Modern RAG and agent applications interleave embedding (for retrieval) and LLM (for generation)
> calls. Without unified scheduling, operators must manually balance two separate services, leading
> to resource fragmentation and suboptimal latency. SAGE's control plane treats them as a single
> resource pool with workload-aware policies.

______________________________________________________________________

## 4. Chinese Summary (for your own reference)

- **分层架构 + declarative pipeline**：强调 6 层、无上行依赖、关注点分离与可维护性。
- **统一控制平面**：LLM + Embedding 统一调度，混合请求分类、批处理、SLO，API 走 OpenAI 兼容
  gateway。**必须有量化指标**（p99延迟降低X%，吞吐提升Yx）。
- **异构集群与工程工具链**：CPU/GPU 混部、job/node 管理、C++ 中间件、统一安装与质量工具，突出"implementation & scalability"。
- **系统化 benchmark**：与 AgentBench/ToolBench/vLLM benchmark 的差异化——同时评估 agent 能力和系统调度性能，而非只关注其中一个维度。

你可以根据最终实验结果，把 `[X]%`, `[Y]x` 等占位符替换成实际数字。
