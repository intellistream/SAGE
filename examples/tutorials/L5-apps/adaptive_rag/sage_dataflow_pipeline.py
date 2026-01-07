#!/usr/bin/env python3
"""
Adaptive-RAG SAGE 数据流 Pipeline 实现

这是一个完整的 SAGE 数据流 API 实现，使用:
- env.from_source(SourceFunction) - 数据源
- .map(MapFunction) - 转换算子
- .filter(FilterFunction) - 过滤算子
- .flatmap(FlatMapFunction) - 一对多映射
- .sink(SinkFunction) - 数据汇

参考论文: Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models
         through Question Complexity (NAACL 2024)

用法示例:
    from sage.kernel.api import LocalEnvironment
    from examples.tutorials.L5-apps.adaptive_rag.sage_dataflow_pipeline import (
        QuerySource, ClassifierMapFunction, AdaptiveRouterMapFunction, ResultSink
    )

    env = LocalEnvironment("adaptive-rag")

    # 构建完整的 Adaptive-RAG Pipeline
    (
        env.from_source(QuerySource, queries=["What is AI?", "Compare X and Y"])
        .map(ClassifierMapFunction)
        .map(AdaptiveRouterMapFunction)
        .sink(ResultSink, parallelism=1)
    )

    env.submit(autostop=True)
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ============================================================================
# SAGE 核心导入
# ============================================================================

from sage.common.core.functions import (
    FilterFunction,
    FlatMapFunction,
    MapFunction,
    SinkFunction,
    SourceFunction,
)
from sage.kernel.api import LocalEnvironment

# 本地分类器导入
from .classifier import (
    ClassificationResult,
    QueryComplexityLevel,
    create_classifier,
)


# ============================================================================
# 数据结构定义
# ============================================================================


@dataclass
class QueryData:
    """查询数据 - 在 Pipeline 中流转的数据结构"""

    query: str
    classification: ClassificationResult | None = None
    context: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "query": self.query,
            "classification": {
                "complexity": self.classification.complexity.value,
                "confidence": self.classification.confidence,
            } if self.classification else None,
            "context": self.context,
            "metadata": self.metadata,
        }

    @classmethod
    def from_string(cls, query: str) -> QueryData:
        """从字符串创建"""
        return cls(query=query, metadata={"created_at": time.time()})


@dataclass
class ResultData:
    """结果数据 - Pipeline 输出的数据结构"""

    query: str
    answer: str
    strategy_used: str = ""
    classification: ClassificationResult | None = None
    retrieval_steps: int = 0
    retrieved_docs: list[str] = field(default_factory=list)
    reasoning_chain: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "query": self.query,
            "answer": self.answer,
            "strategy_used": self.strategy_used,
            "classification": {
                "complexity": self.classification.complexity.value,
                "confidence": self.classification.confidence,
            } if self.classification else None,
            "retrieval_steps": self.retrieval_steps,
            "retrieved_docs": self.retrieved_docs,
            "reasoning_chain": self.reasoning_chain,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata,
        }


# ============================================================================
# SourceFunction: 查询数据源
# ============================================================================


class QuerySource(SourceFunction):
    """
    查询数据源 - SAGE SourceFunction 实现

    用法:
        env.from_source(QuerySource, queries=["What is AI?", "Compare X and Y"])
        env.from_source(QuerySource, queries=query_list, delay=0.1)
    """

    def __init__(
        self,
        queries: list[str] | None = None,
        delay: float = 0.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.queries = queries or []
        self.delay = delay
        self.counter = 0
        self.total = len(self.queries)

    def execute(self) -> QueryData | None:
        """生成下一个查询数据"""
        if self.counter >= self.total:
            return None  # 信号结束

        query = self.queries[self.counter]
        self.counter += 1

        if self.delay > 0:
            time.sleep(self.delay)

        self.logger.info(f"QuerySource: emitted [{self.counter}/{self.total}]: {query[:50]}...")
        print(f"📤 QuerySource [{self.counter}/{self.total}]: {query[:50]}...")

        return QueryData.from_string(query)


# ============================================================================
# MapFunction: 分类器
# ============================================================================


class ClassifierMapFunction(MapFunction):
    """
    分类器 MapFunction - 对查询进行复杂度分类

    输入: QueryData
    输出: QueryData (带有 classification 字段)

    用法:
        stream.map(ClassifierMapFunction)
        stream.map(ClassifierMapFunction, classifier_type="llm", llm_client=client)
    """

    def __init__(
        self,
        classifier_type: str = "rule",
        llm_client: Any = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.classifier_type = classifier_type
        self.llm_client = llm_client
        self._classifier = None

    def setup(self):
        """初始化分类器"""
        self._classifier = create_classifier(self.classifier_type, llm_client=self.llm_client)
        self.logger.info(f"ClassifierMapFunction: initialized with {self.classifier_type} classifier")

    def execute(self, data: QueryData) -> QueryData:
        """对查询进行分类"""
        if self._classifier is None:
            self.setup()

        classification = self._classifier.classify(data.query)
        data.classification = classification

        complexity_name = classification.complexity.name if classification else "UNKNOWN"
        self.logger.info(f"ClassifierMapFunction: classified -> {complexity_name}")
        print(f"🏷️ Classified: {data.query[:30]}... -> {complexity_name}")

        return data

        return data


# ============================================================================
# MapFunction: 自适应路由器 (核心组件)
# ============================================================================


class AdaptiveRouterMapFunction(MapFunction):
    """
    自适应路由器 MapFunction - 根据分类结果选择并执行对应 RAG 策略

    这是 Adaptive-RAG 的核心组件，实现了动态策略选择:
    - Level A (NO_RETRIEVAL): 直接 LLM 生成
    - Level B (SINGLE_HOP): 单次检索 + 生成
    - Level C (MULTI_HOP): 迭代检索 (IRCoT 风格)

    输入: QueryData (带有 classification)
    输出: ResultData

    用法:
        stream.map(AdaptiveRouterMapFunction)
        stream.map(AdaptiveRouterMapFunction, llm_client=client, retriever=retriever)
    """

    def __init__(
        self,
        llm_client: Any = None,
        retriever: Any = None,
        max_iterations: int = 5,
        top_k: int = 5,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_client = llm_client
        self.retriever = retriever
        self.max_iterations = max_iterations
        self.top_k = top_k

    def setup(self):
        """延迟初始化 LLM 和 Retriever"""
        if self.llm_client is None:
            try:
                from sage.common.components.sage_llm import UnifiedInferenceClient
                self.llm_client = UnifiedInferenceClient.create()
            except Exception:
                self.llm_client = MockLLMClient()
                self.logger.warning("Using MockLLMClient - no real LLM available")

        if self.retriever is None:
            self.retriever = MockRetriever()
            self.logger.warning("Using MockRetriever - no real retriever available")

    def execute(self, data: QueryData) -> ResultData:
        """根据分类结果路由到对应策略并执行"""
        start_time = time.time()

        if self.llm_client is None:
            self.setup()

        # 确定复杂度级别 (使用 complexity 属性, 枚举值为 ZERO/SINGLE/MULTI)
        if data.classification is None:
            complexity = QueryComplexityLevel.SINGLE
        else:
            complexity = data.classification.complexity

        # 根据复杂度选择策略并执行
        if complexity == QueryComplexityLevel.ZERO:
            result = self._execute_no_retrieval(data)
        elif complexity == QueryComplexityLevel.MULTI:
            result = self._execute_iterative_retrieval(data)
        else:  # SINGLE (default)
            result = self._execute_single_retrieval(data)

        # 计算处理时间
        result.processing_time_ms = (time.time() - start_time) * 1000

        self.logger.info(
            f"AdaptiveRouter: {data.query[:30]}... -> {result.strategy_used} "
            f"({result.processing_time_ms:.1f}ms)"
        )
        print(
            f"🔀 Routed: {data.query[:30]}... -> {result.strategy_used} "
            f"({result.retrieval_steps} retrieval steps)"
        )

        return result

    def _generate(self, prompt: str) -> str:
        """调用 LLM 生成"""
        try:
            response = self.llm_client.chat(prompt)
            return response if isinstance(response, str) else str(response)
        except Exception as e:
            return f"[Error: {e}]"

    def _retrieve(self, query: str, top_k: int | None = None) -> list[str]:
        """检索相关文档"""
        k = top_k or self.top_k
        try:
            docs = self.retriever.retrieve(query, top_k=k)
            if isinstance(docs, list):
                return [str(d.get("content", d)) if isinstance(d, dict) else str(d) for d in docs]
            return [str(docs)]
        except Exception as e:
            return [f"[Retrieval Error: {e}]"]

    def _execute_no_retrieval(self, data: QueryData) -> ResultData:
        """策略 A: 无检索直接生成"""
        prompt = f"""请直接回答以下问题（无需检索外部知识）：

问题: {data.query}

回答:"""

        answer = self._generate(prompt)

        return ResultData(
            query=data.query,
            answer=answer,
            strategy_used="no_retrieval",
            classification=data.classification,
            retrieval_steps=0,
            retrieved_docs=[],
            reasoning_chain=["Direct LLM generation without retrieval"],
            metadata=data.metadata,
        )

    def _execute_single_retrieval(self, data: QueryData) -> ResultData:
        """策略 B: 单次检索 + 生成"""
        # Step 1: 检索
        retrieved_docs = self._retrieve(data.query)

        # Step 2: 构建上下文
        context = "\n\n".join([f"[Doc {i+1}]: {doc}" for i, doc in enumerate(retrieved_docs)])

        prompt = f"""基于以下检索到的文档回答问题：

{context}

问题: {data.query}

回答:"""

        answer = self._generate(prompt)

        return ResultData(
            query=data.query,
            answer=answer,
            strategy_used="single_retrieval",
            classification=data.classification,
            retrieval_steps=1,
            retrieved_docs=retrieved_docs,
            reasoning_chain=["Retrieved documents", "Generated answer with context"],
            metadata=data.metadata,
        )

    def _execute_iterative_retrieval(self, data: QueryData) -> ResultData:
        """策略 C: 迭代检索 (IRCoT 风格)"""
        reasoning_chain = []
        all_retrieved_docs = []

        # Step 1: 分解问题
        decompose_prompt = f"""将以下复杂问题分解为可以逐步回答的子问题：

问题: {data.query}

请列出子问题（每行一个）:"""

        sub_questions_text = self._generate(decompose_prompt)
        sub_questions = [q.strip() for q in sub_questions_text.split("\n") if q.strip()]
        reasoning_chain.append(f"Decomposed into {len(sub_questions)} sub-questions")

        # Step 2: 迭代检索和思考
        intermediate_answers = []

        for i, sub_q in enumerate(sub_questions[: self.max_iterations]):
            # 检索
            docs = self._retrieve(sub_q, top_k=3)
            all_retrieved_docs.extend(docs)

            # 回答子问题
            context = "\n".join(docs)
            think_prompt = f"""基于以下信息回答子问题：

上下文: {context}

子问题: {sub_q}

回答:"""

            sub_answer = self._generate(think_prompt)
            intermediate_answers.append(f"Q{i+1}: {sub_q}\nA{i+1}: {sub_answer}")
            reasoning_chain.append(f"Step {i+1}: Answered '{sub_q[:30]}...'")

        # Step 3: 综合
        synthesis_prompt = f"""基于以下子问题的回答，综合回答原始问题：

原始问题: {data.query}

子问题回答:
{chr(10).join(intermediate_answers)}

综合回答:"""

        final_answer = self._generate(synthesis_prompt)
        reasoning_chain.append("Synthesized final answer")

        return ResultData(
            query=data.query,
            answer=final_answer,
            strategy_used="iterative_retrieval",
            classification=data.classification,
            retrieval_steps=len(sub_questions[: self.max_iterations]),
            retrieved_docs=all_retrieved_docs,
            reasoning_chain=reasoning_chain,
            metadata=data.metadata,
        )


# ============================================================================
# FilterFunction: 按复杂度过滤
# ============================================================================


class ComplexityFilterFunction(FilterFunction):
    """
    按复杂度级别过滤查询

    用法:
        stream.filter(ComplexityFilterFunction, target_levels=["MULTI"])
        stream.filter(ComplexityFilterFunction, target_levels=["ZERO", "SINGLE"])
    """

    def __init__(
        self,
        target_levels: list[str] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if target_levels is None:
            self.target_levels = set(QueryComplexityLevel)
        else:
            # 支持字符串和枚举两种方式
            self.target_levels = set()
            for lvl in target_levels:
                if isinstance(lvl, str):
                    try:
                        self.target_levels.add(QueryComplexityLevel[lvl])
                    except KeyError:
                        # 尝试从 value 解析
                        self.target_levels.add(QueryComplexityLevel.from_label(lvl))
                else:
                    self.target_levels.add(lvl)

    def execute(self, data: QueryData) -> bool:
        """判断是否保留该查询"""
        if data.classification is None:
            return True

        is_match = data.classification.complexity in self.target_levels
        complexity_name = data.classification.complexity.name

        if is_match:
            print(f"✅ Filter: accepted {complexity_name}")
        else:
            print(f"❌ Filter: rejected {complexity_name}")

        return is_match


# ============================================================================
# SinkFunction: 结果收集器
# ============================================================================


class ResultSink(SinkFunction):
    """
    结果收集器 - SAGE SinkFunction 实现

    用法:
        stream.sink(ResultSink)
        stream.sink(ResultSink, output_file="/path/to/results.jsonl", verbose=True)
    """

    # 类级别结果存储（用于验证）
    _all_results: list[ResultData] = []

    def __init__(
        self,
        output_file: str | None = None,
        verbose: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.verbose = verbose
        self.received_count = 0

        if output_file is None:
            self.output_file = Path(tempfile.gettempdir()) / "adaptive_rag_results.jsonl"
        else:
            self.output_file = Path(output_file)

    def execute(self, data: ResultData):
        """接收并存储结果"""
        self.received_count += 1
        ResultSink._all_results.append(data)

        if self.verbose:
            print(
                f"\n🎯 Result #{self.received_count}:\n"
                f"   Query: {data.query[:60]}...\n"
                f"   Strategy: {data.strategy_used}\n"
                f"   Steps: {data.retrieval_steps}\n"
                f"   Answer: {data.answer[:100]}...\n"
                f"   Time: {data.processing_time_ms:.1f}ms"
            )

        # 追加写入文件
        try:
            with open(self.output_file, "a") as f:
                f.write(json.dumps(data.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"Write error: {e}")

        return data

    @classmethod
    def get_all_results(cls) -> list[ResultData]:
        """获取所有结果"""
        return cls._all_results.copy()

    @classmethod
    def clear_results(cls):
        """清空结果"""
        cls._all_results.clear()


# ============================================================================
# FlatMapFunction: 策略分支（高级用法）
# ============================================================================


class StrategyBranchFlatMap(FlatMapFunction):
    """
    策略分支 FlatMap - 将查询分发到不同策略标签

    用法:
        stream.flatmap(StrategyBranchFlatMap)
    """

    def execute(self, data: QueryData) -> list[dict]:
        """将查询标记并分发"""
        complexity = data.classification.complexity if data.classification else QueryComplexityLevel.SINGLE

        strategy_map = {
            QueryComplexityLevel.ZERO: "no_retrieval",
            QueryComplexityLevel.SINGLE: "single_retrieval",
            QueryComplexityLevel.MULTI: "iterative_retrieval",
        }

        return [
            {
                "tag": "routed_query",
                "strategy": strategy_map.get(complexity, "single_retrieval"),
                "data": data,
            }
        ]


# ============================================================================
# Mock 实现（用于无真实服务时的测试）
# ============================================================================


class MockLLMClient:
    """Mock LLM 客户端"""

    def chat(self, prompt: str) -> str:
        return f"[Mock LLM Response for: {prompt[:50]}...]"

    def generate(self, prompt: str) -> str:
        return self.chat(prompt)


class MockRetriever:
    """Mock 检索器"""

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        return [{"content": f"[Mock Doc {i+1} for: {query[:30]}]"} for i in range(top_k)]


# ============================================================================
# 完整 Pipeline 构建函数
# ============================================================================


def build_adaptive_rag_pipeline(
    env: LocalEnvironment,
    queries: list[str],
    classifier_type: str = "rule",
    llm_client: Any = None,
    retriever: Any = None,
    verbose: bool = True,
) -> LocalEnvironment:
    """
    构建完整的 Adaptive-RAG Pipeline

    Args:
        env: SAGE LocalEnvironment
        queries: 查询列表
        classifier_type: 分类器类型 ("rule", "llm", "t5")
        llm_client: LLM 客户端（可选）
        retriever: 检索器（可选）
        verbose: 是否打印详细信息

    Returns:
        配置好的 Environment

    用法:
        env = LocalEnvironment("adaptive-rag")
        build_adaptive_rag_pipeline(env, queries=["What is AI?", "Compare X and Y"])
        env.submit(autostop=True)
    """
    # 清空之前的结果
    ResultSink.clear_results()

    # 构建 Pipeline
    (
        env.from_source(QuerySource, queries=queries, delay=0.1)
        .map(ClassifierMapFunction, classifier_type=classifier_type, llm_client=llm_client)
        .map(AdaptiveRouterMapFunction, llm_client=llm_client, retriever=retriever)
        .sink(ResultSink, verbose=verbose, parallelism=1)
    )

    return env


# ============================================================================
# 主函数 - 演示用法
# ============================================================================


def main():
    """演示 Adaptive-RAG SAGE 数据流 Pipeline"""
    print("=" * 70)
    print("Adaptive-RAG SAGE 数据流 Pipeline 演示")
    print("=" * 70)

    # 示例查询（覆盖三种复杂度级别）
    queries = [
        # Level A (简单): 定义类问题
        "What is machine learning?",
        # Level B (中等): 需要事实支撑
        "What are the key features of Python 3.12?",
        # Level C (复杂): 多跳比较问题
        "Compare the economic policies of Japan and Germany in handling the 2008 financial crisis, and analyze their long-term effects on GDP growth.",
    ]

    print(f"\n📋 Processing {len(queries)} queries:")
    for i, q in enumerate(queries, 1):
        print(f"   {i}. {q[:60]}...")

    print("\n" + "-" * 70)
    print("🚀 Building and executing SAGE Pipeline...")
    print("-" * 70 + "\n")

    # 创建环境
    env = LocalEnvironment("adaptive-rag-demo")

    # 构建 Pipeline
    build_adaptive_rag_pipeline(env, queries=queries)

    # 执行
    try:
        env.submit(autostop=True)
        time.sleep(2)  # 等待处理完成
    finally:
        env.close()

    # 显示结果摘要
    results = ResultSink.get_all_results()
    print("\n" + "=" * 70)
    print(f"📊 Summary: Processed {len(results)} queries")
    print("=" * 70)

    strategy_counts = {}
    for r in results:
        strategy_counts[r.strategy_used] = strategy_counts.get(r.strategy_used, 0) + 1

    for strategy, count in strategy_counts.items():
        print(f"   - {strategy}: {count} queries")

    print(f"\n📁 Results saved to: {ResultSink._all_results[0].metadata if results else 'N/A'}")
    print("✅ Done.")


# ============================================================================
# 导出
# ============================================================================

__all__ = [
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
    # FlatMap
    "StrategyBranchFlatMap",
    # Sink
    "ResultSink",
    # 构建函数
    "build_adaptive_rag_pipeline",
    # Mock
    "MockLLMClient",
    "MockRetriever",
]


if __name__ == "__main__":
    main()
