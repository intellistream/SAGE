```
                                                                                                                                   # SAGE Benchmark Pipelines
```

可复用的 Pipeline 定义，使用真实 SAGE 算子 + `RemoteEnvironment` + `HeadNodeScheduler`。

______________________________________________________________________

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

______________________________________________________________________

## 算子覆盖矩阵

| 算子类型          | Pipeline A | Pipeline B | Pipeline C | Pipeline D | Pipeline E | Pipeline F |
| ----------------- | :--------: | :--------: | :--------: | :--------: | :--------: | :--------: |
| SourceFunction    |     ✅     |     ✅     | ✅ (Multi) |     ✅     |     ✅     |     ✅     |
| MapFunction       |    ✅×4    |    ✅×3    |    ✅×3    |    ✅×3    |    ✅×2    |     ✅     |
| FilterFunction    |     ✅     |     ✅     |     ✅     |            |            |     ✅     |
| FlatMapFunction   |            |     ✅     |            |            |            |     ✅     |
| SinkFunction      |     ✅     |     ✅     |     ✅     |     ✅     |     ✅     |     ✅     |
| KeyByFunction     |            |            |            |            |            |     ✅     |
| BatchFunction     |            |            |            |            |            |     ✅     |
| BaseJoinFunction  |            |            |            |            |            |     ✅     |
| BaseCoMapFunction |            |            |            |            |            |     ✅     |

### Pipeline F: SAGE Operators Demo

Pipeline F 是一个算子库演示模块，展示了 SAGE 中所有主要算子类型的正确用法：

```python
from sage.benchmark.benchmark_sage.experiments.pipelines import (
    OPERATOR_SUMMARY,
    demo_basic_pipeline,
    demo_flatmap_pipeline,
    demo_keyby_pipeline,
)

# 查看算子总览
print(OPERATOR_SUMMARY)

# 运行演示
demo_basic_pipeline()
```

______________________________________________________________________

## SAGE 算子类型规范

### FilterFunction 正确用法

**关键点**: `FilterFunction.execute()` 必须返回 `bool`，不能修改数据。

```python
from sage.common.core import FilterFunction

# ✅ 正确: 返回 bool
class CorrectFilter(FilterFunction):
    def execute(self, data: dict) -> bool:
        return data.get("score", 0) > 0.5

# ❌ 错误: 返回修改后的数据 (旧版本错误)
class WrongFilter(FilterFunction):
    def execute(self, data: dict) -> Optional[dict]:  # 错误的返回类型
        if data.get("score", 0) > 0.5:
            data["filtered"] = True
            return data  # 错误: 不应该返回修改后的数据
        return None
```

如果需要同时过滤和转换数据，应该使用 **Map + Filter** 组合:

```python
# 正确的模式: Map(转换) + Filter(过滤)
stream.map(ScoreEnrichmentMap).filter(ScoreThresholdFilter)
```

### FlatMapFunction 正确用法

**两种方式**:

```python
from sage.common.core import FlatMapFunction

class ReturnIterableStyle(FlatMapFunction):
    """方式 1: 返回 Iterable"""
    def execute(self, text: str) -> list[str]:
        return text.split()

class CollectStyle(FlatMapFunction):
    """方式 2: 使用 self.collect()"""
    def execute(self, text: str) -> Iterable[str]:
        for word in text.split():
            self.collect(word)
        return []  # 返回空列表，数据已通过 collect() 发射
```

______________________________________________________________________

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

______________________________________________________________________

## 文件结构

```
pipelines/
├── README.md                       # 本文档
├── __init__.py                     # 导出所有 Pipeline 类
├── scheduler.py                    # HeadNodeScheduler 实现
├── pipeline_a_rag.py               # Pipeline A: RAG
├── pipeline_b_refiner.py           # Pipeline B: Long Context Refiner
├── pipeline_c_vector_join.py       # Pipeline C: Cross-Source Vector Join
├── pipeline_d_batch.py             # Pipeline D: Batch Processing
├── pipeline_e_scheduling.py        # Pipeline E: Priority Scheduling
├── pipeline_f_operators_demo.py    # Pipeline F: 算子库演示
└── adaptive_rag/                   # Adaptive-RAG 子模块
    ├── __init__.py
    ├── classifier.py               # 查询复杂度分类器
    ├── functions.py                # RAG 策略函数
    ├── pipeline.py                 # Adaptive-RAG Pipeline
    ├── branch_pipeline.py          # 多分支 Pipeline
    └── sage_dataflow_pipeline.py   # SAGE Dataflow 实现
```
