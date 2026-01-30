"""
Distributed Scheduling Benchmark - Data Models
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ============================================================================
# Query Complexity Classification (for Adaptive-RAG)
# ============================================================================


class QueryComplexityLevel(Enum):
    """查询复杂度级别"""

    ZERO = "zero"  # 简单问题，无需检索
    SINGLE = "single"  # 中等问题，单次检索
    MULTI = "multi"  # 复杂问题，多步推理


@dataclass
class ClassificationResult:
    """分类结果"""

    complexity: QueryComplexityLevel
    confidence: float = 1.0
    reasoning: str = ""


@dataclass
class AdaptiveRAGQueryData:
    """Adaptive-RAG 查询数据"""

    query: str
    classification: ClassificationResult | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class AdaptiveRAGResultData:
    """Adaptive-RAG 结果数据"""

    query: str
    answer: str
    strategy_used: str
    complexity: str
    retrieval_steps: int = 0
    processing_time_ms: float = 0.0


@dataclass
class IterativeState:
    """迭代检索的中间状态 - 在流中传递"""

    original_query: str  # 原始问题
    current_query: str  # 当前检索 query
    accumulated_docs: list[dict] = field(default_factory=list)
    reasoning_chain: list[str] = field(default_factory=list)
    iteration: int = 0
    is_complete: bool = False
    start_time: float = 0.0
    classification: ClassificationResult | None = None


# ============================================================================
# Task State (for general benchmarks)
# ============================================================================


@dataclass
class TaskState:
    """Task state flowing through pipeline stages."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    query: str = ""

    created_time: float = field(default_factory=time.time)
    scheduled_time: float = 0.0
    started_time: float = 0.0
    completed_time: float = 0.0

    scheduling_latency: float = 0.0
    queue_latency: float = 0.0
    execution_latency: float = 0.0
    total_latency: float = 0.0

    node_id: str = ""
    operator_name: str = ""
    stage: int = 0

    context: str = ""
    response: str = ""
    retrieved_docs: list[dict] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    success: bool = True

    def mark_scheduled(self) -> None:
        self.scheduled_time = time.time()
        self.scheduling_latency = self.scheduled_time - self.created_time

    def mark_started(self) -> None:
        self.started_time = time.time()
        if self.scheduled_time > 0:
            self.queue_latency = self.started_time - self.scheduled_time

    def mark_completed(self) -> None:
        self.completed_time = time.time()
        if self.started_time > 0:
            self.execution_latency = self.completed_time - self.started_time
        self.total_latency = self.completed_time - self.created_time

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "query": self.query[:50] if self.query else "",
            "node_id": self.node_id,
            "stage": self.stage,
            "scheduling_latency_ms": self.scheduling_latency * 1000,
            "queue_latency_ms": self.queue_latency * 1000,
            "execution_latency_ms": self.execution_latency * 1000,
            "total_latency_ms": self.total_latency * 1000,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class BenchmarkConfig:
    """Benchmark configuration."""

    experiment_name: str = "benchmark"
    num_tasks: int = 100
    task_complexity: str = "medium"

    parallelism: int = 4
    num_nodes: int = 1

    scheduler_type: str = "load_aware"
    scheduler_strategy: str = "spread"

    use_remote: bool = True
    head_node: str = "sage-node-1"
    worker_nodes: list[str] = field(default_factory=list)

    llm_base_url: str = "http://11.11.11.7:8904/v1"
    llm_model: str = "Qwen/Qwen2.5-3B-Instruct"
    max_tokens: int = 256

    embedding_base_url: str = "http://11.11.11.7:8090/v1"
    embedding_model: str = "BAAI/bge-large-en-v1.5"

    # Retriever 配置
    retriever_type: str = "simple"  # "simple" (内置) 或 "wiki18_faiss" (Wiki18)
    retriever_top_k: int = 10
    # Wiki18 FAISS 专用配置
    wiki18_index_path: str | None = None  # 如: "/home/cyb/wiki18_maxp.index"
    wiki18_documents_path: str | None = None  # 如: "/home/cyb/wiki18_fulldoc.jsonl"
    wiki18_mapping_path: str | None = None  # 如: "/home/cyb/wiki18_maxp_maxp_mapping.json"

    pipeline_stages: int = 3
    enable_rag: bool = True
    enable_llm: bool = True

    test_mode: bool = False
    warmup_tasks: int = 5

    output_dir: str = "results"
    llm_output_file: str | None = None  # 指定 LLM 回复输出文件路径
    save_detailed_metrics: bool = True

    def get_worker_nodes(self, count: int) -> list[str]:
        if self.worker_nodes:
            return self.worker_nodes[:count]
        return [f"sage-node-{i}" for i in range(16, 16 + count)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_name": self.experiment_name,
            "num_tasks": self.num_tasks,
            "task_complexity": self.task_complexity,
            "parallelism": self.parallelism,
            "num_nodes": self.num_nodes,
            "scheduler_type": self.scheduler_type,
            "scheduler_strategy": self.scheduler_strategy,
            "use_remote": self.use_remote,
            "pipeline_stages": self.pipeline_stages,
            "enable_rag": self.enable_rag,
            "enable_llm": self.enable_llm,
        }


@dataclass
class BenchmarkMetrics:
    """Performance metrics collector."""

    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0

    start_time: float = 0.0
    end_time: float = 0.0
    total_duration: float = 0.0

    scheduling_latencies: list[float] = field(default_factory=list)
    queue_latencies: list[float] = field(default_factory=list)
    execution_latencies: list[float] = field(default_factory=list)
    total_latencies: list[float] = field(default_factory=list)

    node_distribution: dict[str, int] = field(default_factory=dict)
    node_latencies: dict[str, list[float]] = field(default_factory=dict)

    stage_latencies: dict[int, list[float]] = field(default_factory=dict)

    config: BenchmarkConfig | None = None

    def record_task(self, state: TaskState) -> None:
        if state.success:
            self.successful_tasks += 1
        else:
            self.failed_tasks += 1

        if state.scheduling_latency > 0:
            self.scheduling_latencies.append(state.scheduling_latency)
        if state.queue_latency > 0:
            self.queue_latencies.append(state.queue_latency)
        if state.execution_latency > 0:
            self.execution_latencies.append(state.execution_latency)
        if state.total_latency > 0:
            self.total_latencies.append(state.total_latency)

        if state.node_id:
            self.node_distribution[state.node_id] = self.node_distribution.get(state.node_id, 0) + 1
            if state.node_id not in self.node_latencies:
                self.node_latencies[state.node_id] = []
            self.node_latencies[state.node_id].append(state.total_latency)

        if state.stage not in self.stage_latencies:
            self.stage_latencies[state.stage] = []
        self.stage_latencies[state.stage].append(state.execution_latency)

    @property
    def throughput(self) -> float:
        if self.total_duration > 0:
            return self.successful_tasks / self.total_duration
        return 0.0

    @property
    def avg_latency_ms(self) -> float:
        if self.total_latencies:
            return sum(self.total_latencies) / len(self.total_latencies)
        return 0.0

    @property
    def p50_latency_ms(self) -> float:
        if self.total_latencies:
            sorted_lat = sorted(self.total_latencies)
            idx = len(sorted_lat) // 2
            return sorted_lat[idx]
        return 0.0

    @property
    def p95_latency_ms(self) -> float:
        if self.total_latencies:
            sorted_lat = sorted(self.total_latencies)
            idx = int(len(sorted_lat) * 0.95)
            return sorted_lat[min(idx, len(sorted_lat) - 1)]
        return 0.0

    @property
    def p99_latency_ms(self) -> float:
        if self.total_latencies:
            sorted_lat = sorted(self.total_latencies)
            idx = int(len(sorted_lat) * 0.99)
            return sorted_lat[min(idx, len(sorted_lat) - 1)]
        return 0.0

    @property
    def avg_scheduling_latency_ms(self) -> float:
        if self.scheduling_latencies:
            return sum(self.scheduling_latencies) / len(self.scheduling_latencies) * 1000
        return 0.0

    @property
    def avg_queue_latency_ms(self) -> float:
        if self.queue_latencies:
            return sum(self.queue_latencies) / len(self.queue_latencies) * 1000
        return 0.0

    @property
    def avg_execution_latency_ms(self) -> float:
        if self.execution_latencies:
            return sum(self.execution_latencies) / len(self.execution_latencies) * 1000
        return 0.0

    @property
    def node_balance_score(self) -> float:
        if not self.node_distribution or len(self.node_distribution) <= 1:
            return 1.0
        counts = list(self.node_distribution.values())
        avg = sum(counts) / len(counts)
        if avg == 0:
            return 1.0
        variance = sum((c - avg) ** 2 for c in counts) / len(counts)
        std = variance**0.5
        cv = std / avg
        return max(0.0, 1.0 - cv)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "total_duration_sec": self.total_duration,
            "throughput_tasks_per_sec": self.throughput,
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "avg_scheduling_latency_ms": self.avg_scheduling_latency_ms,
            "avg_queue_latency_ms": self.avg_queue_latency_ms,
            "avg_execution_latency_ms": self.avg_execution_latency_ms,
            "node_distribution": self.node_distribution,
            "node_balance_score": self.node_balance_score,
            "config": self.config.to_dict() if self.config else None,
        }

    def print_summary(self) -> None:
        print("\n" + "=" * 70)
        print("Benchmark Results Summary")
        print("=" * 70)
        print(f"  Total Tasks:       {self.total_tasks}")
        print(f"  Successful:        {self.successful_tasks}")
        print(f"  Failed:            {self.failed_tasks}")
        print(f"  Duration:          {self.total_duration:.2f}s")
        print("-" * 70)
        print(f"  Throughput:        {self.throughput:.2f} tasks/sec")
        print(f"  Avg Latency:       {self.avg_latency_ms:.2f} ms")
        print(f"  P50 Latency:       {self.p50_latency_ms:.2f} ms")
        print(f"  P95 Latency:       {self.p95_latency_ms:.2f} ms")
        print(f"  P99 Latency:       {self.p99_latency_ms:.2f} ms")
        print("-" * 70)
        print(f"  Avg Scheduling:    {self.avg_scheduling_latency_ms:.2f} ms")
        print(f"  Avg Queue:         {self.avg_queue_latency_ms:.2f} ms")
        print(f"  Avg Execution:     {self.avg_execution_latency_ms:.2f} ms")
        print("-" * 70)
        print(f"  Node Balance:      {self.node_balance_score:.2%}")
        if self.node_distribution:
            print("  Node Distribution:")
            for node, count in sorted(self.node_distribution.items()):
                pct = count / self.successful_tasks * 100 if self.successful_tasks > 0 else 0
                print(f"    {node}: {count} ({pct:.1f}%)")
        print("=" * 70)
