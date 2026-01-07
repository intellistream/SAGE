#!/usr/bin/env python3
"""
Adaptive-RAG 流分支 Pipeline 实现

这个版本展示如何使用 SAGE 的流分支模式 (Multi-Branch Pipeline) 来实现 Adaptive-RAG。
关键思想：对同一个分类后的流多次应用 filter，创建不同的分支，每个分支处理不同复杂度的查询。

流分支模式 (参考 SAGE 文档):
```
                    ┌─ filter(ZERO) ─> NoRetrievalMap ─> sink
    Source ─> Map ─┼─ filter(SINGLE) ─> SingleRetrievalMap ─> sink
                    └─ filter(MULTI) ─> IterativeRetrievalMap ─> sink
```

用法:
    from sage.kernel.api import LocalEnvironment
    from examples.tutorials.L5_apps.adaptive_rag.branch_pipeline import (
        build_branching_adaptive_rag_pipeline
    )

    env = LocalEnvironment("adaptive-rag-branch")
    build_branching_adaptive_rag_pipeline(env, queries=["What is AI?", "Compare X and Y"])
    env.submit(autostop=True)
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sage.common.core.functions import (
    FilterFunction,
    MapFunction,
    SinkFunction,
    SourceFunction,
)
from sage.kernel.api import LocalEnvironment

from .classifier import (
    ClassificationResult,
    QueryComplexityLevel,
    create_classifier,
)


# ============================================================================
# 数据结构
# ============================================================================


@dataclass
class QueryData:
    """查询数据"""
    query: str
    classification: ClassificationResult | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ResultData:
    """结果数据"""
    query: str
    answer: str
    strategy_used: str
    complexity: str
    retrieval_steps: int = 0
    processing_time_ms: float = 0.0


# ============================================================================
# Source: 查询数据源
# ============================================================================


class QuerySource(SourceFunction):
    """查询数据源"""

    def __init__(self, queries: list[str], delay: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.queries = queries
        self.delay = delay
        self.counter = 0

    def execute(self) -> QueryData | None:
        if self.counter >= len(self.queries):
            return None
        query = self.queries[self.counter]
        self.counter += 1
        if self.delay > 0:
            time.sleep(self.delay)
        print(f"📤 Source [{self.counter}/{len(self.queries)}]: {query[:50]}...")
        return QueryData(query=query, metadata={"index": self.counter - 1})


# ============================================================================
# Classifier MapFunction
# ============================================================================


class ClassifierMap(MapFunction):
    """分类器 - 对查询进行复杂度分类"""

    def __init__(self, classifier_type: str = "rule", **kwargs):
        super().__init__(**kwargs)
        self.classifier_type = classifier_type
        self._classifier = None

    def execute(self, data: QueryData) -> QueryData:
        if self._classifier is None:
            self._classifier = create_classifier(self.classifier_type)

        classification = self._classifier.classify(data.query)
        data.classification = classification

        print(f"🏷️ Classified: {data.query[:30]}... -> {classification.complexity.name}")
        return data


# ============================================================================
# Filter Functions: 按复杂度分支
# ============================================================================


class ZeroComplexityFilter(FilterFunction):
    """过滤: 只保留 ZERO (简单) 复杂度的查询"""

    def execute(self, data: QueryData) -> bool:
        if data.classification is None:
            return False
        is_match = data.classification.complexity == QueryComplexityLevel.ZERO
        if is_match:
            print(f"  ✅ ZERO branch: {data.query[:30]}...")
        return is_match


class SingleComplexityFilter(FilterFunction):
    """过滤: 只保留 SINGLE (中等) 复杂度的查询"""

    def execute(self, data: QueryData) -> bool:
        if data.classification is None:
            return False
        is_match = data.classification.complexity == QueryComplexityLevel.SINGLE
        if is_match:
            print(f"  ✅ SINGLE branch: {data.query[:30]}...")
        return is_match


class MultiComplexityFilter(FilterFunction):
    """过滤: 只保留 MULTI (复杂) 复杂度的查询"""

    def execute(self, data: QueryData) -> bool:
        if data.classification is None:
            return False
        is_match = data.classification.complexity == QueryComplexityLevel.MULTI
        if is_match:
            print(f"  ✅ MULTI branch: {data.query[:30]}...")
        return is_match


# ============================================================================
# Strategy MapFunctions: 各分支的处理逻辑
# ============================================================================


class NoRetrievalStrategy(MapFunction):
    """策略 A: 无检索 - 直接 LLM 生成"""

    def execute(self, data: QueryData) -> ResultData:
        start_time = time.time()

        # 模拟 LLM 直接回答
        answer = f"[Direct LLM Answer] {data.query[:50]}..."

        print(f"  🔵 NoRetrieval: {data.query[:30]}...")

        return ResultData(
            query=data.query,
            answer=answer,
            strategy_used="no_retrieval",
            complexity="ZERO",
            retrieval_steps=0,
            processing_time_ms=(time.time() - start_time) * 1000,
        )


class SingleRetrievalStrategy(MapFunction):
    """策略 B: 单次检索 + 生成"""

    def execute(self, data: QueryData) -> ResultData:
        start_time = time.time()

        # 模拟检索 + LLM
        answer = f"[Single Retrieval Answer] {data.query[:50]}..."

        print(f"  🟡 SingleRetrieval: {data.query[:30]}...")

        return ResultData(
            query=data.query,
            answer=answer,
            strategy_used="single_retrieval",
            complexity="SINGLE",
            retrieval_steps=1,
            processing_time_ms=(time.time() - start_time) * 1000,
        )


class IterativeRetrievalStrategy(MapFunction):
    """策略 C: 迭代检索 (IRCoT 风格)"""

    def execute(self, data: QueryData) -> ResultData:
        start_time = time.time()

        # 模拟多跳检索
        steps = 3
        answer = f"[Iterative Retrieval Answer - {steps} steps] {data.query[:50]}..."

        print(f"  🔴 IterativeRetrieval ({steps} steps): {data.query[:30]}...")

        return ResultData(
            query=data.query,
            answer=answer,
            strategy_used="iterative_retrieval",
            complexity="MULTI",
            retrieval_steps=steps,
            processing_time_ms=(time.time() - start_time) * 1000,
        )


# ============================================================================
# Sink: 结果收集器
# ============================================================================


class ResultSink(SinkFunction):
    """结果收集器"""

    _all_results: list[ResultData] = []

    def __init__(self, branch_name: str = "", **kwargs):
        super().__init__(**kwargs)
        self.branch_name = branch_name
        self.count = 0

    def execute(self, data: ResultData):
        self.count += 1
        ResultSink._all_results.append(data)

        print(
            f"\n🎯 [{self.branch_name}] Result #{self.count}:\n"
            f"   Query: {data.query[:50]}...\n"
            f"   Strategy: {data.strategy_used}\n"
            f"   Answer: {data.answer[:60]}..."
        )

        return data

    @classmethod
    def get_all_results(cls) -> list[ResultData]:
        return cls._all_results.copy()

    @classmethod
    def clear_results(cls):
        cls._all_results.clear()


# ============================================================================
# 流分支 Pipeline 构建函数
# ============================================================================


def build_branching_adaptive_rag_pipeline(
    env: LocalEnvironment,
    queries: list[str],
    classifier_type: str = "rule",
) -> LocalEnvironment:
    """
    构建流分支模式的 Adaptive-RAG Pipeline

    这是 SAGE 推荐的多分支模式：对同一个流多次应用 filter 创建不同分支。

    架构:
    ```
                          ┌─ filter(ZERO) ─> NoRetrieval ─> sink(ZERO)
    Source ─> Classifier ─┼─ filter(SINGLE) ─> SingleRetrieval ─> sink(SINGLE)
                          └─ filter(MULTI) ─> IterativeRetrieval ─> sink(MULTI)
    ```

    Args:
        env: SAGE LocalEnvironment
        queries: 查询列表
        classifier_type: 分类器类型

    Returns:
        配置好的 Environment
    """
    ResultSink.clear_results()

    # Step 1: 创建 Source 和 Classifier（共享的上游）
    classified_stream = (
        env.from_source(QuerySource, queries=queries, delay=0.1)
        .map(ClassifierMap, classifier_type=classifier_type)
    )

    # Step 2: 分支 A - ZERO 复杂度 (无检索)
    (
        classified_stream
        .filter(ZeroComplexityFilter)
        .map(NoRetrievalStrategy)
        .sink(ResultSink, branch_name="ZERO", parallelism=1)
    )

    # Step 3: 分支 B - SINGLE 复杂度 (单次检索)
    (
        classified_stream
        .filter(SingleComplexityFilter)
        .map(SingleRetrievalStrategy)
        .sink(ResultSink, branch_name="SINGLE", parallelism=1)
    )

    # Step 4: 分支 C - MULTI 复杂度 (迭代检索)
    (
        classified_stream
        .filter(MultiComplexityFilter)
        .map(IterativeRetrievalStrategy)
        .sink(ResultSink, branch_name="MULTI", parallelism=1)
    )

    return env


# ============================================================================
# 主函数 - 演示
# ============================================================================


def main():
    """演示流分支 Adaptive-RAG Pipeline"""
    print("=" * 70)
    print("Adaptive-RAG 流分支 Pipeline 演示")
    print("=" * 70)

    queries = [
        "What is machine learning?",  # ZERO
        "What are the key features of Python 3.12?",  # 可能 ZERO 或 SINGLE
        "Compare Japan and Germany economic policies during 2008 crisis and their long-term effects on GDP",  # MULTI
        "Define artificial intelligence",  # ZERO
        "How does BERT work for NLP tasks?",  # SINGLE
    ]

    print(f"\n📋 Processing {len(queries)} queries:")
    for i, q in enumerate(queries, 1):
        print(f"   {i}. {q[:60]}...")

    print("\n" + "-" * 70)
    print("🚀 Building Multi-Branch Pipeline...")
    print("-" * 70 + "\n")

    env = LocalEnvironment("adaptive-rag-branch")

    build_branching_adaptive_rag_pipeline(env, queries=queries)

    print("Pipeline structure:")
    print("  Source -> Classifier -+-> filter(ZERO) -> NoRetrieval -> Sink")
    print("                        +-> filter(SINGLE) -> SingleRetrieval -> Sink")
    print("                        +-> filter(MULTI) -> IterativeRetrieval -> Sink")
    print()

    try:
        env.submit(autostop=True)
        time.sleep(3)
    finally:
        env.close()

    results = ResultSink.get_all_results()

    print("\n" + "=" * 70)
    print(f"📊 Summary: Processed {len(results)} queries")
    print("=" * 70)

    strategy_counts = {}
    for r in results:
        strategy_counts[r.strategy_used] = strategy_counts.get(r.strategy_used, 0) + 1

    for strategy, count in strategy_counts.items():
        print(f"   - {strategy}: {count} queries")

    print("\n✅ Multi-Branch Pipeline completed.")


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "QueryData",
    "ResultData",
    "QuerySource",
    "ClassifierMap",
    "ZeroComplexityFilter",
    "SingleComplexityFilter",
    "MultiComplexityFilter",
    "NoRetrievalStrategy",
    "SingleRetrievalStrategy",
    "IterativeRetrievalStrategy",
    "ResultSink",
    "build_branching_adaptive_rag_pipeline",
]


if __name__ == "__main__":
    main()
