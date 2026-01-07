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
    from sage.benchmark.benchmark_sage.experiments.pipelines.adaptive_rag import (
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

from sage.common.core import (
    FilterFunction,
    MapFunction,
    SinkFunction,
    SourceFunction,
)
from sage.kernel.api import LocalEnvironment
from sage.kernel.api.remote_environment import RemoteEnvironment

# 支持直接运行和模块运行两种方式
try:
    from .classifier import (
        ClassificationResult,
        QueryComplexityLevel,
        create_classifier,
    )
except ImportError:
    from classifier import (
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


@dataclass
class IterativeState:
    """迭代检索的中间状态 - 在流中传递"""
    original_query: str                          # 原始问题
    current_query: str                           # 当前检索 query (可能是子查询)
    accumulated_docs: list[dict] = field(default_factory=list)  # 累积的文档
    reasoning_chain: list[str] = field(default_factory=list)    # 推理链
    iteration: int = 0                           # 当前迭代次数
    is_complete: bool = False                    # 是否已完成（提前终止）
    start_time: float = 0.0                      # 开始时间
    classification: ClassificationResult | None = None


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
        print(f"📤 Source [{self.counter}/{len(self.queries)}]: {query}")
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

        print(f"🏷️ Classified: {data.query} -> {classification.complexity.name}")
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
            print(f"  ✅ ZERO branch: {data.query}")
        return is_match


class SingleComplexityFilter(FilterFunction):
    """过滤: 只保留 SINGLE (中等) 复杂度的查询"""

    def execute(self, data: QueryData) -> bool:
        if data.classification is None:
            return False
        is_match = data.classification.complexity == QueryComplexityLevel.SINGLE
        if is_match:
            print(f"  ✅ SINGLE branch: {data.query}")
        return is_match


class MultiComplexityFilter(FilterFunction):
    """过滤: 只保留 MULTI (复杂) 复杂度的查询"""

    def execute(self, data: QueryData) -> bool:
        if data.classification is None:
            return False
        is_match = data.classification.complexity == QueryComplexityLevel.MULTI
        if is_match:
            print(f"  ✅ MULTI branch: {data.query}")
        return is_match


# ============================================================================
# Strategy MapFunctions: 各分支的处理逻辑
# 使用 requests 直接调用 LLM API (参考 SimpleGenerator 风格)
# ============================================================================


class NoRetrievalStrategy(MapFunction):
    """
    策略 A: 无检索 - 直接 LLM 生成

    适用于简单问题，LLM 可直接回答。
    """

    def __init__(
        self,
        llm_base_url: str = "http://11.11.11.7:8903/v1",
        llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
        max_tokens: int = 512,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.max_tokens = max_tokens

    def _generate(self, query: str) -> str:
        """直接调用 LLM 生成回复"""
        import requests

        messages = [
            {"role": "user", "content": query},
        ]

        try:
            response = requests.post(
                f"{self.llm_base_url}/chat/completions",
                json={
                    "model": self.llm_model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": 0.7,
                },
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[Generation Error] {str(e)}"

    def execute(self, data: QueryData) -> ResultData:
        start_time = time.time()

        print(f"  🔵 NoRetrieval: {data.query}")

        answer = self._generate(data.query)

        return ResultData(
            query=data.query,
            answer=answer,
            strategy_used="no_retrieval",
            complexity="ZERO",
            retrieval_steps=0,
            processing_time_ms=(time.time() - start_time) * 1000,
        )


class SingleRetrievalStrategy(MapFunction):
    """
    策略 B: 单次检索 + 生成

    适用于需要检索上下文的问题。
    """

    # 简单知识库 (可替换为真实检索)
    KNOWLEDGE_BASE = [
        {"content": "Machine learning is a subset of artificial intelligence that learns from data.", "id": "1"},
        {"content": "Deep learning uses neural networks with multiple layers.", "id": "2"},
        {"content": "Python is a popular programming language for ML tasks.", "id": "3"},
        {"content": "BERT is a transformer-based model for NLP tasks.", "id": "4"},
        {"content": "RAG combines retrieval with generation for better answers.", "id": "5"},
    ]

    def __init__(
        self,
        llm_base_url: str = "http://11.11.11.7:8903/v1",
        llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
        max_tokens: int = 512,
        top_k: int = 3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.max_tokens = max_tokens
        self.top_k = top_k

    def _retrieve(self, query: str) -> list[dict]:
        """简单关键词检索"""
        query_words = set(query.lower().split())
        scored_docs = []

        for doc in self.KNOWLEDGE_BASE:
            content_words = set(doc["content"].lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                scored_docs.append({**doc, "score": overlap / len(query_words)})

        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[:self.top_k]

    def _generate(self, query: str, context: str) -> str:
        """基于上下文生成回复"""
        import requests

        messages = [
            {
                "role": "system",
                "content": "Answer the question based on the provided context. If no relevant info, say so.",
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}",
            },
        ]

        try:
            response = requests.post(
                f"{self.llm_base_url}/chat/completions",
                json={
                    "model": self.llm_model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": 0.7,
                },
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[Generation Error] {str(e)}"

    def execute(self, data: QueryData) -> ResultData:
        start_time = time.time()

        print(f"  🟡 SingleRetrieval: {data.query}")

        # 检索
        docs = self._retrieve(data.query)
        context = "\n".join([f"[Doc {i+1}]: {d['content']}" for i, d in enumerate(docs)])
        if not context:
            context = "No relevant documents found."

        # 生成
        answer = self._generate(data.query, context)

        return ResultData(
            query=data.query,
            answer=answer,
            strategy_used="single_retrieval",
            complexity="SINGLE",
            retrieval_steps=len(docs),
            processing_time_ms=(time.time() - start_time) * 1000,
        )


class IterativeRetrievalStrategy(MapFunction):
    """
    策略 C: 迭代检索 (IRCoT 风格) - 初始化状态

    将 QueryData 转换为 IterativeState，开始迭代流程。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def execute(self, data: QueryData) -> IterativeState:
        print(f"  🔴 IterativeRetrieval Init: {data.query}")
        return IterativeState(
            original_query=data.query,
            current_query=data.query,
            accumulated_docs=[],
            reasoning_chain=[],
            iteration=0,
            is_complete=False,
            start_time=time.time(),
            classification=data.classification,
        )


# ============================================================================
# 迭代检索的独立算子 (用于 MULTI 分支的循环展开)
# ============================================================================


class SimpleRetriever(MapFunction):
    """
    检索算子 - 根据 current_query 检索文档

    输入: IterativeState
    输出: IterativeState (更新 accumulated_docs)
    """

    KNOWLEDGE_BASE = [
        {"content": "Machine learning is a subset of artificial intelligence that learns from data.", "id": "1"},
        {"content": "Deep learning uses neural networks with multiple layers.", "id": "2"},
        {"content": "Python is a popular programming language for ML tasks.", "id": "3"},
        {"content": "BERT is a transformer-based model for NLP tasks.", "id": "4"},
        {"content": "RAG combines retrieval with generation for better answers.", "id": "5"},
        {"content": "Transformers use attention mechanisms for sequence modeling.", "id": "6"},
        {"content": "GPT models are autoregressive language models.", "id": "7"},
    ]

    def __init__(self, top_k: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.top_k = top_k

    def execute(self, state: IterativeState) -> IterativeState:
        # 如果已完成，直接透传
        if state.is_complete:
            return state

        # 简单关键词检索
        query_words = set(state.current_query.lower().split())
        scored_docs = []

        for doc in self.KNOWLEDGE_BASE:
            content_words = set(doc["content"].lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                scored_docs.append({**doc, "score": overlap / len(query_words)})

        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        new_docs = scored_docs[:self.top_k]

        # 更新状态
        state.accumulated_docs.extend(new_docs)
        state.reasoning_chain.append(f"[Retrieve] Query: '{state.current_query}' -> {len(new_docs)} docs")

        print(f"    📚 Retrieve[{state.iteration}]: {len(new_docs)} docs for '{state.current_query[:30]}...'")
        return state


class IterativeReasoner(MapFunction):
    """
    推理算子 - 判断是否继续迭代 + 生成下一个子查询

    输入: IterativeState
    输出: IterativeState (更新 current_query, iteration, is_complete)
    """

    def __init__(
        self,
        llm_base_url: str = "http://11.11.11.7:8903/v1",
        llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
        max_iterations: int = 3,
        min_docs: int = 5,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.max_iterations = max_iterations
        self.min_docs = min_docs

    def _llm_call(self, messages: list[dict]) -> str:
        import requests
        try:
            response = requests.post(
                f"{self.llm_base_url}/chat/completions",
                json={"model": self.llm_model, "messages": messages, "max_tokens": 256, "temperature": 0.7},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[LLM Error] {str(e)}"

    def execute(self, state: IterativeState) -> IterativeState:
        # 如果已完成，直接透传
        if state.is_complete:
            return state

        state.iteration += 1

        # 检查终止条件
        if state.iteration >= self.max_iterations or len(state.accumulated_docs) >= self.min_docs:
            state.is_complete = True
            state.reasoning_chain.append(f"[Reason] Iteration {state.iteration}: Complete (docs={len(state.accumulated_docs)})")
            print(f"    🧠 Reason[{state.iteration}]: COMPLETE")
            return state

        # 生成下一个子查询
        context_so_far = "\n".join([f"- {d['content']}" for d in state.accumulated_docs[-3:]])
        messages = [
            {"role": "system", "content": "Generate a follow-up search query to find more information. Reply with ONLY the query."},
            {"role": "user", "content": f"Original: {state.original_query}\n\nContext:\n{context_so_far}\n\nFollow-up query:"},
        ]
        new_query = self._llm_call(messages).strip()

        state.current_query = new_query
        state.reasoning_chain.append(f"[Reason] Iteration {state.iteration}: Next query = '{new_query[:50]}'")
        print(f"    🧠 Reason[{state.iteration}]: Next -> '{new_query[:40]}...'")
        return state


class FinalSynthesizer(MapFunction):
    """
    综合生成算子 - 将所有收集的信息合成最终答案

    输入: IterativeState
    输出: ResultData
    """

    def __init__(
        self,
        llm_base_url: str = "http://11.11.11.7:8903/v1",
        llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model

    def _llm_call(self, messages: list[dict]) -> str:
        import requests
        try:
            response = requests.post(
                f"{self.llm_base_url}/chat/completions",
                json={"model": self.llm_model, "messages": messages, "max_tokens": 512, "temperature": 0.7},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[LLM Error] {str(e)}"

    def execute(self, state: IterativeState) -> ResultData:
        # 构建上下文
        context = "\n".join([f"[Doc {i+1}]: {d['content']}" for i, d in enumerate(state.accumulated_docs)])
        chain_text = "\n".join(state.reasoning_chain)

        messages = [
            {"role": "system", "content": "Synthesize all information to answer comprehensively."},
            {"role": "user", "content": f"Question: {state.original_query}\n\nReasoning:\n{chain_text}\n\nContext:\n{context}\n\nAnswer:"},
        ]
        answer = self._llm_call(messages)

        print(f"    ✨ Synthesize: Generated answer ({len(answer)} chars)")

        return ResultData(
            query=state.original_query,
            answer=answer,
            strategy_used="iterative_retrieval",
            complexity="MULTI",
            retrieval_steps=state.iteration,
            processing_time_ms=(time.time() - state.start_time) * 1000,
        )


# ============================================================================
# Sink: 结果收集器
# ============================================================================


class ResultSink(SinkFunction):
    """
    结果收集器

    Remote 模式下将结果写入文件，支持跨节点收集。
    """

    # 结果输出目录
    RESULTS_OUTPUT_DIR = "/tmp/sage_adaptive_rag_results"

    _all_results: list[ResultData] = []  # Local 模式用

    def __init__(self, branch_name: str = "", **kwargs):
        super().__init__(**kwargs)
        self.branch_name = branch_name
        self.count = 0

        # 创建唯一的输出文件 (Remote 模式用)
        import os
        import socket

        self.instance_id = f"{socket.gethostname()}_{os.getpid()}_{int(time.time() * 1000)}"
        os.makedirs(self.RESULTS_OUTPUT_DIR, exist_ok=True)
        self.results_output_file = f"{self.RESULTS_OUTPUT_DIR}/results_{self.instance_id}.jsonl"

    def _write_to_file(self, data: ResultData) -> None:
        """将结果写入文件 (Remote 模式)"""
        import json

        try:
            record = {
                "query": data.query,
                "answer": data.answer,
                "strategy_used": data.strategy_used,
                "complexity": data.complexity,
                "retrieval_steps": data.retrieval_steps,
                "processing_time_ms": data.processing_time_ms,
                "branch_name": self.branch_name,
                "timestamp": time.time(),
            }
            with open(self.results_output_file, "a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            import sys
            print(f"[ResultSink] Write error: {e}", file=sys.stderr, flush=True)

    def execute(self, data: ResultData):
        self.count += 1
        ResultSink._all_results.append(data)

        # 写入文件 (Remote 模式可收集)
        self._write_to_file(data)

        # 打印到 stderr (Remote 模式下可能看不到，但 Local 可以)
        import sys
        print(
            f"\n🎯 [{self.branch_name}] Result #{self.count}:\n"
            f"   Query: {data.query}\n"
            f"   Strategy: {data.strategy_used}\n"
            f"   Complexity: {data.complexity}\n"
            f"   Retrieval Steps: {data.retrieval_steps}\n"
            f"   Time: {data.processing_time_ms:.1f}ms\n"
            f"   Answer:\n{data.answer}",
            file=sys.stderr,
            flush=True,
        )

        return data

    @classmethod
    def get_all_results(cls) -> list[ResultData]:
        return cls._all_results.copy()

    @classmethod
    def clear_results(cls):
        cls._all_results.clear()

    @classmethod
    def collect_from_files(cls) -> list[dict]:
        """
        从文件收集所有结果 (Remote 模式用)

        会从本地和远程节点收集结果文件。
        """
        import json
        import subprocess
        from pathlib import Path

        results_dir = Path(cls.RESULTS_OUTPUT_DIR)
        results_dir.mkdir(parents=True, exist_ok=True)

        # 从远程节点收集文件
        worker_nodes = ["sage-node-2", "sage-node-3", "sage-node-4"]
        for node in worker_nodes:
            try:
                cmd = f"scp -o StrictHostKeyChecking=no {node}:{cls.RESULTS_OUTPUT_DIR}/*.jsonl {cls.RESULTS_OUTPUT_DIR}/ 2>/dev/null"
                subprocess.run(cmd, shell=True, timeout=10)
            except Exception:
                pass

        # 读取所有结果文件
        all_results = []
        for f in results_dir.glob("results_*.jsonl"):
            try:
                with open(f) as fp:
                    for line in fp:
                        if line.strip():
                            all_results.append(json.loads(line.strip()))
            except Exception:
                pass

        return all_results


# ============================================================================
# 流分支 Pipeline 构建函数
# ============================================================================


def build_branching_adaptive_rag_pipeline(
    env: LocalEnvironment | RemoteEnvironment,
    queries: list[str],
    classifier_type: str = "rule",
    llm_base_url: str = "http://11.11.11.7:8903/v1",
    llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
    max_iterations: int = 3,
) -> LocalEnvironment | RemoteEnvironment:
    """
    构建流分支模式的 Adaptive-RAG Pipeline

    这是 SAGE 推荐的多分支模式：对同一个流多次应用 filter 创建不同分支。
    MULTI 分支使用"循环展开"模式实现迭代检索。

    架构:
    ```
                          ┌─ filter(ZERO) ─> Generator ─> sink(ZERO)
                          │
    Source ─> Classifier ─┼─ filter(SINGLE) ─> Retriever ─> Prompter ─> Generator ─> sink(SINGLE)
                          │
                          └─ filter(MULTI) ─> InitState ─┬─> Retrieve ─> Reason ─┐
                                                         │                       │
                                                         ├─> Retrieve ─> Reason ─┤ (循环展开)
                                                         │                       │
                                                         └─> Retrieve ─> Reason ─┴─> Synthesize ─> sink(MULTI)
    ```

    Args:
        env: SAGE LocalEnvironment 或 RemoteEnvironment
        queries: 查询列表
        classifier_type: 分类器类型
        llm_base_url: LLM 服务地址
        llm_model: LLM 模型名称
        max_iterations: MULTI 分支的最大迭代次数

    Returns:
        配置好的 Environment
    """
    ResultSink.clear_results()

    # Step 1: 创建 Source 和 Classifier（共享的上游）
    classified_stream = (
        env.from_source(QuerySource, queries=queries, delay=0.1)
        .map(ClassifierMap, classifier_type=classifier_type)
    )

    # Step 2: 分支 A - ZERO 复杂度 (无检索，直接生成)
    (
        classified_stream
        .filter(ZeroComplexityFilter)
        .map(NoRetrievalStrategy, llm_base_url=llm_base_url, llm_model=llm_model)
        .sink(ResultSink, branch_name="ZERO", parallelism=1)
    )

    # Step 3: 分支 B - SINGLE 复杂度 (单次检索 + 生成)
    (
        classified_stream
        .filter(SingleComplexityFilter)
        .map(SingleRetrievalStrategy, llm_base_url=llm_base_url, llm_model=llm_model)
        .sink(ResultSink, branch_name="SINGLE", parallelism=1)
    )

    # Step 4: 分支 C - MULTI 复杂度 (迭代检索 - 循环展开模式)
    # 架构: InitState -> [Retrieve -> Reason] x N -> Synthesize -> Sink
    multi_stream = (
        classified_stream
        .filter(MultiComplexityFilter)
        .map(IterativeRetrievalStrategy)  # QueryData -> IterativeState
    )

    # 循环展开: 串联 N 个 [Retrieve -> Reason] Stage
    for i in range(max_iterations):
        multi_stream = (
            multi_stream
            .map(SimpleRetriever, top_k=3)  # 检索
            .map(IterativeReasoner, llm_base_url=llm_base_url, llm_model=llm_model, max_iterations=max_iterations)  # 推理
        )

    # 最终综合生成
    (
        multi_stream
        .map(FinalSynthesizer, llm_base_url=llm_base_url, llm_model=llm_model)  # IterativeState -> ResultData
        .sink(ResultSink, branch_name="MULTI", parallelism=1)
    )

    return env


# ============================================================================
# 主函数 - 演示
# ============================================================================


def main():
    """演示流分支 Adaptive-RAG Pipeline"""
    import sys

    # 默认使用 Local 模式，通过命令行参数切换
    use_remote = "--remote" in sys.argv

    mode_name = "Remote" if use_remote else "Local"
    print("=" * 70)
    print(f"Adaptive-RAG 流分支 Pipeline 演示 ({mode_name} Mode + 真实 LLM)")
    print("=" * 70)

    # LLM 配置 - 传递配置参数而不是客户端对象，支持 Remote 序列化
    llm_base_url = "http://11.11.11.7:8903/v1"
    llm_model = "Qwen/Qwen2.5-7B-Instruct"

    print(f"\n🔌 LLM 配置: {llm_base_url} / {llm_model}")

    queries = [
        "What is machine learning?",  # ZERO
        "What are the key features of Python 3.12?",  # ZERO
        "Compare Japan and Germany economic policies during 2008 crisis and their long-term effects on GDP",  # MULTI
        "Define artificial intelligence",  # ZERO
        "How does BERT work for NLP tasks?",  # SINGLE
    ]

    print(f"\n📋 Processing {len(queries)} queries:")
    for i, q in enumerate(queries, 1):
        print(f"   {i}. {q}")

    print("\n" + "-" * 70)
    print(f"🚀 Building Multi-Branch Pipeline ({mode_name} Mode)...")
    print("-" * 70 + "\n")

    # 根据模式创建环境
    if use_remote:
        env = RemoteEnvironment(
            name="adaptive-rag-branch",
            host="sage-node-1",  # Ray head node
        )
    else:
        env = LocalEnvironment(name="adaptive-rag-branch")

    build_branching_adaptive_rag_pipeline(
        env,
        queries=queries,
        llm_base_url=llm_base_url,
        llm_model=llm_model,
    )

    print("Pipeline structure (循环展开模式):")
    print("  Source -> Classifier -+-> filter(ZERO) -> Generator -> Sink")
    print("                        +-> filter(SINGLE) -> Retriever -> Generator -> Sink")
    print("                        +-> filter(MULTI) -> InitState -+-> [Retrieve -> Reason] x3 -> Synthesize -> Sink")
    print("                                            (循环展开: 独立算子串联)")
    print()

    try:
        env.submit(autostop=True)
        # 等待完成
        env._wait_for_completion()
    except Exception as e:
        print(f"\n⚠️ Pipeline error: {e}")
    finally:
        try:
            env.close()
        except Exception:
            pass

    # 收集结果
    if use_remote:
        # Remote 模式：从文件收集
        print("\n[Collecting results from remote nodes...]")
        file_results = ResultSink.collect_from_files()
        print(f"[Collected {len(file_results)} results from files]")
    else:
        # Local 模式：直接从类变量获取
        file_results = None

    results = ResultSink.get_all_results() if not use_remote else []

    # 合并结果
    if file_results:
        total_results = file_results
    else:
        total_results = [
            {
                "query": r.query,
                "answer": r.answer,
                "strategy_used": r.strategy_used,
                "complexity": r.complexity,
                "retrieval_steps": r.retrieval_steps,
                "processing_time_ms": r.processing_time_ms,
            }
            for r in results
        ]

    print("\n" + "=" * 70)
    print(f"📊 Summary: Processed {len(total_results)} queries")
    print("=" * 70)

    strategy_counts = {}
    for r in total_results:
        strategy = r.get("strategy_used", r.strategy_used if hasattr(r, "strategy_used") else "unknown")
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

    for strategy, count in strategy_counts.items():
        print(f"   - {strategy}: {count} queries")

    # 打印所有结果的详细信息
    print("\n" + "=" * 70)
    print("📝 All Results Details:")
    print("=" * 70)
    for i, r in enumerate(total_results, 1):
        if isinstance(r, dict):
            print(f"\n--- Result {i}/{len(total_results)} ---")
            print(f"Query: {r.get('query', 'N/A')}")
            print(f"Strategy: {r.get('strategy_used', 'N/A')}")
            print(f"Complexity: {r.get('complexity', 'N/A')}")
            print(f"Retrieval Steps: {r.get('retrieval_steps', 'N/A')}")
            print(f"Processing Time: {r.get('processing_time_ms', 0):.1f}ms")
            print(f"Answer:\n{r.get('answer', 'N/A')}")
            print("-" * 40)
        else:
            print(f"\n--- Result {i}/{len(total_results)} ---")
            print(f"Query: {r.query}")
            print(f"Strategy: {r.strategy_used}")
            print(f"Complexity: {r.complexity}")
            print(f"Retrieval Steps: {r.retrieval_steps}")
            print(f"Processing Time: {r.processing_time_ms:.1f}ms")
            print(f"Answer:\n{r.answer}")
            print("-" * 40)

    print("\n✅ Multi-Branch Pipeline completed.")


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 数据结构
    "QueryData",
    "ResultData",
    "IterativeState",
    # Source & Classifier
    "QuerySource",
    "ClassifierMap",
    # Filters
    "ZeroComplexityFilter",
    "SingleComplexityFilter",
    "MultiComplexityFilter",
    # Strategy (ZERO/SINGLE)
    "NoRetrievalStrategy",
    "SingleRetrievalStrategy",
    # 迭代检索独立算子 (MULTI 分支循环展开)
    "IterativeRetrievalStrategy",  # InitState
    "SimpleRetriever",             # 检索算子
    "IterativeReasoner",           # 推理算子
    "FinalSynthesizer",            # 综合生成算子
    # Sink & Builder
    "ResultSink",
    "build_branching_adaptive_rag_pipeline",
]


if __name__ == "__main__":
    main()
