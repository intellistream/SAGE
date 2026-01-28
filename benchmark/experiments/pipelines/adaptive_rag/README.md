# Adaptive-RAG: 基于 SAGE 算子的自适应 RAG Pipeline

基于论文 ["Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity"](https://arxiv.org/abs/2403.14403) (NAACL 2024) 的 SAGE 实现。

## 概述

Adaptive-RAG 是一种自适应的问答框架，能够根据问题复杂度动态选择最合适的 RAG 策略：

```
┌─────────────────────────────────────────────────────────────────┐
│                         Query Input                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  Query Complexity     │
                │     Classifier        │
                │  (T5/LLM/Rule-based)  │
                └───────────┬───────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Level A      │   │  Level B      │   │  Level C      │
│  No Retrieval │   │  Single-hop   │   │  Multi-hop    │
│  (LLM Only)   │   │  Retrieval    │   │  (IRCoT)      │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │    Final Answer       │
                └───────────────────────┘
```

## 复杂度等级

| Level | 名称 | 策略 | 适用场景 |
|-------|------|------|----------|
| A | ZERO | 无检索，LLM 直接回答 | 定义类、常识类简单问题 |
| B | SINGLE | 单步检索 + LLM | 需要事实支撑的一般问题 |
| C | MULTI | 多跳迭代检索 (IRCoT) | 多实体比较、复杂推理问题 |

## 快速开始

### 基本用法

```python
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import (
    AdaptiveRAGPipeline,
    QueryComplexityClassifier,
)

# 1. 创建 Pipeline
pipeline = AdaptiveRAGPipeline()

# 2. 处理查询
result = pipeline.run("What is the relationship between AI and machine learning?")

print(f"策略: {result.strategy}")
print(f"答案: {result.answer}")
print(f"分类: {result.metadata['classification']}")
```

### 使用分类器

```python
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import (
    QueryComplexityClassifier,
    QueryComplexityLevel,
)

classifier = QueryComplexityClassifier()

# 简单问题
result = classifier.classify("What is Python?")
assert result.complexity == QueryComplexityLevel.ZERO

# 复杂问题
result = classifier.classify("Compare the economic policies of Obama and Trump")
assert result.complexity == QueryComplexityLevel.MULTI
```

### 配置 Pipeline

```python
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import (
    AdaptiveRAGPipeline,
)
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag.pipeline import PipelineConfig

config = PipelineConfig(
    # 分类器配置
    classifier_type="rule",  # "rule", "llm", "t5"
    classifier_config={"multi_hop_threshold": 2},
    
    # 检索器配置
    retriever_type="chroma",
    retriever_config={"collection": "my_docs", "top_k": 5},
    
    # LLM 配置
    llm_model="gpt-4",
)

pipeline = AdaptiveRAGPipeline(
    config=config,
    llm_client=my_llm_client,
    retriever=my_retriever,
)
```

### 与 SAGE 数据流集成 (推荐方式)

Adaptive-RAG 完全支持 SAGE 的原生数据流 API (`env.from_source().map().sink()`)：

```python
from sage.kernel.api import LocalEnvironment
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import (
    QuerySource,
    ClassifierMapFunction,
    AdaptiveRouterMapFunction,
    ResultSink,
)

# 创建执行环境
env = LocalEnvironment("adaptive-rag")

# 构建完整的 SAGE 数据流 Pipeline
(
    env.from_source(QuerySource, queries=[
        "What is AI?",
        "Compare Python and Java",
        "Explain WWI causes and effects",
    ], delay=0.1)
    .map(ClassifierMapFunction, classifier_type="rule")
    .map(AdaptiveRouterMapFunction)
    .sink(ResultSink, verbose=True, parallelism=1)
)

# 执行
env.submit(autostop=True)

# 获取结果
results = ResultSink.get_all_results()
for r in results:
    print(f"Query: {r.query}")
    print(f"Strategy: {r.strategy_used}")
    print(f"Answer: {r.answer[:100]}...")
```

#### 使用 Filter 按复杂度筛选

```python
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import ComplexityFilterFunction

# 只处理复杂查询 (Level C)
(
    env.from_source(QuerySource, queries=queries)
    .map(ClassifierMapFunction)
    .filter(ComplexityFilterFunction, target_levels=["C_MULTI_HOP"])
    .map(AdaptiveRouterMapFunction)
    .sink(ResultSink)
)
```

#### 使用构建辅助函数

```python
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import build_adaptive_rag_pipeline

env = LocalEnvironment("adaptive-rag")
build_adaptive_rag_pipeline(
    env,
    queries=["What is AI?", "Compare X and Y"],
    classifier_type="rule",
    verbose=True,
)
env.submit(autostop=True)
```

### SAGE 数据流组件一览

| 组件 | 类型 | 说明 |
|------|------|------|
| `QuerySource` | SourceFunction | 查询数据源 |
| `ClassifierMapFunction` | MapFunction | 复杂度分类器 |
| `AdaptiveRouterMapFunction` | MapFunction | 自适应策略路由器 |
| `ComplexityFilterFunction` | FilterFunction | 按复杂度过滤 |
| `StrategyBranchFlatMap` | FlatMapFunction | 策略分支分发 |
| `ResultSink` | SinkFunction | 结果收集器 |

### 流分支模式 (Multi-Branch Pipeline)

除了 Router 模式（在单个 MapFunction 内部使用 if-else），SAGE 还支持**流分支模式**：对同一数据流应用多个 `filter()` 创建独立分支。

```
Source -> Classifier -+-> filter(ZERO) -> NoRetrieval -> Sink
                      +-> filter(SINGLE) -> SingleRetrieval -> Sink
                      +-> filter(MULTI) -> IterativeRetrieval -> Sink
```

这种模式的优势：
- **真正的流级分支**：不同复杂度在不同的算子链中并行处理
- **更清晰的 DAG 结构**：每个策略有独立的处理路径
- **更好的可观测性**：可以独立监控每个分支的性能

```python
from sage.kernel.api import LocalEnvironment
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import (
    QuerySource,
    ClassifierMapFunction,
    ZeroComplexityFilter,
    SingleComplexityFilter,
    MultiComplexityFilter,
    NoRetrievalStrategy,
    SingleRetrievalStrategy,
    IterativeRetrievalStrategy,
    ResultSink,
)

env = LocalEnvironment("adaptive-rag-branch")

# 共享上游：Source -> Classifier
classified_stream = (
    env.from_source(QuerySource, queries=queries, delay=0.1)
    .map(ClassifierMapFunction, classifier_type="rule")
)

# 分支 A: ZERO 复杂度 -> 无检索策略
(
    classified_stream
    .filter(ZeroComplexityFilter)
    .map(NoRetrievalStrategy)
    .sink(ResultSink, branch_name="ZERO", parallelism=1)
)

# 分支 B: SINGLE 复杂度 -> 单步检索策略
(
    classified_stream
    .filter(SingleComplexityFilter)
    .map(SingleRetrievalStrategy)
    .sink(ResultSink, branch_name="SINGLE", parallelism=1)
)

# 分支 C: MULTI 复杂度 -> 多跳检索策略
(
    classified_stream
    .filter(MultiComplexityFilter)
    .map(IterativeRetrievalStrategy)
    .sink(ResultSink, branch_name="MULTI", parallelism=1)
)

env.submit(autostop=True)
```

#### 两种模式对比

| 特性 | Router 模式 | 流分支模式 |
|------|-------------|-----------|
| 分支方式 | if-else 在 MapFunction 内部 | 多个 filter() 创建独立分支 |
| DAG 结构 | 单链 | 多分支 |
| 并行度 | 策略共享并行度 | 各分支独立并行度 |
| 代码复杂度 | 较简单 | 较复杂但更清晰 |
| 适用场景 | 简单路由 | 需要独立监控/扩展的场景 |

### 旧版集成方式

```python
from sage.kernel import StreamExecutionEnvironment
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import build_sage_pipeline

env = StreamExecutionEnvironment.get_execution_environment()

# 定义数据源
queries = env.from_collection([
    "What is AI?",
    "Compare Python and Java",
    "Explain WWI causes and effects",
])

# 使用 Adaptive-RAG
results = build_sage_pipeline(env, queries)

# 添加 Sink
results.print()

# 执行
env.execute("adaptive-rag")
```

## 模块结构

```
adaptive_rag/
├── __init__.py                  # 包入口 (导出所有组件)
├── classifier.py                # 问题复杂度分类器
│   ├── QueryComplexityLevel     # 复杂度枚举 (A/B/C)
│   ├── ClassificationResult     # 分类结果
│   ├── RuleBasedClassifier      # 规则分类器
│   ├── LLMClassifier            # LLM 分类器
│   └── T5Classifier             # T5 分类器
├── functions.py                 # RAG 策略函数 (封装版)
│   ├── NoRetrievalFunction      # 无检索策略
│   ├── SingleRetrieverFunction  # 单步检索策略
│   ├── IterativeRetrieverFunction  # 多跳策略
│   └── AdaptiveRouterFunction   # 自适应路由
├── sage_dataflow_pipeline.py    # ⭐ SAGE 数据流 API 实现 (Router 模式)
│   ├── QuerySource              # SourceFunction - 查询数据源
│   ├── ClassifierMapFunction    # MapFunction - 分类器
│   ├── AdaptiveRouterMapFunction # MapFunction - 路由器 (if-else 分支)
│   ├── ComplexityFilterFunction # FilterFunction - 过滤器
│   ├── ResultSink               # SinkFunction - 结果收集
│   └── build_adaptive_rag_pipeline  # 构建辅助函数
├── branch_pipeline.py           # ⭐ SAGE 流分支实现 (Multi-Branch 模式)
│   ├── ZeroComplexityFilter     # FilterFunction - ZERO 分支过滤
│   ├── SingleComplexityFilter   # FilterFunction - SINGLE 分支过滤
│   ├── MultiComplexityFilter    # FilterFunction - MULTI 分支过滤
│   ├── NoRetrievalStrategy      # MapFunction - 无检索策略
│   ├── SingleRetrievalStrategy  # MapFunction - 单步检索策略
│   ├── IterativeRetrievalStrategy # MapFunction - 多跳检索策略
│   └── build_branching_adaptive_rag_pipeline  # 流分支构建函数
├── test_branch_pipeline.py      # 流分支测试脚本
├── pipeline.py                  # Pipeline 封装类
│   ├── PipelineConfig           # 配置类
│   ├── AdaptiveRAGPipeline      # 主 Pipeline
│   └── build_sage_pipeline      # 旧版 SAGE 集成
├── example.py                   # 使用示例
└── README.md                    # 本文档
```

## 分类器类型

### 1. RuleBasedClassifier (默认)

基于关键词和启发式规则的分类器，无需额外依赖：

```python
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag.classifier import create_classifier

classifier = create_classifier("rule", config={
    "multi_hop_threshold": 2,     # 多跳特征阈值
    "entity_count_threshold": 3,  # 实体数量阈值
})
```

### 2. LLMClassifier

使用 LLM 进行零样本分类：

```python
classifier = create_classifier("llm", 
    llm_client=my_llm,
    model="gpt-3.5-turbo",
)
```

### 3. T5Classifier

使用微调后的 T5 模型（论文原始方法）：

```python
classifier = create_classifier("t5",
    model_path="path/to/finetuned/model",
    device="cuda",
)
```

## 策略函数

所有策略函数继承自 SAGE 的 `MapFunction`，可直接用于数据流：

### NoRetrievalFunction

```python
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import NoRetrievalFunction

no_ret = NoRetrievalFunction(llm_client=llm)
result = no_ret.execute("What is machine learning?")
# result.strategy == "no_retrieval"
# result.retrieved_docs == []
```

### SingleRetrieverFunction

```python
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import SingleRetrieverFunction

single_ret = SingleRetrieverFunction(
    llm_client=llm,
    retriever=retriever,
    top_k=5,
)
result = single_ret.execute("What are the symptoms of COVID-19?")
# result.retrieved_docs contains 5 documents
```

### IterativeRetrieverFunction

基于 IRCoT (Interleaving Retrieval with Chain-of-Thought) 的多跳检索：

```python
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import IterativeRetrieverFunction

iter_ret = IterativeRetrieverFunction(
    llm_client=llm,
    retriever=retriever,
    max_iterations=3,
    top_k_per_step=3,
)
result = iter_ret.execute("Compare X and Y, and explain their relationship")
# result.reasoning_chain contains step-by-step reasoning
```

## 指标和可观测性

Pipeline 内置指标收集：

```python
pipeline = AdaptiveRAGPipeline()

# 处理查询
for query in queries:
    pipeline.run(query)

# 获取指标
metrics = pipeline.get_metrics()
print(f"总查询数: {metrics['total_queries']}")
print(f"分类分布: {metrics['classification_distribution']}")
print(f"平均延迟: {metrics['avg_latency_ms']} ms")
print(f"错误率: {metrics['error_rate']}%")

# 重置指标
pipeline.reset_metrics()
```

## 与原论文的对应关系

| 论文概念 | SAGE 实现 |
|----------|-----------|
| Query Complexity Classifier | `QueryComplexityClassifier`, `T5Classifier` |
| No Retrieval (NOR) | `NoRetrievalFunction` |
| Single-hop Retrieval (ONER) | `SingleRetrieverFunction` |
| IRCoT (Multi-hop) | `IterativeRetrieverFunction` |
| Adaptive Pipeline | `AdaptiveRAGPipeline` |
| Silver/Binary Labels | 可通过 `T5Classifier` 加载训练好的模型 |

## 运行示例

```bash
# 运行完整示例
python -m sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag.example

# 或者在 Python 中交互式运行
python -c "from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import AdaptiveRAGPipeline; print('OK')"
```

## 扩展和自定义

### 自定义分类器

```python
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag.classifier import (
    BaseClassifier,
    ClassificationResult,
    QueryComplexityLevel,
)

class MyClassifier(BaseClassifier):
    def classify(self, query: str) -> ClassificationResult:
        # 自定义分类逻辑
        complexity = QueryComplexityLevel.SINGLE
        return ClassificationResult(
            query=query,
            complexity=complexity,
            confidence=0.9,
            reasoning="Custom logic",
        )
```

### 自定义策略函数

```python
from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag.functions import (
    BaseRAGStrategyFunction, RAGOutput
)

class MyStrategy(BaseRAGStrategyFunction):
    strategy_name = "my_custom_strategy"
    
    def execute(self, data):
        query = self._extract_query(data)
        # 自定义处理逻辑
        return RAGOutput(
            query=query,
            answer="Custom answer",
            strategy=self.strategy_name,
        )
```

## 参考文献

```bibtex
@inproceedings{jeong2024adaptiverag,
  author    = {Soyeong Jeong and Jinheon Baek and Sukmin Cho and 
               Sung Ju Hwang and Jong Park},
  title     = {Adaptive-RAG: Learning to Adapt Retrieval-Augmented 
               Large Language Models through Question Complexity},
  booktitle = {NAACL},
  year      = {2024},
  url       = {https://arxiv.org/abs/2403.14403}
}
```

## License

Apache-2.0 (与 SAGE 项目一致)
