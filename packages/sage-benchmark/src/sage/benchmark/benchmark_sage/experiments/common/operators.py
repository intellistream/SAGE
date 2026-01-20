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

from sage.common.core.functions.filter_function import FilterFunction
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


# 示例查询池 - 包含 ZERO/SINGLE/MULTI 三种复杂度
SAMPLE_QUERIES = [
    # 交替排列以确保每种类型都能覆盖
    # --- Group 1 ---
    "SAGE version",  # ZERO
    "What is SAGE framework and what are its main features?",  # SINGLE
    "Compare LocalEnvironment and RemoteEnvironment in terms of performance and use cases",  # MULTI
    # --- Group 2 ---
    "Python requirements",  # ZERO
    "How do I install SAGE on Ubuntu?",  # SINGLE
    "Analyze the pros and cons of different scheduler strategies in SAGE",  # MULTI
    # --- Group 3 ---
    "License type",  # ZERO
    "What are the different scheduler strategies available?",  # SINGLE
    "What is the relationship between sage-kernel and sage-middleware components?",  # MULTI
    # --- Group 4 ---
    "Default port",  # ZERO
    "How does the memory service work in SAGE?",  # SINGLE
    "Compare FIFO and LoadAware schedulers and their impact on throughput",  # MULTI
    # --- Group 5 ---
    "Ray cluster",  # ZERO
    "What is the role of middleware components?",  # SINGLE
    "Analyze the effects of parallelism settings on pipeline performance",  # MULTI
    # --- Extra SINGLE queries ---
    "How to configure LLM services in SAGE?",
    "What embedding models are supported?",
    "What is the purpose of sage-kernel package?",
    "What vector databases are supported?",
    "What are the CPU node requirements?",
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
            # 不需要额外等待，StopSignal 会在下游 drain 完成后才传播
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
        embedding_model: str = "BAAI/bge-large-en-v1.5",
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

    # Drain 配置：等待远程节点上 Generator 完成处理
    # 问题：StopSignal 可能比数据先到达，而 Generator 还在等待 LLM 响应
    # Adaptive-RAG 等复杂场景可能需要多轮 LLM 调用，P99 可达 150+ 秒
    # 设置 drain_timeout=300s（总等待时间）和 quiet_period=90s（无数据静默期）
    drain_timeout: float = 200
    drain_quiet_period: float = 30

    def __init__(
        self,
        metrics_collector: Any = None,
        verbose: bool = False,
        drain_timeout: float | None = None,
        drain_quiet_period: float | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.metrics_collector = metrics_collector
        self.verbose = verbose
        self.test_mode = os.getenv("SAGE_TEST_MODE") == "true"

        # 允许通过参数覆盖默认 drain 配置
        if drain_timeout is not None:
            self.drain_timeout = drain_timeout
        if drain_quiet_period is not None:
            self.drain_quiet_period = drain_quiet_period

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
# Embedding 模型: BAAI/bge-large-en-v1.5

# 默认服务配置
LLM_HOST = os.getenv("LLM_HOST", "11.11.11.7")
EMBEDDING_BASE_URL = f"http://{LLM_HOST}:8090/v1"
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
LLM_BASE_URL = f"http://{LLM_HOST}:8904/v1"
LLM_MODEL = "Qwen/Qwen2.5-3B-Instruct"


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


# =============================================================================
# FiQA Dataset Components - FAISS + Remote Embedding Service
# =============================================================================
# 使用 FiQA-PL 数据集作为查询源和 VDB 数据源
# 支持 FAISS 索引持久化到 /home/sage/data
# Embedding 服务: http://11.11.11.7:8090/v1
# Embedding 模型: BAAI/bge-large-en-v1.5

# FiQA 数据集配置
FIQA_DATA_DIR = "/home/sage/data/FiQA-PL"
FIQA_INDEX_DIR = "/home/sage/data"


class FiQADataLoader:
    """FiQA 数据集加载器 (单例模式，避免重复加载)"""

    _queries: list[dict] | None = None
    _corpus: list[dict] | None = None

    @classmethod
    def load_queries(cls, data_dir: str = FIQA_DATA_DIR) -> list[dict]:
        """加载 FiQA 查询数据"""
        if cls._queries is not None:
            return cls._queries

        import pandas as pd

        queries_path = Path(data_dir) / "queries" / "test-00000-of-00001.parquet"
        if not queries_path.exists():
            raise FileNotFoundError(f"FiQA queries not found: {queries_path}")

        df = pd.read_parquet(queries_path)
        cls._queries = [{"id": row["_id"], "text": row["text"]} for _, row in df.iterrows()]
        print(f"[FiQA] Loaded {len(cls._queries)} queries from {queries_path}")
        return cls._queries

    @classmethod
    def load_corpus(cls, data_dir: str = FIQA_DATA_DIR) -> list[dict]:
        """加载 FiQA 语料库"""
        if cls._corpus is not None:
            return cls._corpus

        import pandas as pd

        corpus_path = Path(data_dir) / "corpus" / "test-00000-of-00001.parquet"
        if not corpus_path.exists():
            raise FileNotFoundError(f"FiQA corpus not found: {corpus_path}")

        df = pd.read_parquet(corpus_path)
        cls._corpus = [
            {"id": row["_id"], "text": row["text"], "title": row.get("title", "")}
            for _, row in df.iterrows()
        ]
        print(f"[FiQA] Loaded {len(cls._corpus)} documents from {corpus_path}")
        return cls._corpus

    @classmethod
    def clear_cache(cls):
        """清除缓存"""
        cls._queries = None
        cls._corpus = None


class FiQATaskSource(SourceFunction):
    """
    FiQA 数据集任务生成源。

    从 FiQA 数据集循环读取查询，当 task 数量超过 query 数量时循环读取。
    """

    def __init__(
        self,
        num_tasks: int = 100,
        data_dir: str = FIQA_DATA_DIR,
        task_complexity: str = "medium",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.num_tasks = num_tasks
        self.data_dir = data_dir
        self.task_complexity = task_complexity
        self.current_index = 0
        self._queries: list[dict] | None = None

    def _load_queries(self):
        """延迟加载查询"""
        if self._queries is None:
            self._queries = FiQADataLoader.load_queries(self.data_dir)

    def execute(self, data=None) -> TaskState | StopSignal:
        """生成下一个任务 (循环读取)"""
        if self.current_index >= self.num_tasks:
            # 不需要额外等待，StopSignal 会在下游 drain 完成后才传播
            return StopSignal("All tasks generated")
        self.logger.info(f"[FiQATaskSource] Generating task {self.current_index + 1}/{self.num_tasks}")
        self._load_queries()
        assert self._queries is not None

        # 循环读取 query
        query_idx = self.current_index % len(self._queries)
        query_data = self._queries[query_idx]
        self.current_index += 1
        self.logger.info(f"[FiQATaskSource] Generated task {self.current_index} with query ID {query_data['id']}")
        state = TaskState(
            task_id=f"fiqa_{self.current_index:05d}",
            query=query_data["text"],
            created_time=time.time(),
            metadata={
                "complexity": self.task_complexity,
                "query_id": query_data["id"],
                "query_idx": query_idx,
            },
        )

        return state


class FiQAFAISSRetriever(MapFunction):
    """
    FiQA FAISS 检索器 - 使用远程 Embedding 服务 + FAISS 持久化索引。

    特性:
    - 使用远程 embedding 服务 (http://11.11.11.7:8090/v1)
    - FAISS FlatIndex (IndexFlatIP) 用于精确检索
    - 索引持久化到 /home/sage/data
    - 使用 call_service 调用服务化的 VDB
    """

    def __init__(
        self,
        embedding_base_url: str = EMBEDDING_BASE_URL,
        embedding_model: str = EMBEDDING_MODEL,
        data_dir: str = FIQA_DATA_DIR,
        index_dir: str = FIQA_INDEX_DIR,
        top_k: int = 5,
        stage: int = 1,
        use_service: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.embedding_base_url = embedding_base_url
        self.embedding_model = embedding_model
        self.data_dir = data_dir
        self.index_dir = index_dir
        self.top_k = top_k
        self.stage = stage
        self.use_service = use_service
        self._hostname = socket.gethostname()

        # 延迟初始化
        self._initialized = False
        self._faiss_index = None
        self._documents: list[dict] = []
        self._dimension: int | None = None

    def _get_embeddings(self, texts: list[str]) -> list[list[float]] | None:
        """使用远程 embedding 服务获取向量"""
        return get_remote_embeddings(texts, self.embedding_base_url, self.embedding_model)

    def _get_index_paths(self) -> tuple[Path, Path]:
        """获取索引和文档文件路径"""
        index_path = Path(self.index_dir) / "fiqa_faiss.index"
        docs_path = Path(self.index_dir) / "fiqa_documents.jsonl"
        return index_path, docs_path

    def _initialize(self):
        """初始化 FAISS 索引"""
        if self._initialized:
            return

        import json

        import faiss
        import numpy as np

        index_path, docs_path = self._get_index_paths()

        # 尝试加载已有索引
        if index_path.exists() and docs_path.exists():
            print(f"[FiQARetriever] Loading existing FAISS index from {index_path}")
            self._faiss_index = faiss.read_index(str(index_path))

            # 加载文档
            self._documents = []
            with open(docs_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        self._documents.append(json.loads(line))

            print(f"[FiQARetriever] Loaded {self._faiss_index.ntotal} vectors, {len(self._documents)} docs")
            self._initialized = True
            return

        # 构建新索引
        print(f"[FiQARetriever] Building new FAISS index...")
        corpus = FiQADataLoader.load_corpus(self.data_dir)
        self._documents = corpus

        # 分批获取 embeddings (避免超时)
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(corpus), batch_size):
            batch = corpus[i : i + batch_size]
            texts = [doc["text"][:512] for doc in batch]  # 截断过长文本
            embeddings = self._get_embeddings(texts)
            if embeddings is None:
                raise RuntimeError(f"Failed to get embeddings for batch {i // batch_size}")
            all_embeddings.extend(embeddings)
            print(f"[FiQARetriever] Embedded {min(i + batch_size, len(corpus))}/{len(corpus)} docs")

        # 创建 FAISS 索引 (FlatIP for cosine similarity with normalized vectors)
        vectors = np.array(all_embeddings, dtype=np.float32)

        # 归一化向量 (用于余弦相似度)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / (norms + 1e-8)

        self._dimension = vectors.shape[1]
        self._faiss_index = faiss.IndexFlatIP(self._dimension)
        self._faiss_index.add(vectors)

        # 保存索引和文档
        Path(self.index_dir).mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._faiss_index, str(index_path))

        with open(docs_path, "w", encoding="utf-8") as f:
            for doc in self._documents:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        print(f"[FiQARetriever] Built and saved index: {self._faiss_index.ntotal} vectors")
        self._initialized = True

    def _search(self, query: str) -> list[dict]:
        """使用 FAISS 检索"""
        import numpy as np

        # 获取查询向量
        query_embeddings = self._get_embeddings([query])
        if not query_embeddings:
            return []

        query_vec = np.array(query_embeddings[0], dtype=np.float32)

        # 归一化
        query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        query_vec = query_vec.reshape(1, -1)

        # FAISS 检索
        scores, indices = self._faiss_index.search(query_vec, self.top_k)

        # 构建结果
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._documents):
                doc = self._documents[idx]
                results.append({
                    "id": doc.get("id", str(idx)),
                    "title": doc.get("title", ""),
                    "content": doc.get("text", ""),
                    "score": float(score),
                })

        return results

    def execute(self, data: TaskState) -> TaskState:
        """执行检索"""
        if not isinstance(data, TaskState):
            return data

        state = data
        state.node_id = self._hostname
        state.stage = self.stage
        state.operator_name = f"FiQARetriever_{self.stage}"
        state.mark_started()

        try:
            if self.use_service:
                # 使用服务化的 VDB
                retrieval_start = time.time()
                results = self.call_service(
                    "fiqa_vdb",
                    method="search",
                    query=state.query,
                    top_k=self.top_k,
                    timeout=120.0,  # 首次调用需要加载索引，设置较长超时
                )
                state.retrieved_docs = results if results else []
                retrieval_time = time.time() - retrieval_start
            else:
                # 本地 FAISS 检索
                self._initialize()
                retrieval_start = time.time()
                state.retrieved_docs = self._search(state.query)
                retrieval_time = time.time() - retrieval_start

            state.metadata["retrieval_time_ms"] = retrieval_time * 1000
            state.metadata["num_retrieved"] = len(state.retrieved_docs)
            state.success = True

            # 打印检索结果
            print(f"\n{'='*60}")
            print(f"[Retriever] Task: {state.task_id} | Query: {state.query[:50]}...")
            self.logger.info(f"[Retriever] Retrieved {len(state.retrieved_docs)} docs in {retrieval_time*1000:.1f}ms")
            self.logger.info(f"docs are {state.retrieved_docs}")
            print(f"[Retriever] Retrieved {len(state.retrieved_docs)} docs in {retrieval_time*1000:.1f}ms")
            for i, doc in enumerate(state.retrieved_docs[:3]):
                score = doc.get('score', 0)
                text = doc.get('content', doc.get('text', ''))[:100]
                print(f"  [{i+1}] (score={score:.3f}) {text}...")
            print(f"{'='*60}\n")

            # 保存检索结果到文件
            self._save_retrieval_result(state, retrieval_time)

        except Exception as e:
            state.success = False
            state.error = str(e)
            state.retrieved_docs = []
            import traceback
            traceback.print_exc()

        state.mark_completed()
        return state

    def _save_retrieval_result(self, state: TaskState, retrieval_time: float) -> None:
        """保存检索结果到文件"""
        try:
            import json
            from datetime import datetime
            from pathlib import Path

            output_dir = Path("/home/sage/data/rag_outputs")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "retrieval_results.jsonl"

            record = {
                "timestamp": datetime.now().isoformat(),
                "task_id": state.task_id,
                "node_id": state.node_id,
                "query": state.query,
                "num_docs": len(state.retrieved_docs),
                "retrieval_time_ms": retrieval_time * 1000,
                "docs": state.retrieved_docs[:5],  # 只保存 top 5
            }
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[Warning] Failed to save retrieval result: {e}")


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

            # 记录到日志
            self.logger.info(
                f"[Generator] task_id={state.task_id}, query={state.query[:50]}..., "
                f"response_len={len(state.response)}, gen_time={gen_time*1000:.1f}ms"
            )
            self.logger.debug(f"[Generator] Full response: {state.response[:500]}")

            # 输出到指定文件
            if self.output_file:
                self._save_response_to_file(state, gen_time)

        except Exception as e:
            state.success = False
            state.error = str(e)
            state.response = f"[Error] {str(e)}"

        state.mark_completed()
        return state


# ============================================================================
# Adaptive-RAG Operators
# ============================================================================

try:
    from .models import (
        AdaptiveRAGQueryData,
        AdaptiveRAGResultData,
        ClassificationResult,
        IterativeState,
        QueryComplexityLevel,
    )
except ImportError:
    from models import (
        AdaptiveRAGQueryData,
        AdaptiveRAGResultData,
        ClassificationResult,
        IterativeState,
        QueryComplexityLevel,
    )


class AdaptiveRAGQuerySource(SourceFunction):
    """Adaptive-RAG 查询数据源"""

    def __init__(self, queries: list[str], delay: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.queries = queries
        self.delay = delay
        self.counter = 0

    def execute(self, data=None) -> AdaptiveRAGQueryData | StopSignal:
        if self.counter >= len(self.queries):
            # 不需要额外等待，StopSignal 会在下游 drain 完成后才传播
            return StopSignal("All queries generated")
        query = self.queries[self.counter]
        self.counter += 1
        if self.delay > 0:
            time.sleep(self.delay)
        import sys
        print(f"[Source] [{self.counter}/{len(self.queries)}]: {query}", file=sys.stderr, flush=True)
        return AdaptiveRAGQueryData(query=query, metadata={"index": self.counter - 1})


class QueryClassifier(MapFunction):
    """
    查询复杂度分类器

    支持三种分类方式:
    - rule: 基于关键词的规则分类
    - llm: 使用 LLM 进行分类
    - hybrid: 先规则，不确定时用 LLM

    复杂度定义 (参考 Adaptive-RAG 论文):
    - ZERO (A): 简单事实查询，LLM 可直接回答，无需检索
    - SINGLE (B): 需要单次检索的查询
    - MULTI (C): 需要多跳推理或迭代检索的复杂查询
    """

    # MULTI: 多跳推理、比较分析、因果关系
    MULTI_KEYWORDS = [
        "compare", "contrast", "analyze", "relationship", "between",
        "pros and cons", "advantages and disadvantages", "impact", "effects",
        "differences", "similarities", "how does .* affect", "why does",
        "what factors", "explain the relationship", "connection between",
    ]

    # SINGLE: 需要检索但单步可完成
    SINGLE_KEYWORDS = [
        "what is", "who is", "when was", "where is", "how to",
        "define", "describe", "explain", "how does .* work",
        "what are the", "list the", "name the",
    ]

    # ZERO: 常识性问题，LLM 可直接回答
    ZERO_INDICATORS = [
        # 短查询 (≤3 words)
        # 常见知识问题
        "capital of", "meaning of", "synonym", "antonym",
        "what year", "how many", "true or false",
    ]

    def __init__(
        self,
        classifier_type: str = "rule",
        llm_base_url: str = "http://11.11.11.7:8903/v1",
        llm_model: str = "Qwen/Qwen2.5-7B-Instruct",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.classifier_type = classifier_type
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model

    def _classify_by_rule(self, query: str) -> ClassificationResult:
        import re
        query_lower = query.lower()
        word_count = len(query.split())

        # 1. 检查 ZERO 指示词或短查询
        if word_count <= 3:
            return ClassificationResult(
                complexity=QueryComplexityLevel.ZERO,
                confidence=0.8,
                reasoning=f"Very short query ({word_count} words)"
            )

        for indicator in self.ZERO_INDICATORS:
            if indicator in query_lower:
                return ClassificationResult(
                    complexity=QueryComplexityLevel.ZERO,
                    confidence=0.7,
                    reasoning=f"ZERO indicator: '{indicator}'"
                )

        # 2. 检查 MULTI 关键词 (优先级高于 SINGLE)
        for keyword in self.MULTI_KEYWORDS:
            if re.search(keyword, query_lower):
                return ClassificationResult(
                    complexity=QueryComplexityLevel.MULTI,
                    confidence=0.8,
                    reasoning=f"MULTI keyword: '{keyword}'"
                )

        # 3. 检查 SINGLE 关键词
        for keyword in self.SINGLE_KEYWORDS:
            if re.search(keyword, query_lower):
                return ClassificationResult(
                    complexity=QueryComplexityLevel.SINGLE,
                    confidence=0.8,
                    reasoning=f"SINGLE keyword: '{keyword}'"
                )

        # 4. 基于长度的默认分类
        if word_count <= 8:
            return ClassificationResult(
                complexity=QueryComplexityLevel.ZERO,
                confidence=0.5,
                reasoning=f"Short query without special keywords ({word_count} words)"
            )
        elif word_count <= 20:
            return ClassificationResult(
                complexity=QueryComplexityLevel.SINGLE,
                confidence=0.5,
                reasoning=f"Medium query ({word_count} words)"
            )
        else:
            return ClassificationResult(
                complexity=QueryComplexityLevel.MULTI,
                confidence=0.5,
                reasoning=f"Long query ({word_count} words)"
            )

    def _classify_by_llm(self, query: str) -> ClassificationResult:
        """使用 LLM 进行复杂度分类"""
        import requests

        prompt = f'''Classify the following query into one of three complexity levels:

A (ZERO): Simple factual questions that can be answered directly from common knowledge, no retrieval needed.
B (SINGLE): Questions requiring a single retrieval step to find relevant information.
C (MULTI): Complex questions requiring multi-hop reasoning, comparison, or iterative retrieval.

Query: "{query}"

Respond with only the letter (A, B, or C) and a brief reason.
Format: [LETTER]: [reason]'''

        try:
            response = requests.post(
                f"{self.llm_base_url}/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                    "temperature": 0.1,
                },
                timeout=30,
            )
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"].strip()
                # Parse response: "A: reason" or "B: reason" or "C: reason"
                if content.startswith("A"):
                    return ClassificationResult(
                        complexity=QueryComplexityLevel.ZERO,
                        confidence=0.9,
                        reasoning=f"LLM: {content}"
                    )
                elif content.startswith("B"):
                    return ClassificationResult(
                        complexity=QueryComplexityLevel.SINGLE,
                        confidence=0.9,
                        reasoning=f"LLM: {content}"
                    )
                elif content.startswith("C"):
                    return ClassificationResult(
                        complexity=QueryComplexityLevel.MULTI,
                        confidence=0.9,
                        reasoning=f"LLM: {content}"
                    )
        except Exception as e:
            print(f"[Classifier] LLM error: {e}, falling back to rule-based")

        # Fallback to rule-based
        return self._classify_by_rule(query)

    def execute(self, data: AdaptiveRAGQueryData) -> AdaptiveRAGQueryData:
        if self.classifier_type == "llm":
            classification = self._classify_by_llm(data.query)
        elif self.classifier_type == "hybrid":
            classification = self._classify_by_rule(data.query)
            if classification.confidence < 0.7:
                classification = self._classify_by_llm(data.query)
        else:
            classification = self._classify_by_rule(data.query)

        data.classification = classification
        import sys
        print(f"[Classify] {data.query[:50]}... -> {classification.complexity.name} ({classification.reasoning})", file=sys.stderr, flush=True)
        return data


class ZeroComplexityFilter(FilterFunction):
    """过滤: 只保留 ZERO 复杂度的查询"""
    def execute(self, data: AdaptiveRAGQueryData) -> bool:
        if not isinstance(data, AdaptiveRAGQueryData) or data.classification is None:
            return False
        is_match = data.classification.complexity == QueryComplexityLevel.ZERO
        if is_match:
            print(f"  ZERO branch: {data.query[:50]}...")
        return is_match


class SingleComplexityFilter(FilterFunction):
    """过滤: 只保留 SINGLE 复杂度的查询"""
    def execute(self, data: AdaptiveRAGQueryData) -> bool:
        if not isinstance(data, AdaptiveRAGQueryData) or data.classification is None:
            return False
        is_match = data.classification.complexity == QueryComplexityLevel.SINGLE
        if is_match:
            print(f"  SINGLE branch: {data.query[:50]}...")
        return is_match


class MultiComplexityFilter(FilterFunction):
    """过滤: 只保留 MULTI 复杂度的查询"""
    def execute(self, data: AdaptiveRAGQueryData) -> bool:
        if not isinstance(data, AdaptiveRAGQueryData) or data.classification is None:
            return False
        is_match = data.classification.complexity == QueryComplexityLevel.MULTI
        if is_match:
            print(f"  MULTI branch: {data.query[:50]}...")
        return is_match


class NoRetrievalStrategy(MapFunction):
    """策略 A: 无检索 - 直接 LLM 生成"""

    def __init__(self, llm_base_url: str = "http://11.11.11.7:8903/v1", llm_model: str = "Qwen/Qwen2.5-7B-Instruct", max_tokens: int = 512, **kwargs):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.max_tokens = max_tokens

    def _generate(self, query: str) -> str:
        import requests
        try:
            response = requests.post(f"{self.llm_base_url}/chat/completions", json={"model": self.llm_model, "messages": [{"role": "user", "content": query}], "max_tokens": self.max_tokens, "temperature": 0.7}, timeout=60)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[Generation Error] {str(e)}"

    def execute(self, data: AdaptiveRAGQueryData) -> AdaptiveRAGResultData:
        start_time = time.time()
        print(f"  🔵 NoRetrieval: {data.query[:50]}...")
        answer = self._generate(data.query)
        return AdaptiveRAGResultData(query=data.query, answer=answer, strategy_used="no_retrieval", complexity="ZERO", retrieval_steps=0, processing_time_ms=(time.time() - start_time) * 1000)


class SingleRetrievalStrategy(MapFunction):
    """策略 B: 单次检索 + 生成（服务化向量检索版本）

    使用 self.call_service("embedding") 和 self.call_service("vector_db") 进行真正的向量检索。
    使用 self.call_service("llm") 进行生成。
    """

    def __init__(self, llm_base_url: str = "http://11.11.11.7:8903/v1", llm_model: str = "Qwen/Qwen2.5-7B-Instruct", max_tokens: int = 512, top_k: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.max_tokens = max_tokens
        self.top_k = top_k
        self._hostname = socket.gethostname()

    def _retrieve_via_service(self, query: str) -> list[dict]:
        """使用服务进行向量检索"""
        import numpy as np
        try:
            # RPC: call_service(name, *args, **kwargs) calls service.process(*args, **kwargs)
            query_embeddings = self.call_service("embedding", texts=[query])
            if not query_embeddings:
                print(f"    ⚠️ Failed to get query embedding")
                return []

            query_vec = np.array(query_embeddings[0], dtype=np.float32)

            # RPC: call vector_db.process(query_vec, k=self.top_k)
            results = self.call_service("vector_db", query_vec=query_vec, k=self.top_k)

            # Convert to document format
            docs = []
            for score, metadata in results:
                docs.append({
                    "id": metadata.get("id", ""),
                    "content": metadata.get("content", metadata.get("text", "")),
                    "score": float(score),
                })
            return docs

        except Exception as e:
            print(f"    ⚠️ Service retrieval error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _generate_via_service(self, query: str, context: str) -> str:
        """使用 LLM 服务进行生成"""
        try:
            messages = [
                {"role": "system", "content": "Answer based on the provided context."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
            ]
            # RPC: call llm.process(messages, max_tokens, temperature)
            # timeout=120 to avoid service call timeout for LLM inference
            return self.call_service("llm", messages=messages, max_tokens=self.max_tokens, temperature=0.7, timeout=120)
        except Exception as e:
            # Fallback to direct request
            import requests
            try:
                response = requests.post(f"{self.llm_base_url}/chat/completions", json={"model": self.llm_model, "messages": [{"role": "system", "content": "Answer based on the provided context."}, {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}], "max_tokens": self.max_tokens, "temperature": 0.7}, timeout=60)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except Exception as e2:
                return f"[Generation Error] {str(e2)}"

    def execute(self, data: AdaptiveRAGQueryData) -> AdaptiveRAGResultData:
        start_time = time.time()
        print(f"  🟡 SingleRetrieval[{self._hostname}]: {data.query[:50]}...")
        docs = self._retrieve_via_service(data.query)
        context = "\n".join([f"[Doc {i+1}]: {d['content']}" for i, d in enumerate(docs)]) or "No relevant documents found."
        answer = self._generate_via_service(data.query, context)
        return AdaptiveRAGResultData(query=data.query, answer=answer, strategy_used="single_retrieval", complexity="SINGLE", retrieval_steps=len(docs), processing_time_ms=(time.time() - start_time) * 1000)


class IterativeRetrievalInit(MapFunction):
    """策略 C: 迭代检索初始化"""
    def execute(self, data: AdaptiveRAGQueryData) -> IterativeState:
        print(f"  🔴 IterativeRetrieval Init: {data.query[:50]}...")
        return IterativeState(original_query=data.query, current_query=data.query, accumulated_docs=[], reasoning_chain=[], iteration=0, is_complete=False, start_time=time.time(), classification=data.classification)


class IterativeRetriever(MapFunction):
    """迭代检索算子（服务化向量检索版本）

    使用 self.call_service("embedding") 和 self.call_service("vector_db") 进行真正的向量检索。
    """

    def __init__(self, top_k: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.top_k = top_k
        self._hostname = socket.gethostname()

    def _retrieve_via_service(self, query: str) -> list[dict]:
        """使用服务进行向量检索"""
        import numpy as np
        try:
            # RPC: call embedding.process(texts=[query])
            query_embeddings = self.call_service("embedding", texts=[query])
            if not query_embeddings:
                print(f"      ⚠️ Failed to get query embedding")
                return []

            query_vec = np.array(query_embeddings[0], dtype=np.float32)

            # RPC: call vector_db.process(query_vec, k=self.top_k)
            results = self.call_service("vector_db", query_vec=query_vec, k=self.top_k)

            # Convert to document format
            docs = []
            for score, metadata in results:
                docs.append({
                    "id": metadata.get("id", ""),
                    "content": metadata.get("content", metadata.get("text", "")),
                    "score": float(score),
                })
            return docs

        except Exception as e:
            print(f"      ⚠️ Service retrieval error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def execute(self, state: IterativeState) -> IterativeState:
        if state.is_complete:
            return state

        new_docs = self._retrieve_via_service(state.current_query)
        state.accumulated_docs.extend(new_docs)
        state.reasoning_chain.append(f"[Retrieve] Query: '{state.current_query[:30]}' -> {len(new_docs)} docs")
        print(f"    📚 Retrieve[{self._hostname}][{state.iteration}]: {len(new_docs)} docs")
        return state


class IterativeReasoner(MapFunction):
    """迭代推理算子（服务化 LLM 版本）"""

    def __init__(self, llm_base_url: str = "http://11.11.11.7:8903/v1", llm_model: str = "Qwen/Qwen2.5-7B-Instruct", max_iterations: int = 3, min_docs: int = 5, **kwargs):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.max_iterations = max_iterations
        self.min_docs = min_docs
        self._hostname = socket.gethostname()

    def _llm_call_via_service(self, messages: list[dict]) -> str:
        """使用 LLM 服务进行调用"""
        try:
            # RPC: call llm.process(messages, max_tokens, temperature)
            # timeout=120 to avoid service call timeout for LLM inference
            return self.call_service("llm", messages=messages, max_tokens=256, temperature=0.7, timeout=120)
        except Exception:
            # Fallback to direct request
            import requests
            try:
                response = requests.post(f"{self.llm_base_url}/chat/completions", json={"model": self.llm_model, "messages": messages, "max_tokens": 256, "temperature": 0.7}, timeout=60)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                return f"[LLM Error] {str(e)}"

    def execute(self, state: IterativeState) -> IterativeState:
        if state.is_complete:
            return state
        state.iteration += 1
        if state.iteration >= self.max_iterations or len(state.accumulated_docs) >= self.min_docs:
            state.is_complete = True
            state.reasoning_chain.append(f"[Reason] Complete (docs={len(state.accumulated_docs)})")
            print(f"    🧠 Reason[{self._hostname}][{state.iteration}]: COMPLETE")
            return state
        context_so_far = "\n".join([f"- {d['content']}" for d in state.accumulated_docs[-3:]])
        messages = [{"role": "system", "content": "Generate a follow-up search query. Reply with ONLY the query."}, {"role": "user", "content": f"Original: {state.original_query}\n\nContext:\n{context_so_far}\n\nFollow-up query:"}]
        new_query = self._llm_call_via_service(messages).strip()
        state.current_query = new_query
        state.reasoning_chain.append(f"[Reason] Next query = '{new_query[:40]}'")
        print(f"    🧠 Reason[{self._hostname}][{state.iteration}]: Next -> '{new_query[:30]}...'")
        return state


class FinalSynthesizer(MapFunction):
    """综合生成算子（服务化 LLM 版本）"""

    def __init__(self, llm_base_url: str = "http://11.11.11.7:8903/v1", llm_model: str = "Qwen/Qwen2.5-7B-Instruct", **kwargs):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self._hostname = socket.gethostname()

    def _llm_call_via_service(self, messages: list[dict]) -> str:
        """使用 LLM 服务进行调用"""
        try:
            # RPC: call llm.process(messages, max_tokens, temperature)
            # timeout=120 to avoid service call timeout for LLM inference
            return self.call_service("llm", messages=messages, max_tokens=512, temperature=0.7, timeout=120)
        except Exception:
            # Fallback to direct request
            import requests
            try:
                response = requests.post(f"{self.llm_base_url}/chat/completions", json={"model": self.llm_model, "messages": messages, "max_tokens": 512, "temperature": 0.7}, timeout=60)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                return f"[LLM Error] {str(e)}"

    def execute(self, state: IterativeState) -> AdaptiveRAGResultData:
        context = "\n".join([f"[Doc {i+1}]: {d['content']}" for i, d in enumerate(state.accumulated_docs)])
        chain_text = "\n".join(state.reasoning_chain)
        messages = [{"role": "system", "content": "Synthesize all information to answer comprehensively."}, {"role": "user", "content": f"Question: {state.original_query}\n\nReasoning:\n{chain_text}\n\nContext:\n{context}\n\nAnswer:"}]
        answer = self._llm_call_via_service(messages)
        print(f"    ✨ Synthesize[{self._hostname}]: Generated answer ({len(answer)} chars)")
        return AdaptiveRAGResultData(query=state.original_query, answer=answer, strategy_used="iterative_retrieval", complexity="MULTI", retrieval_steps=state.iteration, processing_time_ms=(time.time() - state.start_time) * 1000)


class AdaptiveRAGResultSink(SinkFunction):
    """Adaptive-RAG 结果收集器 (兼容 MetricsSink 格式)"""

    METRICS_OUTPUT_DIR = "/tmp/sage_metrics"  # 与 MetricsSink 使用相同目录
    _all_results: list[AdaptiveRAGResultData] = []

    # Drain 配置：等待远程节点上 Generator 完成处理
    # 问题：StopSignal 可能比数据先到达，而 Generator 还在等待 LLM 响应
    # Adaptive-RAG 等复杂场景可能需要多轮 LLM 调用，P99 可达 150+ 秒
    # 设置 drain_timeout=300s（总等待时间）和 quiet_period=90s（无数据静默期）
    # drain_timeout: float = 300.0
    # drain_quiet_period: float = 90.0

    def __init__(self, branch_name: str = "", **kwargs):
        super().__init__(**kwargs)
        self.branch_name = branch_name
        self.count = 0
        self.instance_id = f"{socket.gethostname()}_{os.getpid()}_{int(time.time() * 1000)}"
        os.makedirs(self.METRICS_OUTPUT_DIR, exist_ok=True)
        # 使用 metrics_ 前缀以便 run() 的 _collect_metrics_from_files() 能找到
        self.metrics_output_file = f"{self.METRICS_OUTPUT_DIR}/metrics_{self.instance_id}.jsonl"

    def _write_to_file(self, data: AdaptiveRAGResultData) -> None:
        import json
        try:
            # 写入 MetricsSink 兼容格式（包含 type, success, total_latency_ms 等字段）
            record = {
                "type": "task",
                "success": True,
                "total_latency_ms": data.processing_time_ms,
                "node_id": socket.gethostname(),
                # Adaptive-RAG 特有字段
                "query": data.query,
                "answer": data.answer,
                "strategy_used": data.strategy_used,
                "complexity": data.complexity,
                "retrieval_steps": data.retrieval_steps,
                "branch_name": self.branch_name,
                "timestamp": time.time(),
            }
            with open(self.metrics_output_file, "a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            import sys
            print(f"[ResultSink] Write error: {e}", file=sys.stderr, flush=True)

    def execute(self, data: AdaptiveRAGResultData):
        self.count += 1
        AdaptiveRAGResultSink._all_results.append(data)
        self._write_to_file(data)
        import sys
        print(f"\n  [{self.branch_name}] Result #{self.count}: {data.query[:40]}... -> {data.strategy_used}", file=sys.stderr, flush=True)
        return data

    @classmethod
    def get_all_results(cls) -> list[AdaptiveRAGResultData]:
        return cls._all_results.copy()

    @classmethod
    def clear_results(cls):
        cls._all_results.clear()


# =============================================================================
# 为 Adaptive-RAG 类设置固定的 __module__，确保 Ray 序列化/反序列化一致性
# Worker 节点通过 common.operators 导入，所以需要设置 __module__ 为 common.operators
# =============================================================================
_ADAPTIVE_RAG_CLASSES = [
    AdaptiveRAGQuerySource,
    QueryClassifier,
    ZeroComplexityFilter,
    SingleComplexityFilter,
    MultiComplexityFilter,
    NoRetrievalStrategy,
    SingleRetrievalStrategy,
    IterativeRetrievalInit,
    IterativeRetriever,
    IterativeReasoner,
    FinalSynthesizer,
    AdaptiveRAGResultSink,
]

for _cls in _ADAPTIVE_RAG_CLASSES:
    _cls.__module__ = "common.operators"


# =============================================================================
# Service-Based RAG Operators
# =============================================================================
# These operators use registered services via self.call_service()
# to avoid distributed access issues (each worker loading its own model/index).
#
# Services are registered in pipeline.py:
#   - embedding: EmbeddingService for vectorization
#   - vector_db: SageDBService for knowledge base retrieval
#   - llm: LLMService for generation
#
# Usage:
#   from .pipeline import register_all_services
#   register_all_services(env, config)
#   env.from_source(...).map(ServiceRetriever, ...).map(ServiceGenerator, ...)


class ServiceRetriever(MapFunction):
    """
    Service-based retriever using registered vector_db service.

    Uses self.call_service("vector_db") for retrieval.
    Avoids each worker loading its own embedding model and knowledge base.
    """

    def __init__(
        self,
        top_k: int = 5,
        stage: int = 1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.top_k = top_k
        self.stage = stage
        self._hostname = socket.gethostname()

    def execute(self, data: TaskState) -> TaskState:
        """Execute retrieval using vector_db service"""
        if not isinstance(data, TaskState):
            return data

        state = data
        state.node_id = self._hostname
        state.stage = self.stage
        state.operator_name = f"ServiceRetriever_{self.stage}"
        state.mark_started()

        try:
            retrieval_start = time.time()

            # Get embedding service and vector_db service
            embedding_service = self.call_service("embedding")
            vector_db = self.call_service("vector_db")

            # Embed query
            query_embeddings = embedding_service.embed([state.query])
            if not query_embeddings:
                raise ValueError("Failed to get query embedding")

            import numpy as np
            query_vec = np.array(query_embeddings[0], dtype=np.float32)

            # Search vector_db
            results = vector_db.search(query_vec, top_k=self.top_k)

            # Convert results to document format
            state.retrieved_docs = []
            for score, metadata in results:
                state.retrieved_docs.append({
                    "id": metadata.get("id", ""),
                    "title": metadata.get("title", ""),
                    "content": metadata.get("content", metadata.get("text", "")),
                    "score": float(score),
                })

            retrieval_time = time.time() - retrieval_start
            state.metadata["retrieval_time_ms"] = retrieval_time * 1000
            state.metadata["num_retrieved"] = len(state.retrieved_docs)
            state.success = True

            # 打印检索结果
            print(f"\n{'='*60}")
            print(f"[Retriever] Task: {state.task_id} | Query: {state.query[:50]}...")
            print(f"[Retriever] Retrieved {len(state.retrieved_docs)} docs in {retrieval_time*1000:.1f}ms")
            for i, doc in enumerate(state.retrieved_docs[:3]):
                score = doc.get('score', 0)
                text = doc.get('content', doc.get('text', ''))[:100]
                print(f"  [{i+1}] (score={score:.3f}) {text}...")
            print(f"{'='*60}\n")

            # 保存检索结果到文件
            self._save_retrieval_result(state, retrieval_time)

        except Exception as e:
            state.success = False
            state.error = str(e)
            state.retrieved_docs = []
            import traceback
            traceback.print_exc()

        state.mark_completed()
        return state


class ServiceReranker(MapFunction):
    """
    Service-based reranker using registered embedding service.

    Uses self.call_service("embedding") for reranking.
    Computes more refined relevance scores using query-document similarity.
    """

    def __init__(
        self,
        top_k: int = 3,
        stage: int = 2,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.top_k = top_k
        self.stage = stage
        self._hostname = socket.gethostname()

    def execute(self, data: TaskState) -> TaskState:
        """Execute reranking using embedding service"""
        if not isinstance(data, TaskState):
            return data

        state = data
        state.node_id = self._hostname
        state.stage = self.stage
        state.operator_name = f"ServiceReranker_{self.stage}"
        state.mark_started()

        try:
            rerank_start = time.time()

            if not state.retrieved_docs:
                state.success = True
                state.mark_completed()
                return state

            # Get embedding service
            embedding_service = self.call_service("embedding")

            # Get query embedding
            query_embeddings = embedding_service.embed([state.query])
            if not query_embeddings:
                # Fallback: keep original order
                state.retrieved_docs = state.retrieved_docs[:self.top_k]
                state.success = True
                state.mark_completed()
                return state

            # Get document embeddings
            doc_texts = [
                doc.get("content", "")[:500]
                for doc in state.retrieved_docs
            ]
            doc_embeddings = embedding_service.embed(doc_texts)

            if not doc_embeddings:
                state.retrieved_docs = state.retrieved_docs[:self.top_k]
                state.success = True
                state.mark_completed()
                return state

            # Compute cosine similarity and rerank
            import math
            query_vec = query_embeddings[0]

            reranked = []
            for doc, doc_vec in zip(state.retrieved_docs, doc_embeddings):
                # Cosine similarity
                dot = sum(a * b for a, b in zip(query_vec, doc_vec))
                norm1 = math.sqrt(sum(a * a for a in query_vec))
                norm2 = math.sqrt(sum(b * b for b in doc_vec))
                score = dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
                reranked.append({**doc, "rerank_score": score})

            reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            state.retrieved_docs = reranked[:self.top_k]

            rerank_time = time.time() - rerank_start
            state.metadata["rerank_time_ms"] = rerank_time * 1000
            state.metadata["num_reranked"] = len(state.retrieved_docs)
            state.success = True

        except Exception as e:
            state.success = False
            state.error = str(e)

        state.mark_completed()
        return state


class ServicePromptor(MapFunction):
    """
    Promptor that builds prompts from retrieved documents.

    Combines query and context into LLM-ready format.
    No service needed - just formatting.
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
        """Build prompt from retrieved docs"""
        if not isinstance(data, TaskState):
            return data

        state = data
        state.node_id = self._hostname
        state.stage = self.stage
        state.operator_name = f"ServicePromptor_{self.stage}"
        state.mark_started()

        try:
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


class ServiceGenerator(MapFunction):
    """
    Service-based generator using registered LLM service.

    Uses self.call_service("llm") for generation.
    Avoids each worker initializing its own LLM client.
    """

    def __init__(
        self,
        stage: int = 4,
        output_file: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.stage = stage
        self.output_file = output_file
        self._hostname = socket.gethostname()

        if self.output_file:
            output_path = Path(self.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

    def execute(self, data: TaskState) -> TaskState:
        """Execute generation using LLM service"""
        if not isinstance(data, TaskState):
            return data

        state = data
        state.node_id = self._hostname
        state.stage = self.stage
        state.operator_name = f"ServiceGenerator_{self.stage}"
        state.mark_started()

        try:
            gen_start = time.time()

            # Build messages
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Answer based on the provided context. If no relevant information, say so.",
                },
                {
                    "role": "user",
                    "content": f"Context:\n{state.context}\n\nQuestion: {state.query}",
                },
            ]

            # Generate response via RPC (timeout=120 for LLM inference)
            state.response = self.call_service("llm", messages=messages, max_tokens=512, temperature=0.7, timeout=120)

            gen_time = time.time() - gen_start
            state.metadata["generation_time_ms"] = gen_time * 1000
            state.success = True

            # 打印生成结果
            print(f"\n{'='*60}")
            print(f"[Generator] Task: {state.task_id}")
            print(f"[Generator] Query: {state.query[:80]}...")
            print(f"[Generator] Context length: {len(state.context)} chars")
            print(f"[Generator] Response ({gen_time*1000:.1f}ms):")
            print(f"  {state.response[:300]}...")
            print(f"{'='*60}\n")

            # 保存生成结果到文件（始终保存）
            self._save_generation_result(state, gen_time)

            # Save to file if configured (legacy)
            if self.output_file:
                self._save_response(state, gen_time)

        except Exception as e:
            state.success = False
            state.error = str(e)
            state.response = f"[Error] {str(e)}"

        state.mark_completed()
        return state

    def _save_response(self, state: TaskState, gen_time: float) -> None:
        """Save response to file"""
        if not self.output_file:
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
            }
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[Warning] Failed to save response: {e}")

    def _save_generation_result(self, state: TaskState, gen_time: float) -> None:
        """保存生成结果到统一文件"""
        try:
            import json
            from datetime import datetime
            from pathlib import Path

            output_dir = Path("/home/sage/data/rag_outputs")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "generation_results.jsonl"

            record = {
                "timestamp": datetime.now().isoformat(),
                "task_id": state.task_id,
                "node_id": state.node_id,
                "query": state.query,
                "context_length": len(state.context),
                "response": state.response,
                "generation_time_ms": gen_time * 1000,
                "num_docs": len(state.retrieved_docs) if state.retrieved_docs else 0,
            }
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[Warning] Failed to save generation result: {e}")


# Set __module__ for Service-based operators for Ray serialization
_SERVICE_OPERATOR_CLASSES = [
    ServiceRetriever,
    ServiceReranker,
    ServicePromptor,
    ServiceGenerator,
]

for _cls in _SERVICE_OPERATOR_CLASSES:
    _cls.__module__ = "common.operators"

# Set __module__ for FiQA operators for Ray serialization
_FIQA_OPERATOR_CLASSES = [
    FiQATaskSource,
    FiQAFAISSRetriever,
]

for _cls in _FIQA_OPERATOR_CLASSES:
    _cls.__module__ = "common.operators"