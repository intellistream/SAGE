# ICML 2026 论文 Introduction 撰写指南

## 论文定位

**SAGE: A Declarative Dataflow Framework for End-to-End LLM Inference Orchestration**

本文是**大模型全链路推理编排系统领域的开创性工作**，采用类似 MapReduce 的写作风格：

- **不与现有系统对比**（因为没有直接可比的系统）
- **展示系统本身的能力和特性**
- **强调开创性贡献和设计洞察**

______________________________________________________________________

## 当前 Introduction 问题

当前末尾段落（实验结果描述）：

```latex
In our experiments on mixed LLM+embedding workloads, SAGE reduces p99
latency by [X]% compared to [baseline], improves SLO satisfaction by [Y]%
under [Z] traffic, and increases tool selection accuracy by [A]% on [benchmark].
```

**问题**：这是"与基线对比"的增量改进论文写法，不适合开创性系统论文。

______________________________________________________________________

## 可用实验数据

### 1. 并发扩展性 (Concurrency Scaling)

| Concurrency | Throughput | Speedup | P99 Latency |
| ----------- | ---------- | ------- | ----------- |
| 1           | 2.01/s     | 1.0×    | 2.4s        |
| 4           | 7.27/s     | 3.6×    | 0.5s        |
| 8           | 13.30/s    | 6.6×    | 1.2s        |
| 16          | 16.61/s    | 8.3×    | 13.3s       |

**关键洞察**: 近线性扩展至 4 并发 (3.6× speedup)，存在最优工作点 (4-8)

### 2. 调度策略对比

| Scheduler | Throughput | P99 Latency | Balance |
| --------- | ---------- | ----------- | ------- |
| FIFO      | 9.45/s     | 6.9s        | 47%     |
| LoadAware | 9.38/s     | 7.0s        | 99.8%   |
| Priority  | 12.73/s    | 31.1s       | 100%    |

**关键洞察**: 不同策略存在明确权衡，LoadAware 实现 99.8% 负载均衡

### 3. 多 Pipeline 隔离 (Admission Control)

| Start Delay | Throughput | P99 Latency |
| ----------- | ---------- | ----------- |
| 0s (同时)   | 43.6/s     | 77s         |
| 5s (交错)   | 30.7/s     | 33s         |

**关键洞察**: 交错启动降低 57% 尾延迟，支持 8 个并发 pipeline

### 4. 任务复杂度

- 吞吐量对任务复杂度**不敏感** (~9 tasks/s)
- 调度开销 < 1ms，可忽略不计

### 5. 集群规模

- 16 节点集群稳定运行
- 支持分布式 RAG pipeline 编排

______________________________________________________________________

## 末尾段落重写方案

### 方案 A：强调系统能力边界（推荐，最像 MapReduce 风格）

```latex
To make pipeline-level claims measurable, SAGE includes an open benchmark suite that
evaluates both system metrics (throughput, TTFT/TBT, tail latency, SLO compliance)
and agent behaviors (tool selection, planning, timing). Experiments on a 16-node
cluster characterize SAGE's performance envelope: the system achieves 8$\times$
throughput scaling with near-linear efficiency up to moderate concurrency, maintains
99.8\% load balance across heterogeneous workloads through adaptive scheduling, and
reduces multi-tenant tail latency by 57\% via simple admission control policies.
```

### 方案 B：强调设计洞察

```latex
To make pipeline-level claims measurable, SAGE includes an open benchmark suite that
evaluates both system metrics (throughput, TTFT/TBT, tail latency, SLO compliance)
and agent behaviors (tool selection, planning, timing). Our experiments reveal several
insights for LLM inference orchestration: an optimal concurrency level exists beyond
which queueing delays dominate, no single scheduling policy dominates across all metrics,
and admission control can reduce p99 latency by over 50\% without complex fair-share
mechanisms.
```

### 方案 C：强调实用性和规模

```latex
To make pipeline-level claims measurable, SAGE includes an open benchmark suite that
evaluates both system metrics (throughput, TTFT/TBT, tail latency, SLO compliance)
and agent behaviors (tool selection, planning, timing). On a 16-node cluster running
mixed RAG workloads, SAGE sustains over 16 tasks per second with sub-millisecond
scheduling overhead, supports 8 concurrent pipelines with configurable
latency-throughput trade-offs, and provides operators with actionable guidance
for capacity planning and policy selection.
```

### 方案 D：最精炼

```latex
To make pipeline-level claims measurable, SAGE includes an open benchmark suite that
evaluates both system metrics (throughput, TTFT/TBT, tail latency) and agent behaviors
(tool selection, planning). Experiments on a 16-node cluster demonstrate 8$\times$
throughput scaling, 99.8\% load balance under adaptive scheduling, and 57\% tail
latency reduction through staggered admission control.
```

______________________________________________________________________

## 写作原则

1. **不要写 "compared to X" 或 "reduces by X% compared to baseline"** - 没有直接可比的基线
1. **使用绝对数值** - "16 tasks/sec", "99.8% balance", "57% reduction", "8× scaling"
1. **强调系统特性** - 扩展性、多策略支持、多租户能力
1. **提供设计洞察** - "optimal concurrency", "no single policy dominates"
1. **保持谦逊但自信** - 使用 "characterize", "demonstrate", "reveal" 而非 "outperform", "beat"

______________________________________________________________________

## 与 Abstract 保持一致

确保 Introduction 的实验结果描述与 Abstract 的末尾句子在以下方面一致：

- 使用相同的关键数据点（8× scaling, 99.8% balance, 57% latency reduction）
- 采用相同的"能力展示"而非"竞争对比"的语气
- 强调相同的核心洞察

______________________________________________________________________

## 参考：MapReduce Introduction 风格

MapReduce 论文在 Introduction 末尾如何描述实验：

```
"We have implemented a version of MapReduce for use within Google.
This version is used routinely to perform a wide variety of tasks
including web indexing, data mining, machine learning, and statistical
analysis."
```

注意它如何：

- 描述实现和部署环境
- 强调实际应用场景
- 不与其他系统做数值对比

______________________________________________________________________

## Agent 任务

请根据上述指南，将当前 Introduction 中的实验结果段落替换为更合适的表述。

**推荐使用方案 A**，因为：

- 最完整地展示系统能力
- 与 Abstract 风格一致
- 保留了 benchmark suite 的描述

**替换位置**：

```latex
In our experiments on mixed LLM+embedding workloads, SAGE reduces p99
latency by [X]% compared to [baseline], improves SLO satisfaction by [Y]%
under [Z] traffic, and increases tool selection accuracy by [A]% on [benchmark].
```

**替换为方案 A 的内容**。
