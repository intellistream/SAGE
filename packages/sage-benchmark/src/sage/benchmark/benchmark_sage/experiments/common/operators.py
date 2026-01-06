"""
Distributed Scheduling Benchmark - Pipeline Operators
======================================================

Pipeline 算子:
- TaskSource: 任务生成源
- ComputeOperator: CPU 计算任务 (用于调度测试)
- LLMOperator: LLM 推理任务
- RAGOperator: RAG 检索+生成任务
- MetricsSink: 指标收集
"""

from __future__ import annotations

import hashlib
import os
import socket
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction
from sage.common.core.functions.source_function import SourceFunction
from sage.kernel.runtime.communication.packet import StopSignal

if TYPE_CHECKING:
    from .models import TaskState

try:
    from .models import TaskState
except ImportError:
    from models import TaskState


# 示例查询池
SAMPLE_QUERIES = [
    "What is SAGE framework and what are its main features?",
    "How do I install SAGE on Ubuntu?",
    "Explain the pipeline architecture in SAGE",
    "What are the different scheduler strategies available?",
    "How does the memory service work in SAGE?",
    "What is the role of middleware components?",
    "How to configure LLM services in SAGE?",
    "Explain the difference between LocalEnvironment and RemoteEnvironment",
    "What are the best practices for building RAG pipelines?",
    "How does distributed scheduling work in SAGE?",
    "What embedding models are supported?",
    "How to optimize pipeline performance?",
    "Explain the six-layer architecture of SAGE",
    "What is the purpose of sage-kernel package?",
    "How to monitor pipeline execution?",
    "What vector databases are supported?",
    "How to implement custom operators?",
    "Explain the ReAct reasoning pattern",
    "What are the CPU node requirements?",
    "How to configure multi-node clusters?",
]

# 知识库
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


class TaskSource(SourceFunction):
    """
    任务生成源。

    从查询池生成测试任务。
    """

    def __init__(
        self,
        num_tasks: int = 100,
        query_pool: list[str] | None = None,
        task_complexity: str = "medium",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.query_pool = query_pool or SAMPLE_QUERIES
        self.num_tasks = num_tasks
        self.task_complexity = task_complexity
        self.current_index = 0

    def execute(self, data=None) -> TaskState | StopSignal:
        """生成下一个任务"""
        if self.current_index >= self.num_tasks:
            time.sleep(60.0)  # 60 秒等待所有 actor 启动和 LLM 响应
            return StopSignal("All tasks generated")

        query = self.query_pool[self.current_index % len(self.query_pool)]
        self.current_index += 1

        state = TaskState(
            task_id=f"task_{self.current_index:05d}",
            query=query,
            created_time=time.time(),
            metadata={"complexity": self.task_complexity},
        )

        return state


class ComputeOperator(MapFunction):
    """
    CPU 计算任务算子。

    用于测试纯调度性能，不依赖外部服务。
    可配置计算复杂度 (light/medium/heavy)。
    """

    def __init__(
        self,
        complexity: str = "medium",
        stage: int = 1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.complexity = complexity
        self.stage = stage
        self._hostname = socket.gethostname()

        # 复杂度对应的迭代次数
        self.iterations = {
            "light": 1000,
            "medium": 10000,
            "heavy": 100000,
        }.get(complexity, 10000)

    def _do_compute(self, data: str) -> str:
        """执行 CPU 密集计算"""
        result = data
        for i in range(self.iterations):
            result = hashlib.md5(f"{result}{i}".encode()).hexdigest()
        return result

    def execute(self, data: TaskState) -> TaskState:
        """执行计算任务"""
        if not isinstance(data, TaskState):
            return data

        state = data
        state.node_id = self._hostname
        state.stage = self.stage
        state.operator_name = f"ComputeOperator_{self.stage}"
        state.mark_started()

        try:
            # 执行计算
            result = self._do_compute(state.query)
            state.metadata[f"compute_result_{self.stage}"] = result[:16]
            state.success = True
        except Exception as e:
            state.success = False
            state.error = str(e)

        state.mark_completed()
        return state


class LLMOperator(MapFunction):
    """
    LLM 推理任务算子。

    调用真实 LLM 服务进行推理。
    """

    def __init__(
        self,
        llm_base_url: str = "http://11.11.11.7:8903/v1",
        llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
        max_tokens: int = 256,
        stage: int = 1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.max_tokens = max_tokens
        self.stage = stage
        self._hostname = socket.gethostname()
        self._llm_client = None

    def _get_client(self):
        """延迟初始化 LLM 客户端"""
        if self._llm_client is None:
            try:
                from sage.common.components.sage_llm import UnifiedInferenceClient

                self._llm_client = UnifiedInferenceClient.create(
                    control_plane_url=self.llm_base_url,
                    default_llm_model=self.llm_model,
                )
            except Exception as e:
                print(f"[LLMOperator] Client init error: {e}")
        return self._llm_client

    def execute(self, data: TaskState) -> TaskState:
        """执行 LLM 推理"""
        if not isinstance(data, TaskState):
            return data

        state = data
        state.node_id = self._hostname
        state.stage = self.stage
        state.operator_name = f"LLMOperator_{self.stage}"
        state.mark_started()

        try:
            client = self._get_client()
            if client:
                messages = [
                    {"role": "system", "content": "You are a helpful assistant. Be concise."},
                    {"role": "user", "content": state.query},
                ]
                response = client.chat(messages, max_tokens=self.max_tokens)
                state.response = str(response) if not isinstance(response, str) else response
            else:
                # Fallback: 模拟响应
                state.response = f"[Simulated] Response to: {state.query[:50]}..."
            state.success = True
        except Exception as e:
            state.success = False
            state.error = str(e)
            state.response = f"[Error] {str(e)}"

        state.mark_completed()
        return state


class RAGOperator(MapFunction):
    """
    RAG 检索+生成任务算子。

    先使用 Embedding 检索相关文档，再调用 LLM 生成响应。
    """

    def __init__(
        self,
        llm_base_url: str = "http://11.11.11.7:8903/v1",
        llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
        embedding_base_url: str = "http://11.11.11.7:8090/v1",
        embedding_model: str = "BAAI/bge-m3",
        max_tokens: int = 256,
        top_k: int = 3,
        knowledge_base: list[dict] | None = None,
        stage: int = 1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.embedding_base_url = embedding_base_url
        self.embedding_model = embedding_model
        self.max_tokens = max_tokens
        self.top_k = top_k
        self.knowledge_base = knowledge_base or SAMPLE_KNOWLEDGE_BASE
        self.stage = stage
        self._hostname = socket.gethostname()
        self._client = None
        self._initialized = False

    def _initialize(self):
        """延迟初始化客户端"""
        if self._initialized:
            return
        try:
            from sage.common.components.sage_llm import UnifiedInferenceClient

            self._client = UnifiedInferenceClient.create(
                control_plane_url=self.llm_base_url,
                default_llm_model=self.llm_model,
                default_embedding_model=self.embedding_model,
            )
            self._initialized = True
        except Exception as e:
            print(f"[RAGOperator] Init error: {e}")
            self._initialized = True

    def _retrieve(self, query: str) -> list[dict]:
        """检索相关文档"""
        # 简单关键词匹配作为 fallback
        query_lower = query.lower()
        results = []
        for doc in self.knowledge_base:
            content_lower = doc.get("content", "").lower()
            title_lower = doc.get("title", "").lower()
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            title_words = set(title_lower.split())
            overlap = len(query_words & (content_words | title_words))
            if overlap > 0:
                results.append(
                    {
                        "score": overlap,
                        "title": doc.get("title", ""),
                        "content": doc.get("content", ""),
                    }
                )
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[: self.top_k]

    def execute(self, data: TaskState) -> TaskState:
        """执行 RAG 任务"""
        if not isinstance(data, TaskState):
            return data

        state = data
        state.node_id = self._hostname
        state.stage = self.stage
        state.operator_name = f"RAGOperator_{self.stage}"
        state.mark_started()

        self._initialize()

        try:
            # 检索
            retrieval_start = time.time()
            state.retrieved_docs = self._retrieve(state.query)
            retrieval_time = time.time() - retrieval_start
            state.metadata["retrieval_time_ms"] = retrieval_time * 1000

            # 构建上下文
            context_parts = [f"{doc['title']}: {doc['content']}" for doc in state.retrieved_docs]
            state.context = "\n".join(context_parts)

            # 生成
            if self._client:
                messages = [
                    {"role": "system", "content": "Answer based on the context. Be concise."},
                    {
                        "role": "user",
                        "content": f"Context:\n{state.context}\n\nQuestion: {state.query}",
                    },
                ]
                response = self._client.chat(messages, max_tokens=self.max_tokens)
                state.response = str(response) if not isinstance(response, str) else response
            else:
                state.response = f"[Simulated RAG] Based on {len(state.retrieved_docs)} docs."

            state.success = True
        except Exception as e:
            state.success = False
            state.error = str(e)

        state.mark_completed()
        return state


class MetricsSink(SinkFunction):
    """
    指标收集 Sink。

    收集任务指标并聚合统计。
    将结果写入文件以支持 Remote 模式。
    """

    # Metrics 输出目录
    METRICS_OUTPUT_DIR = "/tmp/sage_metrics"

    def __init__(
        self,
        metrics_collector: Any = None,
        verbose: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.metrics_collector = metrics_collector
        self.verbose = verbose
        self.test_mode = os.getenv("SAGE_TEST_MODE") == "true"

        # 本地统计
        self.count = 0
        self.success_count = 0
        self.fail_count = 0
        self.latencies: list[float] = []
        self.node_stats: dict[str, int] = {}

        # 创建唯一的输出文件
        self._start_time = time.time()
        self.instance_id = f"{socket.gethostname()}_{os.getpid()}_{int(time.time() * 1000)}"
        os.makedirs(self.METRICS_OUTPUT_DIR, exist_ok=True)
        self.metrics_output_file = f"{self.METRICS_OUTPUT_DIR}/metrics_{self.instance_id}.jsonl"

        # 写入 header
        self._write_header()

    def _write_header(self) -> None:
        """写入 metrics 文件 header"""
        import json
        import sys

        try:
            header = {
                "type": "header",
                "instance_id": self.instance_id,
                "start_time": self._start_time,
                "hostname": socket.gethostname(),
                "pid": os.getpid(),
            }
            with open(self.metrics_output_file, "w") as f:
                f.write(json.dumps(header) + "\n")
            print(
                f"    [MetricsSink] Initialized: {self.metrics_output_file}",
                file=sys.stderr,
                flush=True,
            )
        except Exception as e:
            print(f"    [MetricsSink] Init error: {e}", file=sys.stderr, flush=True)

    def _write_task_to_file(self, task: TaskState) -> None:
        """将任务结果写入文件"""
        import json

        try:
            record = {
                "type": "task",
                "task_id": task.task_id,
                "success": task.success,
                "node_id": task.node_id,
                "total_latency_ms": getattr(
                    task,
                    "total_latency_ms",
                    task.total_latency * 1000 if hasattr(task, "total_latency") else 0,
                ),
                "timestamp": time.time(),
            }
            with open(self.metrics_output_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            import sys

            print(f"    [MetricsSink] Write error: {e}", file=sys.stderr, flush=True)

    def _write_summary(self) -> None:
        """写入最终摘要"""
        import json
        import sys

        try:
            elapsed = time.time() - self._start_time
            avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
            summary = {
                "type": "summary",
                "total_tasks": self.count,
                "success_count": self.success_count,
                "fail_count": self.fail_count,
                "elapsed_seconds": elapsed,
                "throughput": self.count / elapsed if elapsed > 0 else 0,
                "avg_latency_ms": avg_latency,
                "node_distribution": self.node_stats,
            }
            with open(self.metrics_output_file, "a") as f:
                f.write(json.dumps(summary) + "\n")
            print(
                f"    [MetricsSink] Summary: {self.count} tasks, {self.success_count} success -> {self.metrics_output_file}",
                file=sys.stderr,
                flush=True,
            )
        except Exception as e:
            print(f"    [MetricsSink] Summary error: {e}", file=sys.stderr, flush=True)

    def execute(self, data: TaskState) -> None:
        """收集任务 metrics"""
        if not isinstance(data, TaskState):
            return

        state = data
        self.count += 1

        # 统计成功/失败
        if state.success:
            self.success_count += 1
        else:
            self.fail_count += 1

        # 记录延迟
        latency_ms = getattr(
            state,
            "total_latency_ms",
            state.total_latency * 1000 if hasattr(state, "total_latency") else 0,
        )
        if latency_ms > 0:
            self.latencies.append(latency_ms)

        # 更新节点统计
        if state.node_id:
            self.node_stats[state.node_id] = self.node_stats.get(state.node_id, 0) + 1

        # 写入文件 (Remote 模式可用)
        self._write_task_to_file(state)

        # 记录到共享收集器 (仅 Local 模式有效)
        if self.metrics_collector:
            self.metrics_collector.record_task(state)

        # 详细输出
        if self.verbose and (not self.test_mode or self.count <= 5):
            print(f"[{self.count}] Task: {state.task_id}, Node: {state.node_id}")
            print(f"    Latency: {latency_ms:.1f}ms, Success: {state.success}")
            if hasattr(state, "error") and state.error:
                print(f"    Error: {state.error}")
        elif self.verbose and self.count == 6:
            print("    ... (remaining output suppressed)")

        # Periodic progress report
        if self.count % 100 == 0:
            print(f"[Progress] {self.count} tasks completed")
            if self.node_stats:
                print("  Node distribution:", dict(sorted(self.node_stats.items())))

    def close(self) -> None:
        """关闭时写入摘要"""
        self._write_summary()


# =============================================================================
# Simple RAG Operators - Using Remote Embedding Service
# =============================================================================
# 这些算子使用远程 embedding 服务，不需要本地下载模型
# Embedding 服务: http://{LLM_HOST}:8090/v1
# Embedding 模: BAAI/bge-large-zh-v1.5

# 默认服务配置
LLM_HOST = os.getenv("LLM_HOST", "11.11.11.7")
EMBEDDING_BASE_URL = f"http://{LLM_HOST}:8090/v1"
EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"
LLM_BASE_URL = f"http://{LLM_HOST}:8903/v1"
LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"


def get_remote_embeddings(
    texts: list[str],
    base_url: str = EMBEDDING_BASE_URL,
    model: str = EMBEDDING_MODEL,
) -> list[list[float]] | None:
    """
    使用远程 embedding 服务获取向量。

    Args:
        texts: 要编码的文本列表
        base_url: Embedding 服务地址
        model: Embedding 模型名

    Returns:
        向量列表，或 None（失败时）
    """
    try:
        import requests

        response = requests.post(
            f"{base_url}/embeddings",
            json={
                "input": texts,
                "model": model,
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()

        # 提取 embeddings
        embeddings = [item["embedding"] for item in result["data"]]
        return embeddings
    except Exception as e:
        print(f"[Embedding] Error: {e}")
        return None


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """计算两个向量的余弦相似度"""
    import math

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class SimpleRetriever(MapFunction):
    """
    简单检索器 - 使用远程 Embedding 服务。

    基于余弦相似度检索最相关的文档。
    不依赖 ChromaDB 或本地模型。
    """

    def __init__(
        self,
        embedding_base_url: str = EMBEDDING_BASE_URL,
        embedding_model: str = EMBEDDING_MODEL,
        top_k: int = 5,
        knowledge_base: list[dict] | None = None,
        stage: int = 1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.embedding_base_url = embedding_base_url
        self.embedding_model = embedding_model
        self.top_k = top_k
        self.knowledge_base = knowledge_base or SAMPLE_KNOWLEDGE_BASE
        self.stage = stage
        self._hostname = socket.gethostname()
        self._kb_embeddings: list[list[float]] | None = None
        self._initialized = False

    def _initialize(self):
        """初始化知识库向量"""
        if self._initialized:
            return

        # 获取知识库文档的 embeddings
        texts = [doc.get("content", doc.get("text", "")) for doc in self.knowledge_base]
        self._kb_embeddings = get_remote_embeddings(
            texts,
            base_url=self.embedding_base_url,
            model=self.embedding_model,
        )

        if self._kb_embeddings:
            print(
                f"[SimpleRetriever] Initialized with {len(self._kb_embeddings)} document embeddings"
            )
        else:
            print("[SimpleRetriever] Warning: Failed to get KB embeddings, using keyword fallback")

        self._initialized = True

    def _retrieve_by_embedding(self, query: str) -> list[dict]:
        """使用 embedding 检索"""
        # 获取查询向量
        query_embeddings = get_remote_embeddings(
            [query],
            base_url=self.embedding_base_url,
            model=self.embedding_model,
        )

        if not query_embeddings or not self._kb_embeddings:
            return self._retrieve_by_keyword(query)

        query_vec = query_embeddings[0]

        # 计算相似度
        scored_docs = []
        for i, (doc, doc_vec) in enumerate(zip(self.knowledge_base, self._kb_embeddings)):
            score = cosine_similarity(query_vec, doc_vec)
            scored_docs.append(
                {
                    "id": doc.get("id", str(i)),
                    "title": doc.get("title", ""),
                    "content": doc.get("content", doc.get("text", "")),
                    "score": score,
                }
            )

        # 按相似度排序
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[: self.top_k]

    def _retrieve_by_keyword(self, query: str) -> list[dict]:
        """关键词检索 fallback"""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored_docs = []
        for i, doc in enumerate(self.knowledge_base):
            content = doc.get("content", doc.get("text", "")).lower()
            title = doc.get("title", "").lower()

            # 计算关键词匹配分数
            score = 0
            for word in query_words:
                if len(word) > 2:
                    if word in content:
                        score += 2
                    if word in title:
                        score += 3

            if score > 0:
                scored_docs.append(
                    {
                        "id": doc.get("id", str(i)),
                        "title": doc.get("title", ""),
                        "content": doc.get("content", doc.get("text", "")),
                        "score": score / 10.0,  # 归一化
                    }
                )

        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[: self.top_k]

    def execute(self, data: TaskState) -> TaskState:
        """执行检索"""
        if not isinstance(data, TaskState):
            return data

        state = data
        state.node_id = self._hostname
        state.stage = self.stage
        state.operator_name = f"SimpleRetriever_{self.stage}"
        state.mark_started()

        self._initialize()

        try:
            retrieval_start = time.time()
            state.retrieved_docs = self._retrieve_by_embedding(state.query)
            retrieval_time = time.time() - retrieval_start
            state.metadata["retrieval_time_ms"] = retrieval_time * 1000
            state.metadata["num_retrieved"] = len(state.retrieved_docs)
            state.success = True
        except Exception as e:
            state.success = False
            state.error = str(e)
            state.retrieved_docs = []

        state.mark_completed()
        return state


class SimpleReranker(MapFunction):
    """
        简单重排>> - 使用远程 Embedding 服务。

    #    Supports multiple pipeline types:

        使用 embedding 模型计算更精细的相关性分数。
    """

    def __init__(
        self,
        embedding_base_url: str = EMBEDDING_BASE_URL,
        embedding_model: str = EMBEDDING_MODEL,
        top_k: int = 3,
        stage: int = 2,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.embedding_base_url = embedding_base_url
        self.embedding_model = embedding_model
        self.top_k = top_k
        self.stage = stage
        self._hostname = socket.gethostname()

    def _rerank(self, query: str, docs: list[dict]) -> list[dict]:
        """
        重排文档。

        使用 [query + document] 组合的 embedding 进行更精细的相关性计算。
        """
        if not docs:
            return []

        # 构建 query-doc 对进行评分
        # 使用格式: "Query: {query} Document: {content}"
        pairs = []
        for doc in docs:
            content = doc.get("content", "")[:500]  # 截断
            pair_text = f"Query: {query} Document: {content}"
            pairs.append(pair_text)

        # 获取 query embedding
        query_embedding = get_remote_embeddings(
            [query],
            base_url=self.embedding_base_url,
            model=self.embedding_model,
        )

        # 获取每个 doc 的 embedding
        doc_texts = [doc.get("content", "")[:500] for doc in docs]
        doc_embeddings = get_remote_embeddings(
            doc_texts,
            base_url=self.embedding_base_url,
            model=self.embedding_model,
        )

        if not query_embedding or not doc_embeddings:
            # Fallback: 保持原有排序
            return docs[: self.top_k]

        query_vec = query_embedding[0]

        # 计算新的相关性分数
        reranked = []
        for i, (doc, doc_vec) in enumerate(zip(docs, doc_embeddings)):
            score = cosine_similarity(query_vec, doc_vec)
            reranked.append(
                {
                    **doc,
                    "rerank_score": score,
                }
            )

        # 按新分数排序
        reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return reranked[: self.top_k]

    def execute(self, data: TaskState) -> TaskState:
        """执行重排"""
        if not isinstance(data, TaskState):
            return data

        state = data
        state.node_id = self._hostname
        state.stage = self.stage
        state.operator_name = f"SimpleReranker_{self.stage}"
        state.mark_started()

        try:
            rerank_start = time.time()
            state.retrieved_docs = self._rerank(state.query, state.retrieved_docs)
            rerank_time = time.time() - rerank_start
            state.metadata["rerank_time_ms"] = rerank_time * 1000
            state.metadata["num_reranked"] = len(state.retrieved_docs)
            state.success = True
        except Exception as e:
            state.success = False
            state.error = str(e)

        state.mark_completed()
        return state


class SimplePromptor(MapFunction):
    """
    简单提示构建器。

    将检索的文档和查询组合成 LLM 提示。
    """

    def __init__(
        self,
        stage: int = 3,
        max_context_length: int = 2000,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.stage = stage
        self.max_context_length = max_context_length
        self._hostname = socket.gethostname()

    def execute(self, data: TaskState) -> TaskState:
        """构建提示"""
        if not isinstance(data, TaskState):
            return data

        state = data
        state.node_id = self._hostname
        state.stage = self.stage
        state.operator_name = f"SimplePromptor_{self.stage}"
        state.mark_started()

        try:
            # 构建上下文
            context_parts = []
            total_length = 0

            for i, doc in enumerate(state.retrieved_docs):
                title = doc.get("title", f"Document {i + 1}")
                content = doc.get("content", "")

                doc_text = f"[{title}]\n{content}"
                if total_length + len(doc_text) > self.max_context_length:
                    break

                context_parts.append(doc_text)
                total_length += len(doc_text)

            state.context = "\n\n".join(context_parts)
            state.metadata["context_length"] = len(state.context)
            state.success = True
        except Exception as e:
            state.success = False
            state.error = str(e)
            state.context = ""

        state.mark_completed()
        return state


class SimpleGenerator(MapFunction):
    """
    简单生成器 - 使用远程 LLM 服务。

    基于上下文和查询生成回复。
    """

    def __init__(
        self,
        llm_base_url: str = LLM_BASE_URL,
        llm_model: str = LLM_MODEL,
        max_tokens: int = 256,
        stage: int = 4,
        output_file: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.max_tokens = max_tokens
        self.stage = stage
        self.output_file = output_file
        self._hostname = socket.gethostname()

        #!/usr/bin/env python3
        if self.output_file:
            output_path = Path(self.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

    def _generate(self, query: str, context: str) -> str:
        """调用 LLM 生成回复"""
        try:
            import requests

            messages = [
                {
                    "role": "system",
                    "content": "你是一个helpful--------没有相关信息，请直接说明。",
                },
                {
                    "role": "user",
                    "content": f"上下文:\n{context}\n\n问题: {query}",
                },
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

            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[Generation Error] {str(e)}"

    def _save_response_to_file(self, state: TaskState, gen_time: float) -> None:
        """保存 LLM 回复到指定文件"""
        if self.output_file is None:
            return

        try:
            import json
            from datetime import datetime

            record = {
                "timestamp": datetime.now().isoformat(),
                "task_id": state.task_id,
                "node_id": state.node_id,
                "query": state.query,
                "context": state.context,
                "response": state.response,
                "generation_time_ms": gen_time * 1000,
                "model": self.llm_model,
            }

            # 追加<< JSONL 格式
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        except Exception as e:
            print(f"[Warning] Failed to save response to file: {e}")

    def execute(self, data: TaskState) -> TaskState:
        """执行生成"""
        if not isinstance(data, TaskState):
            return data

        state = data
        state.node_id = self._hostname
        state.stage = self.stage
        state.operator_name = f"SimpleGenerator_{self.stage}"
        state.mark_started()

        try:
            gen_start = time.time()
            state.response = self._generate(state.query, state.context)
            gen_time = time.time() - gen_start
            state.metadata["generation_time_ms"] = gen_time * 1000
            state.success = True
            # 输出到指定文件
            if self.output_file:
                self._save_response_to_file(state, gen_time)

        except Exception as e:
            state.success = False
            state.error = str(e)
            state.response = f"[Error] {str(e)}"

        state.mark_completed()
        return state
