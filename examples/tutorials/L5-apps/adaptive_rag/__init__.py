"""
Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models
through Question Complexity

基于 SAGE 算子系统实现的 Adaptive-RAG Pipeline。

参考论文: "Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models
through Question Complexity" (NAACL 2024)
https://arxiv.org/abs/2403.14403

核心思想:
- 根据问题复杂度动态选择最适合的 RAG 策略
- 三种策略: No Retrieval (A), Single-hop Retrieval (B), Multi-hop Retrieval (C)
- 使用小型分类器预测问题复杂度，选择最优策略

两种 SAGE 实现模式:

1. **Router 模式** (sage_dataflow_pipeline.py):
   单一 MapFunction 内部通过 if-else 选择策略
   ```
   Source -> Classifier -> Router(if-else) -> Sink
   ```

2. **流分支模式** (branch_pipeline.py) - 推荐:
   使用 SAGE 的 Multi-Branch Pipeline 模式，对同一流多次 filter 创建分支
   ```
   Source -> Classifier -+-> filter(ZERO) -> NoRetrieval -> Sink
                         +-> filter(SINGLE) -> SingleRetrieval -> Sink
                         +-> filter(MULTI) -> IterativeRetrieval -> Sink
   ```

用法示例（流分支模式）:

    from sage.kernel.api import LocalEnvironment
    from examples.tutorials.L5_apps.adaptive_rag.branch_pipeline import (
        build_branching_adaptive_rag_pipeline
    )

    env = LocalEnvironment("adaptive-rag")
    build_branching_adaptive_rag_pipeline(env, queries=["What is AI?", "Compare X and Y"])
    env.submit(autostop=True)
"""

from .classifier import QueryComplexityClassifier, QueryComplexityLevel
from .functions import (
    AdaptiveRouterFunction,
    IterativeRetrieverFunction,
    NoRetrievalFunction,
    SingleRetrieverFunction,
)
from .pipeline import AdaptiveRAGPipeline

# SAGE 数据流 API 组件 - Router 模式
from .sage_dataflow_pipeline import (
    # 数据结构
    QueryData,
    ResultData,
    # Source
    QuerySource,
    # Map Functions
    ClassifierMapFunction,
    AdaptiveRouterMapFunction,
    # Filter
    ComplexityFilterFunction,
    # Sink
    ResultSink,
    # 构建函数
    build_adaptive_rag_pipeline,
)

# SAGE 数据流 API 组件 - 流分支模式
from .branch_pipeline import (
    # Filters
    ZeroComplexityFilter,
    SingleComplexityFilter,
    MultiComplexityFilter,
    # Strategy Functions
    NoRetrievalStrategy,
    SingleRetrievalStrategy,
    IterativeRetrievalStrategy,
    # 构建函数
    build_branching_adaptive_rag_pipeline,
)

__all__ = [
    # 核心分类器
    "QueryComplexityClassifier",
    "QueryComplexityLevel",
    # 策略函数 (原始封装)
    "NoRetrievalFunction",
    "SingleRetrieverFunction",
    "IterativeRetrieverFunction",
    "AdaptiveRouterFunction",
    # Pipeline (原始封装)
    "AdaptiveRAGPipeline",
    # ============ SAGE 数据流 API - Router 模式 ============
    # 数据结构
    "QueryData",
    "ResultData",
    # Source
    "QuerySource",
    # Map Functions
    "ClassifierMapFunction",
    "AdaptiveRouterMapFunction",
    # Filter
    "ComplexityFilterFunction",
    # Sink
    "ResultSink",
    # 构建函数
    "build_adaptive_rag_pipeline",
    # ============ SAGE 数据流 API - 流分支模式 ============
    # Filters
    "ZeroComplexityFilter",
    "SingleComplexityFilter",
    "MultiComplexityFilter",
    # Strategy Functions
    "NoRetrievalStrategy",
    "SingleRetrievalStrategy",
    "IterativeRetrievalStrategy",
    # 构建函数
    "build_branching_adaptive_rag_pipeline",
]

