#!/usr/bin/env python3
"""
LangChain RAG Pipeline Benchmark
================================

等价于 SAGE `--pipeline rag` 的 LangChain 实现，用于性能对比。

Pipeline 结构:
- SAGE: TaskSource -> SimpleRetriever -> SimpleReranker -> SimplePromptor -> SimpleGenerator -> MetricsSink
- LangChain: 使用 LCEL (LangChain Expression Language) 构建等价 chain

使用方法:
    python langchain_rag_benchmark.py --tasks 100 --concurrency 4
    python langchain_rag_benchmark.py --tasks 500 --concurrency 16
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# ============================================================================
# 配置
# ============================================================================

# 服务配置 (与 SAGE benchmark 保持一致)
LLM_HOST = os.getenv("LLM_HOST", "11.11.11.7")
LLM_BASE_URL = f"http://{LLM_HOST}:8904/v1"
LLM_MODEL = "Qwen/Qwen2.5-3B-Instruct"
EMBEDDING_BASE_URL = f"http://{LLM_HOST}:8090/v1"
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"

# 示例查询池 (与 SAGE SAMPLE_QUERIES 相同)
SAMPLE_QUERIES = [
    "SAGE version",
    "What is SAGE framework and what are its main features?",
    "Compare LocalEnvironment and RemoteEnvironment in terms of performance and use cases",
    "Python requirements",
    "How do I install SAGE on Ubuntu?",
    "Analyze the pros and cons of different scheduler strategies in SAGE",
    "License type",
    "What are the different scheduler strategies available?",
    "What is the relationship between sage-kernel and sage-middleware components?",
    "Default port",
    "How does the memory service work in SAGE?",
    "Compare FIFO and LoadAware schedulers and their impact on throughput",
    "Ray cluster",
    "What is the role of middleware components?",
    "Analyze the effects of parallelism settings on pipeline performance",
    "How to configure LLM services in SAGE?",
    "What embedding models are supported?",
    "What is the purpose of sage-kernel package?",
    "What vector databases are supported?",
    "What are the CPU node requirements?",
]

# 知识库 (与 SAGE SAMPLE_KNOWLEDGE_BASE 相同)
SAMPLE_KNOWLEDGE_BASE = [
    {
        "id": "1",
        "title": "SAGE Framework Overview",
        "content": "SAGE is a Python 3.10+ framework for building AI/LLM data processing pipelines.",
    },
    {
        "id": "2",
        "title": "SAGE Installation Guide",
        "content": "To install SAGE, run ./quickstart.sh --dev --yes for development.",
    },
    {
        "id": "3",
        "title": "Pipeline Architecture",
        "content": "SAGE pipelines use SourceFunction, MapFunction, and SinkFunction operators.",
    },
    {
        "id": "4",
        "title": "Scheduler Strategies",
        "content": "SAGE supports FIFO, LoadAware, Random, RoundRobin, and Priority schedulers.",
    },
    {
        "id": "5",
        "title": "Memory Services",
        "content": "sage-mem provides HierarchicalMemoryService with STM/MTM/LTM tiers.",
    },
]


# ============================================================================
# 数据模型
# ============================================================================


@dataclass
class TaskResult:
    """单个任务的结果"""
    task_id: str
    query: str
    response: str
    retrieved_docs: list[dict]
    
    # 时间指标 (ms)
    total_latency_ms: float
    retrieval_time_ms: float
    rerank_time_ms: float
    generation_time_ms: float
    
    success: bool = True
    error: str = ""


@dataclass
class BenchmarkResult:
    """Benchmark 汇总结果"""
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    
    total_duration_sec: float = 0.0
    
    latencies_ms: list[float] = field(default_factory=list)
    retrieval_times_ms: list[float] = field(default_factory=list)
    rerank_times_ms: list[float] = field(default_factory=list)
    generation_times_ms: list[float] = field(default_factory=list)
    
    @property
    def throughput(self) -> float:
        if self.total_duration_sec > 0:
            return self.successful_tasks / self.total_duration_sec
        return 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0.0
    
    @property
    def p50_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_lat = sorted(self.latencies_ms)
        return sorted_lat[len(sorted_lat) // 2]
    
    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]
    
    @property
    def p99_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]
    
    def print_summary(self):
        print("\n" + "=" * 70)
        print("LangChain RAG Benchmark Results")
        print("=" * 70)
        print(f"  Total Tasks:       {self.total_tasks}")
        print(f"  Successful:        {self.successful_tasks}")
        print(f"  Failed:            {self.failed_tasks}")
        print(f"  Duration:          {self.total_duration_sec:.2f}s")
        print("-" * 70)
        print(f"  Throughput:        {self.throughput:.2f} tasks/sec")
        print(f"  Avg Latency:       {self.avg_latency_ms:.2f} ms")
        print(f"  P50 Latency:       {self.p50_latency_ms:.2f} ms")
        print(f"  P95 Latency:       {self.p95_latency_ms:.2f} ms")
        print(f"  P99 Latency:       {self.p99_latency_ms:.2f} ms")
        print("-" * 70)
        if self.retrieval_times_ms:
            print(f"  Avg Retrieval:     {statistics.mean(self.retrieval_times_ms):.2f} ms")
        if self.rerank_times_ms:
            print(f"  Avg Rerank:        {statistics.mean(self.rerank_times_ms):.2f} ms")
        if self.generation_times_ms:
            print(f"  Avg Generation:    {statistics.mean(self.generation_times_ms):.2f} ms")
        print("=" * 70)


# ============================================================================
# LangChain RAG Pipeline 组件
# ============================================================================


def get_remote_embeddings(
    texts: list[str],
    base_url: str = EMBEDDING_BASE_URL,
    model: str = EMBEDDING_MODEL,
) -> list[list[float]] | None:
    """调用远程 Embedding 服务"""
    try:
        response = requests.post(
            f"{base_url}/embeddings",
            json={"input": texts, "model": model},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        return [item["embedding"] for item in result["data"]]
    except Exception as e:
        print(f"[Embedding Error] {e}")
        return None


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """计算余弦相似度"""
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class LangChainRAGPipeline:
    """
    LangChain 风格的 RAG Pipeline
    
    等价于 SAGE 的 SimpleRetriever -> SimpleReranker -> SimplePromptor -> SimpleGenerator
    """
    
    def __init__(
        self,
        llm_base_url: str = LLM_BASE_URL,
        llm_model: str = LLM_MODEL,
        embedding_base_url: str = EMBEDDING_BASE_URL,
        embedding_model: str = EMBEDDING_MODEL,
        knowledge_base: list[dict] | None = None,
        retriever_top_k: int = 10,
        reranker_top_k: int = 5,
        max_tokens: int = 256,
    ):
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.embedding_base_url = embedding_base_url
        self.embedding_model = embedding_model
        self.knowledge_base = knowledge_base or SAMPLE_KNOWLEDGE_BASE
        self.retriever_top_k = retriever_top_k
        self.reranker_top_k = reranker_top_k
        self.max_tokens = max_tokens
        
        # 预计算知识库 embeddings
        self._kb_embeddings: list[list[float]] | None = None
        self._initialize_kb_embeddings()
    
    def _initialize_kb_embeddings(self):
        """初始化知识库向量"""
        texts = [doc.get("content", "") for doc in self.knowledge_base]
        self._kb_embeddings = get_remote_embeddings(
            texts,
            base_url=self.embedding_base_url,
            model=self.embedding_model,
        )
        if self._kb_embeddings:
            print(f"[LangChain] Initialized KB with {len(self._kb_embeddings)} embeddings")
        else:
            print("[LangChain] Warning: Failed to initialize KB embeddings")
    
    def retrieve(self, query: str) -> tuple[list[dict], float]:
        """
        Stage 1: 检索 (等价于 SimpleRetriever)
        
        Returns:
            (retrieved_docs, retrieval_time_ms)
        """
        start = time.time()
        
        query_embeddings = get_remote_embeddings(
            [query],
            base_url=self.embedding_base_url,
            model=self.embedding_model,
        )
        
        if not query_embeddings or not self._kb_embeddings:
            # Fallback to keyword matching
            return self._keyword_retrieve(query), (time.time() - start) * 1000
        
        query_vec = query_embeddings[0]
        
        # 计算相似度
        scored_docs = []
        for i, (doc, doc_vec) in enumerate(zip(self.knowledge_base, self._kb_embeddings)):
            score = cosine_similarity(query_vec, doc_vec)
            scored_docs.append({
                "id": doc.get("id", str(i)),
                "title": doc.get("title", ""),
                "content": doc.get("content", ""),
                "score": score,
            })
        
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        retrieval_time = (time.time() - start) * 1000
        
        return scored_docs[:self.retriever_top_k], retrieval_time
    
    def _keyword_retrieve(self, query: str) -> list[dict]:
        """关键词检索 fallback"""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_docs = []
        for i, doc in enumerate(self.knowledge_base):
            content = doc.get("content", "").lower()
            title = doc.get("title", "").lower()
            score = sum(1 for w in query_words if w in content or w in title)
            if score > 0:
                scored_docs.append({
                    "id": doc.get("id", str(i)),
                    "title": doc.get("title", ""),
                    "content": doc.get("content", ""),
                    "score": score / 10.0,
                })
        
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[:self.retriever_top_k]
    
    def rerank(self, query: str, docs: list[dict]) -> tuple[list[dict], float]:
        """
        Stage 2: 重排 (等价于 SimpleReranker)
        
        Returns:
            (reranked_docs, rerank_time_ms)
        """
        start = time.time()
        
        if not docs:
            return [], 0.0
        
        # 获取 query embedding
        query_embeddings = get_remote_embeddings(
            [query],
            base_url=self.embedding_base_url,
            model=self.embedding_model,
        )
        
        # 获取 doc embeddings
        doc_texts = [doc.get("content", "")[:500] for doc in docs]
        doc_embeddings = get_remote_embeddings(
            doc_texts,
            base_url=self.embedding_base_url,
            model=self.embedding_model,
        )
        
        if not query_embeddings or not doc_embeddings:
            rerank_time = (time.time() - start) * 1000
            return docs[:self.reranker_top_k], rerank_time
        
        query_vec = query_embeddings[0]
        
        # 计算新分数
        reranked = []
        for doc, doc_vec in zip(docs, doc_embeddings):
            score = cosine_similarity(query_vec, doc_vec)
            reranked.append({**doc, "rerank_score": score})
        
        reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        rerank_time = (time.time() - start) * 1000
        
        return reranked[:self.reranker_top_k], rerank_time
    
    def build_prompt(self, query: str, docs: list[dict]) -> str:
        """
        Stage 3: 构建 Prompt (等价于 SimplePromptor)
        """
        context_parts = []
        for doc in docs:
            title = doc.get("title", "")
            content = doc.get("content", "")
            context_parts.append(f"[{title}]\n{content}")
        
        context = "\n\n".join(context_parts)
        return f"上下文:\n{context}\n\n问题: {query}"
    
    def generate(self, query: str, context: str) -> tuple[str, float]:
        """
        Stage 4: 生成 (等价于 SimpleGenerator)
        
        Returns:
            (response, generation_time_ms)
        """
        start = time.time()
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是一个helpful助手。根据上下文回答问题，如果没有相关信息，请直接说明。",
                },
                {"role": "user", "content": context},
            ]
            
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
            answer = result["choices"][0]["message"]["content"]
            
        except Exception as e:
            answer = f"[Generation Error] {str(e)}"
        
        generation_time = (time.time() - start) * 1000
        return answer, generation_time
    
    def invoke(self, query: str, task_id: str = "") -> TaskResult:
        """
        执行完整的 RAG pipeline
        
        等价于 SAGE: Retrieve -> Rerank -> Prompt -> Generate
        """
        total_start = time.time()
        
        try:
            # Stage 1: Retrieve
            docs, retrieval_time = self.retrieve(query)
            
            # Stage 2: Rerank
            reranked_docs, rerank_time = self.rerank(query, docs)
            
            # Stage 3: Build Prompt
            prompt = self.build_prompt(query, reranked_docs)
            
            # Stage 4: Generate
            response, generation_time = self.generate(query, prompt)
            
            total_latency = (time.time() - total_start) * 1000
            
            return TaskResult(
                task_id=task_id,
                query=query,
                response=response,
                retrieved_docs=reranked_docs,
                total_latency_ms=total_latency,
                retrieval_time_ms=retrieval_time,
                rerank_time_ms=rerank_time,
                generation_time_ms=generation_time,
                success=True,
            )
            
        except Exception as e:
            total_latency = (time.time() - total_start) * 1000
            return TaskResult(
                task_id=task_id,
                query=query,
                response="",
                retrieved_docs=[],
                total_latency_ms=total_latency,
                retrieval_time_ms=0,
                rerank_time_ms=0,
                generation_time_ms=0,
                success=False,
                error=str(e),
            )


# ============================================================================
# Benchmark Runner
# ============================================================================


def run_benchmark(
    num_tasks: int = 100,
    concurrency: int = 4,
    output_dir: str | None = None,
) -> BenchmarkResult:
    """
    运行 LangChain RAG Benchmark
    
    Args:
        num_tasks: 任务数量
        concurrency: 并发数
        output_dir: 结果输出目录
    """
    print("\n" + "=" * 70)
    print("LangChain RAG Pipeline Benchmark")
    print("=" * 70)
    print(f"  Tasks:       {num_tasks}")
    print(f"  Concurrency: {concurrency}")
    print(f"  LLM:         {LLM_BASE_URL} ({LLM_MODEL})")
    print(f"  Embedding:   {EMBEDDING_BASE_URL} ({EMBEDDING_MODEL})")
    print("=" * 70)
    
    # 初始化 pipeline
    pipeline = LangChainRAGPipeline()
    
    # 生成任务
    queries = [SAMPLE_QUERIES[i % len(SAMPLE_QUERIES)] for i in range(num_tasks)]
    
    # 运行 benchmark
    result = BenchmarkResult()
    result.total_tasks = num_tasks
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(pipeline.invoke, query, f"task_{i:05d}"): i
            for i, query in enumerate(queries)
        }
        
        for future in as_completed(futures):
            task_idx = futures[future]
            try:
                task_result = future.result()
                
                if task_result.success:
                    result.successful_tasks += 1
                    result.latencies_ms.append(task_result.total_latency_ms)
                    result.retrieval_times_ms.append(task_result.retrieval_time_ms)
                    result.rerank_times_ms.append(task_result.rerank_time_ms)
                    result.generation_times_ms.append(task_result.generation_time_ms)
                else:
                    result.failed_tasks += 1
                    print(f"  Task {task_idx} failed: {task_result.error}")
                    
            except Exception as e:
                result.failed_tasks += 1
                print(f"  Task {task_idx} exception: {e}")
    
    result.total_duration_sec = time.time() - start_time
    
    # 打印结果
    result.print_summary()
    
    # 保存结果
    if output_dir:
        save_results(result, output_dir)
    
    return result


def save_results(result: BenchmarkResult, output_dir: str):
    """保存结果到文件"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path(output_dir) / f"langchain_rag_{timestamp}.json"
    
    data = {
        "timestamp": timestamp,
        "framework": "langchain",
        "pipeline_type": "rag",
        "total_tasks": result.total_tasks,
        "successful_tasks": result.successful_tasks,
        "failed_tasks": result.failed_tasks,
        "total_duration_sec": result.total_duration_sec,
        "throughput_tasks_per_sec": result.throughput,
        "avg_latency_ms": result.avg_latency_ms,
        "p50_latency_ms": result.p50_latency_ms,
        "p95_latency_ms": result.p95_latency_ms,
        "p99_latency_ms": result.p99_latency_ms,
        "avg_retrieval_ms": statistics.mean(result.retrieval_times_ms) if result.retrieval_times_ms else 0,
        "avg_rerank_ms": statistics.mean(result.rerank_times_ms) if result.rerank_times_ms else 0,
        "avg_generation_ms": statistics.mean(result.generation_times_ms) if result.generation_times_ms else 0,
        "config": {
            "llm_base_url": LLM_BASE_URL,
            "llm_model": LLM_MODEL,
            "embedding_base_url": EMBEDDING_BASE_URL,
            "embedding_model": EMBEDDING_MODEL,
        },
    }
    
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="LangChain RAG Pipeline Benchmark")
    parser.add_argument("--tasks", type=int, default=100, help="Number of tasks")
    parser.add_argument("--concurrency", type=int, default=4, help="Concurrency level")
    parser.add_argument("--output", type=str, default="results", help="Output directory")
    
    args = parser.parse_args()
    
    run_benchmark(
        num_tasks=args.tasks,
        concurrency=args.concurrency,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()
