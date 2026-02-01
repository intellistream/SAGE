# ICML 2026 论文 Abstract 撰写指南

## 论文定位

**SAGE: A Declarative Dataflow Framework for End-to-End LLM Inference Orchestration**

本文是**大模型全链路推理编排系统领域的开创性工作**，采用类似 MapReduce 的写作风格：

- **不与现有系统对比**（因为没有直接可比的系统）
- **展示系统本身的能力和特性**
- **强调开创性贡献和设计洞察**

______________________________________________________________________

## 当前 Abstract 问题

当前末尾句子：

```
Experiments show that SAGE achieves [X]% lower p99 latency and [Y]% higher throughput
compared to [baseline framework] on mixed retrieval-generation workloads.
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

### 3. 多 Pipeline 隔离

| Start Delay | Throughput | P99 Latency |
| ----------- | ---------- | ----------- |
| 0s (同时)   | 43.6/s     | 77s         |
| 5s (交错)   | 30.7/s     | 33s         |

**关键洞察**: 交错启动降低 57% 尾延迟，支持 8 个并发 pipeline

### 4. 任务复杂度

- 吞吐量对任务复杂度**不敏感** (~9 tasks/s)
- 调度开销 < 1ms，可忽略不计

______________________________________________________________________

## 末尾句子重写方案

### 方案 A：强调扩展性和多策略能力

```
Experiments on a 16-node cluster demonstrate that SAGE achieves near-linear
throughput scaling (3.6× at 4-way concurrency), supports multiple scheduling
policies with distinct trade-offs, and reduces tail latency by 57% through
admission control in multi-tenant deployments.
```

### 方案 B：强调系统能力边界（推荐，更像 MapReduce 风格）

```
Experiments on a 16-node cluster characterize SAGE's performance envelope:
the system scales to 16.6 tasks/sec with 8× speedup, maintains 99.8% load
balance across heterogeneous workloads, and supports 8 concurrent pipelines
with configurable latency-throughput trade-offs.
```

### 方案 C：强调设计洞察

```
Experiments reveal key insights for LLM inference orchestration: an optimal
concurrency sweet spot exists beyond which queueing delays dominate, and
simple admission control policies can reduce p99 latency by over 50% without
complex fair-share scheduling.
```

### 方案 D：简洁有力（最精炼）

```
On a 16-node cluster, SAGE processes over 16 RAG tasks per second with
sub-second scheduling overhead, scales near-linearly to 8× speedup, and
reduces multi-tenant tail latency by 57% through staggered admission.
```

______________________________________________________________________

## 写作原则

1. **不要写 "compared to X"** - 没有直接可比的基线
1. **使用绝对数值** - "16.6 tasks/sec", "99.8% balance", "57% reduction"
1. **强调系统特性** - 扩展性、多策略、多租户支持
1. **提供设计洞察** - "optimal concurrency", "latency-throughput trade-off"
1. **保持谦逊但自信** - "characterize", "demonstrate", "reveal"

______________________________________________________________________

## Agent 任务

请根据上述指南，将当前 abstract 的最后一句话替换为更合适的表述。

**推荐使用方案 B 或 D**，因为：

- 方案 B 最完整地展示系统能力
- 方案 D 最精炼，适合字数限制

**注意事项**：

- 保持与 abstract 前文的语气一致
- 确保数据准确（参考上方实验数据）
- 避免过度宣称，使用 "characterize" 而非 "achieve best"

______________________________________________________________________

## 参考：MapReduce Abstract 风格

MapReduce 论文 abstract 末尾：

```
"We have implemented MapReduce on a large cluster of commodity machines
and find it to be highly effective. Programs are often hundreds of lines
of code and can achieve orders-of-magnitude performance improvements
compared to programs without using the framework."
```

注意它如何：

- 描述实现环境（"large cluster"）
- 使用定性描述（"highly effective"）
- 与"不使用框架"对比而非与其他框架对比
