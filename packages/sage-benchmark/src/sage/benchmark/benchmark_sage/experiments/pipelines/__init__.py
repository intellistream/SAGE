"""
可复用 Pipeline 模块
====================

包含 5 个可复用的 Pipeline 实现 (A-E)，供各实验引用。

Pipeline 定义:
- Pipeline A: RAG (检索增强生成)
- Pipeline B: Long Context Refiner (长文本精炼)
- Pipeline C: Cross-Source Vector Stream Join (跨源向量流相似度 Join)
- Pipeline D: Batch Processing (批处理)
- Pipeline E: Priority Scheduling (优先级调度)
- Adaptive-RAG: 自适应 RAG Pipeline (基于问题复杂度动态选择策略)

所有 Pipeline 使用:
- 真实 SAGE 算子 (MapFunction, FilterFunction, SinkFunction 等)
- RemoteEnvironment 远程执行
- HeadNodeScheduler 限制 Source/Sink 在 head 节点
"""

from .scheduler import HeadNodeScheduler
from .pipeline_a_rag import RAGPipeline
from .pipeline_b_refiner import RefinerPipeline
from .pipeline_c_vector_join import VectorJoinPipeline
from .pipeline_d_batch import BatchPipeline
from .pipeline_e_scheduling import SchedulingPipeline

# Adaptive-RAG Pipeline
from .adaptive_rag import (
    # Core
    AdaptiveRAGPipeline,
    QueryComplexityClassifier,
    QueryComplexityLevel,
    # Strategy Functions
    NoRetrievalFunction,
    SingleRetrieverFunction,
    IterativeRetrieverFunction,
    AdaptiveRouterFunction,
    # SAGE Dataflow Components - Router Mode
    QueryData,
    ResultData,
    QuerySource,
    ClassifierMapFunction,
    AdaptiveRouterMapFunction,
    ComplexityFilterFunction,
    ResultSink,
    build_adaptive_rag_pipeline,
    # SAGE Dataflow Components - Multi-Branch Mode
    ZeroComplexityFilter,
    SingleComplexityFilter,
    MultiComplexityFilter,
    NoRetrievalStrategy,
    SingleRetrievalStrategy,
    IterativeRetrievalStrategy,
    build_branching_adaptive_rag_pipeline,
)

__all__ = [
    "HeadNodeScheduler",
    "RAGPipeline",
    "RefinerPipeline",
    "VectorJoinPipeline",
    "BatchPipeline",
    "SchedulingPipeline",
    # Adaptive-RAG
    "AdaptiveRAGPipeline",
    "QueryComplexityClassifier",
    "QueryComplexityLevel",
    "NoRetrievalFunction",
    "SingleRetrieverFunction",
    "IterativeRetrieverFunction",
    "AdaptiveRouterFunction",
    "QueryData",
    "ResultData",
    "QuerySource",
    "ClassifierMapFunction",
    "AdaptiveRouterMapFunction",
    "ComplexityFilterFunction",
    "ResultSink",
    "build_adaptive_rag_pipeline",
    "ZeroComplexityFilter",
    "SingleComplexityFilter",
    "MultiComplexityFilter",
    "NoRetrievalStrategy",
    "SingleRetrievalStrategy",
    "IterativeRetrievalStrategy",
    "build_branching_adaptive_rag_pipeline",
]
