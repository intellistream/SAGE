"""
Workload 4 生成和 Sink

实现批量 LLM 生成和指标收集功能。
"""

from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sage.common.core.functions.map_function import MapFunction
from sage.common.core.functions.sink_function import SinkFunction

if TYPE_CHECKING:
    from .models import BatchContext, Workload4Metrics


class BatchLLMGenerator(MapFunction):
    """
    批量 LLM 生成算子。

    处理 Global Batch 的批量请求，调用 LLM 服务生成回复。

    特点:
    - 批量调用 LLM API
    - 支持并发控制
    - 错误处理和重试
    - 性能指标记录

    Args:
        llm_base_url: LLM 服务地址
        llm_model: 使用的模型名称
        max_tokens: 最大生成 token 数
        temperature: 生成温度
        batch_timeout_seconds: 批量调用超时(秒)
        max_retries: 最大重试次数
        **kwargs: 其他参数
    """

    def __init__(
        self,
        llm_base_url: str,
        llm_model: str,
        max_tokens: int = 120,
        temperature: float = 0.7,
        batch_timeout_seconds: int = 30,
        max_retries: int = 3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.batch_timeout_seconds = batch_timeout_seconds
        self.max_retries = max_retries

        # 统计
        self.total_calls = 0
        self.total_tokens = 0
        self.failed_calls = 0

    def execute(self, batch_context: BatchContext) -> list[tuple[str, str, Workload4Metrics]]:
        """
        批量生成 LLM 回复。

        Args:
            batch_context: 批处理上下文

        Returns:
            [(query_id, response, metrics), ...] 列表
        """
        from sage.kernel.runtime.communication.packet import StopSignal

        if isinstance(batch_context, StopSignal):
            return batch_context

        start_time = time.time()
        results = []

        # 为批次中的每个 item 生成回复
        for item in batch_context.items:
            # item 是 (joined_event, graph_results, reranking_results)
            joined_event, graph_results, reranking_results = item
            query = joined_event.query

            # 构建 prompt(使用检索到的上下文)
            # 合并 graph 和 reranking 的文档
            context_docs = []

            # 添加 graph 结果
            for graph_result in graph_results[:2]:  # 取前2个graph结果
                if hasattr(graph_result, "content"):
                    context_docs.append(graph_result.content)

            # 添加 reranking 结果
            for rerank_result in reranking_results[:3]:  # 取前3个rerank结果
                if hasattr(rerank_result, "vdb_result") and hasattr(
                    rerank_result.vdb_result, "content"
                ):
                    context_docs.append(rerank_result.vdb_result.content)

            context = "\n\n".join(context_docs) if context_docs else "No relevant context found."

            prompt = self._build_prompt(query.query_text, context)

            # 调用 LLM(带重试)
            response = self._call_llm_with_retry(prompt)

            # 创建指标对象
            metrics = self._create_metrics(joined_event, start_time)

            # 添加结果
            results.append((query.query_id, response, metrics))

        # 更新统计
        self.total_calls += len(batch_context.items)

        return results

    def _build_prompt(self, query: str, context: str) -> str:
        """
        构建 LLM prompt。

        Args:
            query: 用户查询
            context: 检索到的上下文

        Returns:
            完整的 prompt
        """
        return f"""Based on the following context, please answer the question.

Context:
{context}

Question: {query}

Answer:"""

    def _call_llm_with_retry(self, prompt: str) -> str:
        """
        调用 LLM API(带重试机制)。

        Args:
            prompt: 输入 prompt

        Returns:
            生成的回复
        """
        import requests

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.llm_base_url}/chat/completions",
                    json={
                        "model": self.llm_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                    },
                    timeout=self.batch_timeout_seconds,
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]

                    # 更新 token 统计
                    if "usage" in data:
                        self.total_tokens += data["usage"].get("total_tokens", 0)

                    return content
                else:
                    error_msg = f"LLM API error (status {response.status_code}): {response.text}"
                    if attempt < self.max_retries - 1:
                        time.sleep(2**attempt)  # Exponential backoff
                        continue
                    else:
                        self.failed_calls += 1
                        return f"[Error: {error_msg}]"

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    continue
                else:
                    self.failed_calls += 1
                    return "[Error: LLM request timeout]"

            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)
                    continue
                else:
                    self.failed_calls += 1
                    return f"[Error: {str(e)}]"

        return "[Error: Max retries exceeded]"

    def _create_metrics(self, item: Any, start_time: float) -> Workload4Metrics:
        """
        创建指标对象。

        Args:
            item: JoinedEvent
            start_time: 批处理开始时间

        Returns:
            Workload4Metrics 对象
        """
        try:
            from .models import Workload4Metrics
        except ImportError:
            from models import Workload4Metrics

        current_time = time.time()
        query = item.query

        metrics = Workload4Metrics(
            task_id=item.joined_id,
            query_id=query.query_id,
            query_arrival_time=query.timestamp,
            join_time=item.join_timestamp,
            generation_time=current_time,
            end_to_end_time=current_time - query.timestamp,
            join_matched_docs=len(item.matched_docs),
            semantic_join_score=item.semantic_score,
        )

        return metrics

    def get_stats(self) -> dict[str, Any]:
        """
        获取生成统计。

        Returns:
            统计字典
        """
        return {
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "total_tokens": self.total_tokens,
            "avg_tokens_per_call": self.total_tokens / self.total_calls
            if self.total_calls > 0
            else 0,
        }


class Workload4MetricsSink(SinkFunction):
    """
    Workload 4 指标收集 Sink。

    收集完整的端到端指标，包括所有 stage 的时间戳和统计信息。

    特点:
    - 支持长时间运行(Workload 4 延迟高)
    - 实时写入文件(避免内存溢出)
    - 生成详细的汇总报告
    - 支持 CSV 和 JSON 输出

    Args:
        metrics_output_dir: 指标输出目录
        verbose: 是否打印详细信息
        drain_timeout: Drain 总超时(秒)，默认 24 小时
        drain_quiet_period: 静默期(秒)，默认 2 分钟
        **kwargs: 其他参数
    """

    # Workload 4 特定的 drain 配置(更长的超时时间)
    drain_timeout: float = 86400  # 24 hours
    drain_quiet_period: float = 120  # 2 minutes

    def __init__(
        self,
        metrics_output_dir: str = "/tmp/sage_metrics_workload4",
        verbose: bool = True,
        drain_timeout: float | None = None,
        drain_quiet_period: float | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.metrics_output_dir = Path(metrics_output_dir)
        self.verbose = verbose

        # 允许通过参数覆盖 drain 配置
        if drain_timeout is not None:
            self.drain_timeout = drain_timeout
        if drain_quiet_period is not None:
            self.drain_quiet_period = drain_quiet_period

        # 创建输出目录
        self.metrics_output_dir.mkdir(parents=True, exist_ok=True)

        # 统计
        self.count = 0
        self.metrics: list[Workload4Metrics] = []
        self.start_time = time.time()

        # 创建输出文件
        self.instance_id = f"{socket.gethostname()}_{os.getpid()}_{int(time.time() * 1000)}"
        self.jsonl_file = self.metrics_output_dir / f"metrics_{self.instance_id}.jsonl"
        self.csv_file = self.metrics_output_dir / f"metrics_{self.instance_id}.csv"

        # 写入文件 header
        self._write_header()

    def _write_header(self) -> None:
        """写入文件 header"""
        # JSONL header
        with open(self.jsonl_file, "w") as f:
            header = {
                "type": "header",
                "instance_id": self.instance_id,
                "start_time": self.start_time,
                "hostname": socket.gethostname(),
                "pid": os.getpid(),
                "workload": "workload4",
            }
            f.write(json.dumps(header) + "\n")

        # CSV header
        with open(self.csv_file, "w") as f:
            f.write("task_id,query_id,end_to_end_latency_ms,join_latency_ms,")
            f.write("vdb1_latency_ms,vdb2_latency_ms,graph_latency_ms,")
            f.write("clustering_latency_ms,reranking_latency_ms,generation_latency_ms,")
            f.write("join_matched_docs,vdb1_results,vdb2_results,graph_nodes_visited,")
            f.write("clusters_found,duplicates_removed,final_top_k,")
            f.write("semantic_join_score,final_rerank_score,diversity_score\n")

        if self.verbose:
            print("[Workload4MetricsSink] Initialized:")
            print(f"  JSONL: {self.jsonl_file}")
            print(f"  CSV: {self.csv_file}")

    def execute(self, data: tuple[str, str, Workload4Metrics]) -> None:
        """
        收集单个任务的指标。

        Args:
            data: (query_id, response, metrics) 元组
        """
        from sage.kernel.runtime.communication.packet import StopSignal

        if isinstance(data, StopSignal):
            # SinkFunction 遇到 StopSignal 不需要返回，直接返回 None
            return
        self.logger.info(f"received data : {data}")
        query_id, response, metrics = data

        # 添加到内存列表
        self.metrics.append(metrics)
        self.count += 1

        # 实时写入文件
        self._write_metrics_to_file(metrics)

        # 打印进度
        if self.verbose and self.count % 10 == 0:
            elapsed = time.time() - self.start_time
            throughput = self.count / elapsed if elapsed > 0 else 0
            print(
                f"[Workload4MetricsSink] Processed {self.count} tasks, throughput: {throughput:.2f} QPS"
            )

    def _write_metrics_to_file(self, metrics: Workload4Metrics) -> None:
        """
        将指标写入文件。

        Args:
            metrics: Workload4Metrics 对象
        """
        # 写入 JSONL
        with open(self.jsonl_file, "a") as f:
            record = {
                "type": "task",
                "task_id": metrics.task_id,
                "query_id": metrics.query_id,
                "end_to_end_time": metrics.end_to_end_time,
                "join_time": metrics.join_time,
                "vdb1_latency": metrics.vdb1_end_time - metrics.vdb1_start_time
                if metrics.vdb1_end_time > 0
                else 0,
                "vdb2_latency": metrics.vdb2_end_time - metrics.vdb2_start_time
                if metrics.vdb2_end_time > 0
                else 0,
                "graph_latency": metrics.graph_end_time - metrics.graph_start_time
                if metrics.graph_end_time > 0
                else 0,
                "clustering_time": metrics.clustering_time,
                "reranking_time": metrics.reranking_time,
                "generation_time": metrics.generation_time,
                "join_matched_docs": metrics.join_matched_docs,
                "vdb1_results": metrics.vdb1_results,
                "vdb2_results": metrics.vdb2_results,
                "graph_nodes_visited": metrics.graph_nodes_visited,
                "clusters_found": metrics.clusters_found,
                "duplicates_removed": metrics.duplicates_removed,
                "final_top_k": metrics.final_top_k,
                "semantic_join_score": metrics.semantic_join_score,
                "final_rerank_score": metrics.final_rerank_score,
                "diversity_score": metrics.diversity_score,
                "timestamp": time.time(),
            }
            f.write(json.dumps(record) + "\n")

        # 写入 CSV
        with open(self.csv_file, "a") as f:
            latencies = metrics.compute_latencies()
            f.write(f"{metrics.task_id},{metrics.query_id},")
            f.write(f"{metrics.end_to_end_time * 1000:.2f},")
            f.write(f"{latencies['join_latency'] * 1000:.2f},")
            f.write(f"{latencies['vdb1_latency'] * 1000:.2f},")
            f.write(f"{latencies['vdb2_latency'] * 1000:.2f},")
            f.write(f"{latencies.get('graph_latency', 0) * 1000:.2f},")
            f.write(f"{metrics.clustering_time * 1000:.2f},")
            f.write(f"{metrics.reranking_time * 1000:.2f},")
            f.write(f"{(metrics.generation_time - metrics.join_time) * 1000:.2f},")
            f.write(f"{metrics.join_matched_docs},")
            f.write(f"{metrics.vdb1_results},")
            f.write(f"{metrics.vdb2_results},")
            f.write(f"{metrics.graph_nodes_visited},")
            f.write(f"{metrics.clusters_found},")
            f.write(f"{metrics.duplicates_removed},")
            f.write(f"{metrics.final_top_k},")
            f.write(f"{metrics.semantic_join_score:.4f},")
            f.write(f"{metrics.final_rerank_score:.4f},")
            f.write(f"{metrics.diversity_score:.4f}\n")

    def close(self) -> None:
        """
        关闭 Sink，生成汇总报告。
        """
        if self.count == 0:
            if self.verbose:
                print("[Workload4MetricsSink] No metrics collected")
            return

        # 生成汇总报告
        self._generate_summary_report()

        if self.verbose:
            print(f"[Workload4MetricsSink] Closed. Total tasks: {self.count}")

    def _generate_summary_report(self) -> None:
        """生成汇总报告"""
        import statistics

        elapsed = time.time() - self.start_time

        # 计算延迟统计
        e2e_latencies = [m.end_to_end_time * 1000 for m in self.metrics]
        join_latencies = [
            (m.join_time - m.query_arrival_time) * 1000 for m in self.metrics if m.join_time > 0
        ]

        # 计算中间结果统计
        total_join_docs = sum(m.join_matched_docs for m in self.metrics)
        total_vdb1_results = sum(m.vdb1_results for m in self.metrics)
        total_vdb2_results = sum(m.vdb2_results for m in self.metrics)
        total_graph_nodes = sum(m.graph_nodes_visited for m in self.metrics)
        total_clusters = sum(m.clusters_found for m in self.metrics)
        total_duplicates = sum(m.duplicates_removed for m in self.metrics)

        # 生成报告
        report = {
            "summary": {
                "total_tasks": self.count,
                "elapsed_time_seconds": elapsed,
                "throughput_qps": self.count / elapsed if elapsed > 0 else 0,
            },
            "latency_statistics": {
                "end_to_end": {
                    "mean_ms": statistics.mean(e2e_latencies),
                    "median_ms": statistics.median(e2e_latencies),
                    "p95_ms": self._percentile(e2e_latencies, 95),
                    "p99_ms": self._percentile(e2e_latencies, 99),
                    "min_ms": min(e2e_latencies),
                    "max_ms": max(e2e_latencies),
                },
                "join": {
                    "mean_ms": statistics.mean(join_latencies) if join_latencies else 0,
                    "median_ms": statistics.median(join_latencies) if join_latencies else 0,
                    "p95_ms": self._percentile(join_latencies, 95) if join_latencies else 0,
                    "p99_ms": self._percentile(join_latencies, 99) if join_latencies else 0,
                },
            },
            "intermediate_results": {
                "avg_join_matched_docs": total_join_docs / self.count,
                "avg_vdb1_results": total_vdb1_results / self.count,
                "avg_vdb2_results": total_vdb2_results / self.count,
                "avg_graph_nodes_visited": total_graph_nodes / self.count,
                "avg_clusters_found": total_clusters / self.count,
                "total_duplicates_removed": total_duplicates,
                "dedup_rate": total_duplicates / (total_vdb1_results + total_vdb2_results)
                if (total_vdb1_results + total_vdb2_results) > 0
                else 0,
            },
            "quality_metrics": {
                "avg_semantic_join_score": statistics.mean(
                    [m.semantic_join_score for m in self.metrics if m.semantic_join_score > 0]
                )
                if any(m.semantic_join_score > 0 for m in self.metrics)
                else 0.0,
                "avg_final_rerank_score": statistics.mean(
                    [m.final_rerank_score for m in self.metrics if m.final_rerank_score > 0]
                )
                if any(m.final_rerank_score > 0 for m in self.metrics)
                else 0.0,
                "avg_diversity_score": statistics.mean(
                    [m.diversity_score for m in self.metrics if m.diversity_score > 0]
                )
                if any(m.diversity_score > 0 for m in self.metrics)
                else 0.0,
            },
        }

        # 写入报告文件
        report_file = self.metrics_output_dir / f"summary_{self.instance_id}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        if self.verbose:
            print("\n" + "=" * 80)
            print("Workload 4 Benchmark Summary")
            print("=" * 80)
            print(f"Total Tasks: {report['summary']['total_tasks']}")
            print(f"Elapsed Time: {report['summary']['elapsed_time_seconds']:.2f}s")
            print(f"Throughput: {report['summary']['throughput_qps']:.2f} QPS")
            print()
            print("End-to-End Latency:")
            print(f"  Mean: {report['latency_statistics']['end_to_end']['mean_ms']:.2f}ms")
            print(f"  Median: {report['latency_statistics']['end_to_end']['median_ms']:.2f}ms")
            print(f"  P95: {report['latency_statistics']['end_to_end']['p95_ms']:.2f}ms")
            print(f"  P99: {report['latency_statistics']['end_to_end']['p99_ms']:.2f}ms")
            print()
            print("Intermediate Results:")
            print(
                f"  Avg Join Matched Docs: {report['intermediate_results']['avg_join_matched_docs']:.1f}"
            )
            print(f"  Avg VDB1 Results: {report['intermediate_results']['avg_vdb1_results']:.1f}")
            print(f"  Avg VDB2 Results: {report['intermediate_results']['avg_vdb2_results']:.1f}")
            print(f"  Dedup Rate: {report['intermediate_results']['dedup_rate'] * 100:.1f}%")
            print("=" * 80)
            print(f"Report saved to: {report_file}")

    def _percentile(self, data: list[float], percentile: int) -> float:
        """
        计算百分位数。

        Args:
            data: 数据列表
            percentile: 百分位(0-100)

        Returns:
            百分位值
        """
        if not data:
            return 0.0

        sorted_data = sorted(data)
        # 使用线性插值计算百分位
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = k - f

        if f + 1 < len(sorted_data):
            return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
        else:
            return sorted_data[f]

    def get_stats(self) -> dict[str, Any]:
        """
        获取当前统计。

        Returns:
            统计字典
        """
        elapsed = time.time() - self.start_time
        return {
            "count": self.count,
            "elapsed_seconds": elapsed,
            "throughput_qps": self.count / elapsed if elapsed > 0 else 0,
        }


# 工具函数


def create_mock_batch_context(num_items: int = 5) -> BatchContext:
    """
    创建 Mock BatchContext 用于测试。

    Args:
        num_items: 批次大小

    Returns:
        BatchContext 对象
    """
    try:
        from .models import BatchContext, DocumentEvent, JoinedEvent, QueryEvent
    except ImportError:
        # 如果相对导入失败，尝试绝对导入
        from models import BatchContext, DocumentEvent, JoinedEvent, QueryEvent

    items = []
    for i in range(num_items):
        query = QueryEvent(
            query_id=f"query_{i}",
            query_text=f"What is test query {i}?",
            query_type="factual",
            category="general",
            timestamp=time.time(),
        )

        docs = [
            DocumentEvent(
                doc_id=f"doc_{i}_{j}",
                doc_text=f"This is document {j} for query {i}",
                doc_category="general",
                timestamp=time.time(),
            )
            for j in range(3)
        ]

        joined = JoinedEvent(
            joined_id=f"joined_{i}",
            query=query,
            matched_docs=docs,
            join_timestamp=time.time(),
            semantic_score=0.85,
        )

        items.append(joined)

    return BatchContext(
        batch_id=f"batch_{int(time.time())}",
        batch_type="global",
        items=items,
        batch_timestamp=time.time(),
        batch_size=num_items,
    )
