# SAGE Benchmark Pipelines

可复用的 Pipeline 定义，使用真实 SAGE 算子 + `RemoteEnvironment` + `HeadNodeScheduler`。

---

## Pipeline 拓扑结构

### Pipeline A: RAG Pipeline (检索增强生成)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Pipeline A: RAG Pipeline                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐    ┌───────────┐    ┌───────────┐    ┌──────────┐           │
│   │  Source  │───▶│ Embedding │───▶│ Retrieval │───▶│  Rerank  │           │
│   │ (Query)  │    │   [Map]   │    │   [Map]   │    │ [Filter] │           │
│   └──────────┘    └───────────┘    └───────────┘    └────┬─────┘           │
│        ↑                                                 │                  │
│   HEAD NODE                                              ▼                  │
│                    ┌───────────┐    ┌───────────┐                          │
│                    │   Sink    │◀───│    LLM    │                          │
│                    │ (Result)  │    │   [Map]   │                          │
│                    └───────────┘    └───────────┘                          │
│                         ↑                                                   │
│                    HEAD NODE                                                │
│                                                                             │
│   算子链: Source → Map(Embed) → Map(Retrieve) → Filter(Rerank)             │
│           → Map(LLM) → Sink                                                 │
│                                                                             │
│   数据集: QA, MMLU, BBH                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pipeline B: Long Context Refiner (长文本精炼)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Pipeline B: Long Context Refiner                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐          │
│   │  Source  │───▶│  Chunking │───▶│  Filter   │───▶│ Embedding │          │
│   │  (Doc)   │    │ [FlatMap] │    │(Relevance)│    │   [Map]   │          │
│   └──────────┘    └───────────┘    └───────────┘    └─────┬─────┘          │
│        ↑                                                  │                 │
│   HEAD NODE                                               ▼                 │
│                    ┌──────────┐                    ┌───────────┐            │
│                    │   Sink   │◀───────────────────│ Summarize │            │
│                    │ (Summary)│                    │   [Map]   │            │
│                    └──────────┘                    └───────────┘            │
│                         ↑                                                   │
│                    HEAD NODE                                                │
│                                                                             │
│   算子链: Source → FlatMap(Chunk) → Filter(Relevance) → Map(Embed)         │
│           → Map(Summarize) → Sink                                           │
│                                                                             │
│   数据集: LoCoMo                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pipeline C: Cross-Source Vector Stream Join (跨源向量流相似度 Join)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              Pipeline C: Cross-Source Vector Stream Join                    │
│                  (时间窗内跨源向量流近邻匹配)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌────────────────────────────────────────────────────────────────────┐   │
│   │                     MultiSourceFunction                             │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │   │
│   │  │ Source 1 │  │ Source 2 │  │ Source 3 │   ← HEAD NODE            │   │
│   │  │ (News)   │  │ (Social) │  │(Official)│                          │   │
│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘                          │   │
│   │       └─────────────┼─────────────┘                                │   │
│   └─────────────────────┼──────────────────────────────────────────────┘   │
│                         ▼                                                   │
│                  ┌───────────┐                                              │
│                  │ Embedding │                                              │
│                  │   [Map]   │                                              │
│                  └─────┬─────┘                                              │
│                        ▼                                                    │
│            ┌─────────────────────┐                                          │
│            │    Vector Join      │                                          │
│            │       [Map]         │                                          │
│            │  ┌───────────────┐  │                                          │
│            │  │ Time Window   │  │                                          │
│            │  │ + TopK Neighbor│  │                                          │
│            │  │ IVF/HNSW/Clust│  │                                          │
│            │  └───────────────┘  │                                          │
│            └──────────┬──────────┘                                          │
│                       ▼                                                     │
│              ┌───────────────┐                                              │
│              │   Conflict    │                                              │
│              │  Detection    │                                              │
│              │   [Filter]    │                                              │
│              └───────┬───────┘                                              │
│                      ▼                                                      │
│               ┌──────────┐                                                  │
│               │   Sink   │  ← HEAD NODE                                     │
│               │ (Result) │                                                  │
│               └──────────┘                                                  │
│                                                                             │
│   算子链: Source(Multi) → Map(Embed) → Map(VectorJoin) → Filter(Conflict)  │
│           → Sink                                                            │
│                                                                             │
│   Join 策略: IVF / HNSW / Clustered                                         │
│   数据集: MemAgentBench                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pipeline D: Batch Processing (批处理)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Pipeline D: Batch Processing                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐          │
│   │  Source  │───▶│  Batching │───▶│  Window   │───▶│ Batch LLM │          │
│   │ (Stream) │    │   [Map]   │    │   [Map]   │    │   [Map]   │          │
│   └──────────┘    └───────────┘    └───────────┘    └─────┬─────┘          │
│        ↑                                                  │                 │
│   HEAD NODE                                               ▼                 │
│                                                    ┌──────────┐             │
│                                                    │   Sink   │             │
│                                                    │ (Output) │             │
│                                                    └──────────┘             │
│                                                         ↑                   │
│                                                    HEAD NODE                │
│                                                                             │
│   算子链: Source → Map(Batch) → Map(Window) → Map(BatchLLM) → Sink         │
│                                                                             │
│   数据集: BBH, GPQA                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pipeline E: Priority Scheduling (优先级调度)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Pipeline E: Priority Scheduling                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────┐                                                              │
│   │  Source  │  ← HEAD NODE                                                 │
│   │(Requests)│                                                              │
│   └────┬─────┘                                                              │
│        │                                                                    │
│        │    ┌─────────────────────────────────────────────────────────┐    │
│        │    │              Request Distribution                       │    │
│        │    │   ┌───────┐    ┌───────┐    ┌───────┐                  │    │
│        └───▶│   │ High  │    │Medium │    │  Low  │                  │    │
│             │   │  20%  │    │  50%  │    │  30%  │                  │    │
│             │   │ SLO:  │    │ SLO:  │    │ SLO:  │                  │    │
│             │   │ 500ms │    │ 1000ms│    │ 5000ms│                  │    │
│             │   └───┬───┘    └───┬───┘    └───┬───┘                  │    │
│             │       └────────────┼────────────┘                       │    │
│             └────────────────────┼────────────────────────────────────┘    │
│                                  ▼                                          │
│                          ┌───────────────┐                                  │
│                          │   Scheduler   │                                  │
│                          │     [Map]     │                                  │
│                          │ ┌───────────┐ │                                  │
│                          │ │ FIFO      │ │                                  │
│                          │ │ Priority  │ │                                  │
│                          │ │ SLO-Aware │ │                                  │
│                          │ │ Hybrid    │ │                                  │
│                          │ └───────────┘ │                                  │
│                          └───────┬───────┘                                  │
│                                  ▼                                          │
│                          ┌───────────────┐                                  │
│                          │      LLM      │                                  │
│                          │     [Map]     │                                  │
│                          └───────┬───────┘                                  │
│                                  ▼                                          │
│                           ┌──────────┐                                      │
│                           │   Sink   │  ← HEAD NODE                         │
│                           │ (Result) │                                      │
│                           └──────────┘                                      │
│                                                                             │
│   算子链: Source → Map(Scheduler) → Map(LLM) → Sink                        │
│                                                                             │
│   调度策略: FIFO / Priority / SLO-Aware / Hybrid                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 算子覆盖矩阵

| 算子 | Pipeline A | Pipeline B | Pipeline C | Pipeline D | Pipeline E |
|------|:----------:|:----------:|:----------:|:----------:|:----------:|
| Source | ✅ | ✅ | ✅ (Multi) | ✅ | ✅ |
| Map | ✅×3 | ✅×2 | ✅×2 | ✅×3 | ✅×2 |
| FlatMap | | ✅ | | | |
| Filter | ✅ | ✅ | ✅ | | |
| VectorJoin | | | ✅ | | |
| Sink | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## HeadNodeScheduler

所有 Pipeline 使用 `HeadNodeScheduler` 确保 **Source 和 Sink 节点在 Head 节点执行**：

```python
from sage.benchmark.benchmark_sage.experiments.pipelines import (
    RAGPipeline,
    HeadNodeScheduler,
)

# 创建 Pipeline
pipeline = RAGPipeline(
    pipeline_id="rag_test",
    embedding_base_url="http://localhost:8090/v1",
    llm_base_url="http://localhost:8001/v1",
)

# 运行
result = pipeline.run()
```

**调度策略**：
- Source 节点 → 绑定到 Head Node（Ray node ID affinity）
- Sink 节点 → 绑定到 Head Node
- 其他算子 → Ray 默认负载均衡

---

## 文件结构

```
pipelines/
├── README.md                   # 本文档
├── __init__.py                 # 导出所有 Pipeline 类
├── scheduler.py                # HeadNodeScheduler 实现
├── pipeline_a_rag.py           # Pipeline A: RAG
├── pipeline_b_refiner.py       # Pipeline B: Long Context Refiner
├── pipeline_c_vector_join.py   # Pipeline C: Cross-Source Vector Join
├── pipeline_d_batch.py         # Pipeline D: Batch Processing
└── pipeline_e_scheduling.py    # Pipeline E: Priority Scheduling
```
