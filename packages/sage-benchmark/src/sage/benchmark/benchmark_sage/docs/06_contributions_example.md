# SAGE – Example Contributions List (Systems Track)

本文件提供一份面向顶级 **Machine Learning Systems** track 的示例 "Contributions" 列表草案，你可以直接在 Introduction
末尾或单独小节中使用/修改。 重点是把 **整个 SAGE 系统** 的贡献讲清楚：分层架构、数据流、控制平面、异构部署、benchmark。

______________________________________________________________________

## 1. Example Contributions (English Draft)

Below is an example contributions list tailored to SAGE as a **machine learning system** rather than
a pure algorithm or application.

1. **A layered architecture for declarative LLM/AI pipelines.**

   We introduce SAGE, a framework that organizes LLM/AI data processing pipelines into a strict
   six-layer architecture, from foundational utilities (`sage-common`) and platform services
   (`sage-platform`), through kernel and middleware components (`sage-kernel`, `sage-libs`,
   `sage-middleware`), up to applications and user-facing tools (`sage-apps`, `sage-benchmark`,
   `sage-cli`, `sage-studio`, `sage-tools`, `sage-gateway`). By enforcing **no upward
   dependencies**, SAGE cleanly separates concerns between configuration, scheduling, execution, and
   user interfaces, enabling independent evolution of layers, easier testing, and simplified
   large-scale system maintenance.

1. **A unified control plane for LLM and embedding workloads.**

   We design and implement a **sageLLM control plane** that jointly manages LLM and embedding
   workloads across a shared pool of engines. The control plane classifies requests (chat/generation
   vs. embeddings), applies hybrid scheduling and batching policies (e.g.,
   `HybridSchedulingPolicy`), and exposes an OpenAI-compatible API via `sage-gateway` on
   standardized ports from `SagePorts`. This unified design improves resource utilization and
   **reduces tail latency** for mixed LLM+embedding traffic compared to siloed vLLM + separate
   embedding setups, while preserving a familiar client-facing interface.

1. **Systems support for heterogeneous CPU/GPU deployments with reproducible tooling.**

   SAGE provides kernel-level mechanisms for **CPU-only and GPU nodes**, job management
   (`sage-kernel/runtime`), and node selection (`sage-kernel/scheduler`), along with platform
   services (`sage-platform`) for storage, queuing, and service management, and C++ operators in
   `sage-middleware` for performance-critical paths. Together with reproducible installation and
   quality pipelines (`quickstart.sh`, `manage.sh`, `sage-dev`, pre-commit tooling), the system
   lowers the barrier to deploying complex LLM pipelines on heterogeneous clusters and makes
   end-to-end experiments repeatable for both developers and researchers.

1. **A comprehensive benchmark suite and reusable testbed for LLM-centric systems.**

   To evaluate the system, we provide `sage-benchmark`, which instantiates a range of workloads for
   **agent behavior** (tool selection, multi-step planning, timing decisions) and **control-plane
   scheduling** under diverse traffic patterns, as well as additional suites targeting **retrieval,
   memory, DB/TSDB components, and scheduler behavior** in LLM-centric pipelines. The suite reports
   not only task- or model-level accuracy but also systems metrics such as throughput, latency
   distribution, SLO satisfaction, and resource utilization, and it exposes standard interfaces so
   that alternative agents, scheduling algorithms, or middleware components can be plugged in and
   compared on a common testbed built on top of SAGE’s layered architecture and unified control
   plane.

If space is tight, you may merge (3) and (4) into a single contribution on **end-to-end deployment
and evaluation**.

______________________________________________________________________

## 2. Quantitative Claims Checklist

Each contribution should have at least one **quantitative** claim. After experiments are complete,
fill in the placeholders below:

| Contribution      | Claim Template                                                                            | Experiment Needed                               |
| ----------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Architecture (1)  | "enables [X]% faster development iteration" OR "reduces configuration complexity by [Y]%" | Developer study or configuration/LOC comparison |
| Control Plane (2) | "reduces p99 latency by [X]% compared to vLLM + separate embedding"                       | Mixed LLM+embedding workload latency benchmark  |
| Control Plane (2) | "improves throughput by [Y]× while maintaining p95 < [Z] ms"                              | Throughput vs. latency saturation study         |
| Control Plane (2) | "achieves [A]% SLO satisfaction vs. [B]% for baseline"                                    | SLO compliance under varied load                |
| Heterogeneous (3) | "supports CPU-only nodes with [X]% of GPU performance for embedding-heavy workloads"      | CPU vs. GPU embedding / pipeline benchmark      |
| Benchmark (4)     | "reveals \[specific insight, e.g., FIFO degrades p99 by [C]× vs. hybrid policy"           | Comparative scheduling/agent evaluation         |

这些模板可以帮助你在写论文时，系统性地把实验结果映射到贡献点。

______________________________________________________________________

## 3. Positioning vs. Existing Systems (for reviewer FAQs)

You can also prepare short Q&A snippets for reviewers:

**Q: How does SAGE differ from vLLM?**

> vLLM is a single-model inference engine optimized for GPU memory management and continuous
> batching. SAGE uses vLLM as a backend engine and adds: (1) cross-engine load balancing, (2)
> embedding service co-scheduling, (3) declarative pipeline composition, (4) SLO-aware request
> routing, and (5) system-level benchmarks.

**Q: How does SAGE differ from Ray Serve or KServe?**

> Ray Serve and KServe are generic ML serving frameworks. SAGE provides LLM-specific scheduling
> (distinguishing chat vs. generation vs. embedding), workload-aware batching, declarative dataflow
> for pipelines, and an OpenAI-compatible API that simplifies migration from cloud LLM APIs, plus
> benchmarks that focus on LLM-centric systems behavior.

**Q: How does SAGE differ from LangChain / LlamaIndex?**

> LangChain and LlamaIndex are application-level orchestration frameworks for prompt chaining and
> agent logic. SAGE operates at the systems level, providing the underlying resource management,
> scheduling, execution, and benchmarking infrastructure that LangChain-like frameworks could build
> upon.

**Q: Why is a unified LLM+embedding control plane needed?**

> Modern RAG and agent applications interleave embedding (for retrieval) and LLM (for generation)
> calls. Without unified scheduling, operators must manually balance multiple services, leading to
> resource fragmentation and suboptimal latency. SAGE’s control plane treats them as a single
> resource pool with workload-aware policies, integrated into a broader dataflow and benchmarking
> framework.

______________________________________________________________________

## 4. Chinese Summary（供自己校对用）

- **分层架构 + declarative pipeline**：强调 6 层、无上行依赖、关注点分离与可维护性。
- **统一控制平面**：LLM + Embedding 统一调度，混合请求分类、批处理、SLO，API 走 OpenAI 兼容 gateway。
- **异构集群与工程工具链**：CPU/GPU 混部、job/node 管理、C++ 中间件、统一安装与质量工具，突出 "implementation & scalability"。
- **系统化 benchmark**：既评估 agent 能力，也评估调度策略和 pipeline 行为，关注 throughput/latency/SLO 等系统指标。

你可以根据最终实验结果，把 `[X]%`, `[Y]×` 等占位符替换成实际数字。
