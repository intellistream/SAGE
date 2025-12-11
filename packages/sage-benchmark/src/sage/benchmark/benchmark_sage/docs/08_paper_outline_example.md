# SAGE Systems Paper – ICML-Style Outline

下面是基于当前 prompts 跑出的一版 **完整 ICML 风格 SAGE 论文草稿结构**，只包含章节标题与每节 2–3 句英文说明，默认面向顶级 Machine Learning
Systems track（例如 ICML）。

______________________________________________________________________

## 1 Introduction

Introduces the rise of complex LLM/AI applications that compose retrieval, tools, and multiple
models over heterogeneous CPU/GPU clusters, and argues that existing serving and MLOps systems lack
unified support for such pipelines. States the goals and design principles of SAGE as a
dataflow-based ML system, positions it between low-level LLM serving engines and high-level
application frameworks, and outlines the main challenges (scalability, heterogeneity,
programmability, reproducibility). Summarizes the paper’s contributions as a numbered list covering
the layered architecture, declarative dataflow, unified LLM+embedding control plane, heterogeneous
deployment support, and benchmark suite.

## 2 Related Work

Reviews prior work across several categories: LLM serving engines (e.g., vLLM, TensorRT-LLM),
generic serving and workflow frameworks (e.g., Ray Serve, KServe, MLflow, Kubeflow), LLM application
frameworks (e.g., LangChain, LlamaIndex, DSPy), and LLM benchmarks (e.g., AgentBench, ToolBench,
HELM). For each category, explains what systems properties they target and why they are insufficient
as end-to-end platforms for LLM+embedding dataflow pipelines. Concludes by positioning SAGE as a
unified system that complements these efforts by providing layered architecture, declarative
dataflow, a control plane, and system-level benchmarks.

## 3 System Overview and Design Goals

Provides a high-level view of the SAGE system, introducing its role as a Python-based framework for
LLM/AI data processing pipelines built on a strict six-layer architecture. Describes the main design
goals—scalability, support for heterogeneous CPU/GPU environments, programmability via declarative
dataflow, observability, and reproducibility—and how they shape the system’s interfaces and
components. Walks through the lifecycle of a typical SAGE pipeline from user specification
(CLI/Studio/examples) to deployment and execution on a cluster.

## 4 Layered Architecture

Details the responsibilities of each layer from `sage-common` and `sage-platform` through
`sage-kernel`/`sage-libs`, `sage-middleware`, `sage-apps`/`sage-benchmark`, up to `sage-cli`,
`sage-studio`, `sage-tools`, and `sage-gateway`. Explains the “no upward dependencies” constraint
and how it enables modularity, testing, independent evolution of layers, and reuse of lower layers
across tools, applications, and benchmarks. Compares this disciplined layering with ad-hoc scripting
or flat microservice deployments commonly seen in LLM systems.

## 5 Declarative Dataflow and Execution Model

Introduces SAGE’s declarative dataflow abstraction for specifying LLM/AI pipelines (e.g., retrieval,
tools, LLM calls, post-processing) and contrasts it with imperative orchestration code. Describes
how the platform and kernel layers compile dataflow graphs into executable tasks, handling batching,
parallelism, and placement over heterogeneous CPU/GPU nodes. Discusses how this execution model
improves maintainability and performance, and how middleware operators are used for
performance-critical stages.

## 6 LLM & Embedding Control Plane (sageLLM)

Presents the design goals of the sageLLM control plane: unified scheduling of LLM and embedding
workloads, improved throughput and tail latency, and SLO-aware resource management across multiple
backends. Describes the architecture, including the `UnifiedInferenceClient`, request
classification, scheduling policies such as `HybridSchedulingPolicy`, embedding executors, and their
integration with `sage-gateway` and vLLM instances. Clarifies SAGE’s relationship to vLLM and
similar engines, emphasizing that SAGE builds a cross-engine, cross-workload control plane and API
layer on top of them rather than replacing their single-model schedulers.

## 7 Implementation Details and Deployment

Summarizes key implementation choices: Python 3.10+, C++ middleware with CMake builds, internal
directory layout, and the use of XDG-compliant user paths for configuration, logs, models, and
caches. Describes installation and tooling (e.g., `quickstart.sh`, `manage.sh`, `sage-dev`, CI
configuration) that enable reproducible builds, testing, and code quality enforcement. Explains how
SAGE supports CPU-only and GPU deployments in practice, including configuration of ports via
`SagePorts`, cluster configuration files, and operational practices for monitoring and debugging.

## 8 Experiments

Outlines the experimental methodology and setup: hardware and software environment, models,
workloads (end-to-end pipelines, mixed LLM+embedding traffic, heterogeneous deployments), and
measurement procedures following reproducibility best practices. States the main experimental
questions: end-to-end pipeline performance vs. baselines, effectiveness of the unified control plane
and scheduling policies, scalability with backends and load, benefits of heterogeneous deployments,
and insights from agent and system benchmarks. Previews the structure of the section, with
subsections on: (8.1) End-to-End Pipeline Performance, (8.2) Control Plane Effectiveness, (8.3)
Scheduling Policy Comparison, (8.4) Scalability, (8.5) Heterogeneous Hardware & CPU-only Support,
and (8.6) Agent Capability & Benchmarking (if claimed).

## 9 Discussion

Reflects on the practical implications of deploying SAGE in real-world environments, including
trade-offs between flexibility and complexity, and lessons learned from building and operating a
multi-layer ML system. Discusses limitations such as dependency on underlying serving engines,
potential bottlenecks in the control plane, and scenarios where simpler solutions may suffice.
Outlines promising directions for future extensions, such as richer dataflow optimizations, tighter
integration with external data systems, or additional scheduling policies.

## 10 Conclusion

Recaps the motivation for SAGE and the key design elements: layered architecture, declarative
dataflow, unified LLM+embedding control plane, heterogeneous deployment support, and benchmark
suite. Summarizes the main experimental findings in terms of performance, scalability, SLO
satisfaction, and insights into agent and scheduling behavior. Emphasizes SAGE’s role as a reusable
platform and testbed for future research on LLM-centric systems and invites the community to build
on its architecture and benchmarks.
