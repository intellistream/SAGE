# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Hybrid Benchmark Metrics Module
================================

Collects and aggregates performance metrics for mixed LLM and Embedding
benchmark runs.

This module provides:
- HybridRequestMetrics: Aggregated metrics for hybrid benchmark runs
- HybridMetricsCollector: Collects and computes statistics from request results
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..common.base_metrics import BaseMetricsCollector, BaseRequestMetrics
from .client import HybridRequestResult
from .config import RequestType


@dataclass
class HybridRequestMetrics(BaseRequestMetrics):
    """Aggregated metrics for hybrid (LLM + Embedding) benchmark runs.

    Extends BaseRequestMetrics with separate metrics for LLM and Embedding
    request types, enabling detailed analysis of mixed workloads.

    Attributes:
        # LLM-specific metrics
        llm_total_requests: Total LLM requests
        llm_completed_requests: Completed LLM requests
        llm_throughput_rps: LLM requests per second
        llm_token_throughput_tps: LLM tokens generated per second
        llm_ttft_avg_ms: Average time to first token
        llm_ttft_p50_ms: 50th percentile TTFT
        llm_ttft_p95_ms: 95th percentile TTFT
        llm_ttft_p99_ms: 99th percentile TTFT
        llm_tbt_avg_ms: Average time between tokens
        llm_tbt_p95_ms: 95th percentile TBT
        llm_e2e_latency_avg_ms: LLM-specific average E2E latency
        llm_e2e_latency_p99_ms: LLM-specific P99 E2E latency
        llm_slo_compliance_rate: LLM SLO compliance rate

        # Embedding-specific metrics
        embedding_total_requests: Total embedding requests
        embedding_completed_requests: Completed embedding requests
        embedding_throughput_rps: Embedding requests per second
        embedding_throughput_texts_ps: Texts embedded per second
        embedding_batch_efficiency: Average batch utilization efficiency
        embedding_avg_batch_size: Average batch size
        embedding_e2e_latency_avg_ms: Embedding-specific average E2E latency
        embedding_e2e_latency_p99_ms: Embedding-specific P99 E2E latency
        embedding_slo_compliance_rate: Embedding SLO compliance rate

        # Mixed workload metrics
        llm_ratio_actual: Actual ratio of LLM requests
        embedding_ratio_actual: Actual ratio of Embedding requests
        metrics_by_request_type: Metrics breakdown by request type
    """

    # LLM-specific metrics
    llm_total_requests: int = 0
    llm_completed_requests: int = 0
    llm_throughput_rps: float = 0.0
    llm_token_throughput_tps: float = 0.0
    llm_ttft_avg_ms: float = 0.0
    llm_ttft_p50_ms: float = 0.0
    llm_ttft_p95_ms: float = 0.0
    llm_ttft_p99_ms: float = 0.0
    llm_tbt_avg_ms: float = 0.0
    llm_tbt_p95_ms: float = 0.0
    llm_e2e_latency_avg_ms: float = 0.0
    llm_e2e_latency_p99_ms: float = 0.0
    llm_slo_compliance_rate: float = 0.0

    # Embedding-specific metrics
    embedding_total_requests: int = 0
    embedding_completed_requests: int = 0
    embedding_throughput_rps: float = 0.0
    embedding_throughput_texts_ps: float = 0.0
    embedding_batch_efficiency: float = 0.0
    embedding_avg_batch_size: float = 0.0
    embedding_e2e_latency_avg_ms: float = 0.0
    embedding_e2e_latency_p99_ms: float = 0.0
    embedding_slo_compliance_rate: float = 0.0

    # Mixed workload metrics
    llm_ratio_actual: float = 0.0
    embedding_ratio_actual: float = 0.0
    metrics_by_request_type: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary with full breakdown."""
        base_dict = self.to_base_dict()

        # Add LLM-specific metrics
        base_dict["llm"] = {
            "request_counts": {
                "total": self.llm_total_requests,
                "completed": self.llm_completed_requests,
            },
            "throughput": {
                "requests_per_second": self.llm_throughput_rps,
                "tokens_per_second": self.llm_token_throughput_tps,
            },
            "ttft_ms": {
                "avg": self.llm_ttft_avg_ms,
                "p50": self.llm_ttft_p50_ms,
                "p95": self.llm_ttft_p95_ms,
                "p99": self.llm_ttft_p99_ms,
            },
            "tbt_ms": {
                "avg": self.llm_tbt_avg_ms,
                "p95": self.llm_tbt_p95_ms,
            },
            "e2e_latency_ms": {
                "avg": self.llm_e2e_latency_avg_ms,
                "p99": self.llm_e2e_latency_p99_ms,
            },
            "slo_compliance_rate": self.llm_slo_compliance_rate,
        }

        # Add Embedding-specific metrics
        base_dict["embedding"] = {
            "request_counts": {
                "total": self.embedding_total_requests,
                "completed": self.embedding_completed_requests,
            },
            "throughput": {
                "requests_per_second": self.embedding_throughput_rps,
                "texts_per_second": self.embedding_throughput_texts_ps,
            },
            "batch": {
                "efficiency": self.embedding_batch_efficiency,
                "avg_size": self.embedding_avg_batch_size,
            },
            "e2e_latency_ms": {
                "avg": self.embedding_e2e_latency_avg_ms,
                "p99": self.embedding_e2e_latency_p99_ms,
            },
            "slo_compliance_rate": self.embedding_slo_compliance_rate,
        }

        # Add mixed workload metrics
        base_dict["mixed_workload"] = {
            "llm_ratio_actual": self.llm_ratio_actual,
            "embedding_ratio_actual": self.embedding_ratio_actual,
        }

        base_dict["metrics_by_request_type"] = self.metrics_by_request_type

        return base_dict


class HybridMetricsCollector(BaseMetricsCollector):
    """Collects and aggregates metrics for hybrid benchmark runs.

    This collector handles both LLM and Embedding request results,
    computing separate statistics for each type while also providing
    combined metrics for the overall benchmark run.

    Example:
        collector = HybridMetricsCollector()
        collector.set_time_range(start_time, end_time)
        for result in results:
            collector.add_result(result)
        metrics = collector.compute_metrics()
    """

    def __init__(self, max_batch_size: int = 32) -> None:
        """Initialize hybrid metrics collector.

        Args:
            max_batch_size: Maximum expected batch size for efficiency calculation
        """
        super().__init__()
        self._max_batch_size = max_batch_size

    @property
    def results(self) -> list[HybridRequestResult]:
        """Get collected results with proper typing."""
        return self._results  # type: ignore[return-value]

    def _get_llm_results(self) -> list[HybridRequestResult]:
        """Get only LLM request results."""
        return [r for r in self.results if r.is_llm_request]

    def _get_embedding_results(self) -> list[HybridRequestResult]:
        """Get only Embedding request results."""
        return [r for r in self.results if r.is_embedding_request]

    def compute_metrics(self) -> HybridRequestMetrics:
        """Compute aggregated metrics from collected results.

        Returns:
            HybridRequestMetrics with all computed statistics
        """
        if not self._results:
            return HybridRequestMetrics()

        # Start with base metrics computation
        base_metrics = self._compute_base_metrics()

        # Create hybrid metrics with base values
        metrics = HybridRequestMetrics(
            # Copy base metrics
            total_requests=base_metrics.total_requests,
            completed_requests=base_metrics.completed_requests,
            failed_requests=base_metrics.failed_requests,
            timeout_requests=base_metrics.timeout_requests,
            duration_seconds=base_metrics.duration_seconds,
            throughput_rps=base_metrics.throughput_rps,
            e2e_latency_avg_ms=base_metrics.e2e_latency_avg_ms,
            e2e_latency_p50_ms=base_metrics.e2e_latency_p50_ms,
            e2e_latency_p95_ms=base_metrics.e2e_latency_p95_ms,
            e2e_latency_p99_ms=base_metrics.e2e_latency_p99_ms,
            e2e_latency_min_ms=base_metrics.e2e_latency_min_ms,
            e2e_latency_max_ms=base_metrics.e2e_latency_max_ms,
            slo_compliance_rate=base_metrics.slo_compliance_rate,
            slo_by_priority=base_metrics.slo_by_priority,
            error_rate=base_metrics.error_rate,
            timeout_rate=base_metrics.timeout_rate,
            metrics_by_priority=base_metrics.metrics_by_priority,
        )

        # Compute LLM-specific metrics
        self._compute_llm_metrics(metrics)

        # Compute Embedding-specific metrics
        self._compute_embedding_metrics(metrics)

        # Compute mixed workload ratios
        self._compute_mixed_workload_metrics(metrics)

        # Compute metrics by request type
        metrics.metrics_by_request_type = self._compute_metrics_by_request_type()

        return metrics

    def _compute_llm_metrics(self, metrics: HybridRequestMetrics) -> None:
        """Compute LLM-specific metrics.

        Args:
            metrics: HybridRequestMetrics object to populate
        """
        llm_results = self._get_llm_results()
        if not llm_results:
            return

        # Request counts
        metrics.llm_total_requests = len(llm_results)
        metrics.llm_completed_requests = sum(1 for r in llm_results if r.success)

        # Throughput
        if metrics.duration_seconds > 0:
            metrics.llm_throughput_rps = metrics.llm_completed_requests / metrics.duration_seconds

        # Token throughput
        total_tokens = sum(r.output_token_count for r in llm_results if r.success)
        if metrics.duration_seconds > 0:
            metrics.llm_token_throughput_tps = total_tokens / metrics.duration_seconds

        # TTFT (Time To First Token)
        ttfts = [r.ttft_ms for r in llm_results if r.success and r.ttft_ms is not None]
        if ttfts:
            metrics.llm_ttft_avg_ms = float(np.mean(ttfts))
            metrics.llm_ttft_p50_ms = float(np.percentile(ttfts, 50))
            metrics.llm_ttft_p95_ms = float(np.percentile(ttfts, 95))
            metrics.llm_ttft_p99_ms = float(np.percentile(ttfts, 99))

        # TBT (Time Between Tokens)
        all_tbts: list[float] = []
        for r in llm_results:
            if r.success and r.inter_token_latencies:
                all_tbts.extend(r.inter_token_latencies)
        if all_tbts:
            metrics.llm_tbt_avg_ms = float(np.mean(all_tbts))
            metrics.llm_tbt_p95_ms = float(np.percentile(all_tbts, 95))

        # E2E Latency for LLM
        llm_latencies = [
            r.e2e_latency_ms for r in llm_results if r.success and r.e2e_latency_ms is not None
        ]
        if llm_latencies:
            metrics.llm_e2e_latency_avg_ms = float(np.mean(llm_latencies))
            metrics.llm_e2e_latency_p99_ms = float(np.percentile(llm_latencies, 99))

        # SLO compliance for LLM
        successful_llm = [r for r in llm_results if r.success]
        if successful_llm:
            slo_met = sum(1 for r in successful_llm if r.met_slo)
            metrics.llm_slo_compliance_rate = slo_met / len(successful_llm)

    def _compute_embedding_metrics(self, metrics: HybridRequestMetrics) -> None:
        """Compute Embedding-specific metrics.

        Args:
            metrics: HybridRequestMetrics object to populate
        """
        embedding_results = self._get_embedding_results()
        if not embedding_results:
            return

        # Request counts
        metrics.embedding_total_requests = len(embedding_results)
        metrics.embedding_completed_requests = sum(1 for r in embedding_results if r.success)

        # Throughput (requests per second)
        if metrics.duration_seconds > 0:
            metrics.embedding_throughput_rps = (
                metrics.embedding_completed_requests / metrics.duration_seconds
            )

        # Texts per second throughput
        total_texts = sum(r.total_texts_embedded for r in embedding_results if r.success)
        if metrics.duration_seconds > 0:
            metrics.embedding_throughput_texts_ps = total_texts / metrics.duration_seconds

        # Batch efficiency (actual batch size / max batch size)
        batch_sizes = [r.batch_size for r in embedding_results if r.success]
        if batch_sizes:
            metrics.embedding_avg_batch_size = float(np.mean(batch_sizes))
            metrics.embedding_batch_efficiency = (
                metrics.embedding_avg_batch_size / self._max_batch_size
            )

        # E2E Latency for Embedding
        embedding_latencies = [
            r.e2e_latency_ms
            for r in embedding_results
            if r.success and r.e2e_latency_ms is not None
        ]
        if embedding_latencies:
            metrics.embedding_e2e_latency_avg_ms = float(np.mean(embedding_latencies))
            metrics.embedding_e2e_latency_p99_ms = float(np.percentile(embedding_latencies, 99))

        # SLO compliance for Embedding
        successful_embedding = [r for r in embedding_results if r.success]
        if successful_embedding:
            slo_met = sum(1 for r in successful_embedding if r.met_slo)
            metrics.embedding_slo_compliance_rate = slo_met / len(successful_embedding)

    def _compute_mixed_workload_metrics(self, metrics: HybridRequestMetrics) -> None:
        """Compute mixed workload ratio metrics.

        Args:
            metrics: HybridRequestMetrics object to populate
        """
        if metrics.total_requests == 0:
            return

        metrics.llm_ratio_actual = metrics.llm_total_requests / metrics.total_requests
        metrics.embedding_ratio_actual = metrics.embedding_total_requests / metrics.total_requests

    def _compute_metrics_by_request_type(self) -> dict[str, dict[str, Any]]:
        """Compute metrics breakdown by request type.

        Returns:
            Dictionary mapping request type to metrics
        """
        type_groups: dict[str, list[HybridRequestResult]] = {}

        for r in self.results:
            request_type = r.request_type.value
            if request_type not in type_groups:
                type_groups[request_type] = []
            type_groups[request_type].append(r)

        result: dict[str, dict[str, Any]] = {}
        for request_type, group_results in type_groups.items():
            success_results = [r for r in group_results if r.success]
            e2e_latencies = [
                r.e2e_latency_ms for r in success_results if r.e2e_latency_ms is not None
            ]

            result[request_type] = {
                "total_requests": len(group_results),
                "completed_requests": len(success_results),
                "avg_latency_ms": float(np.mean(e2e_latencies)) if e2e_latencies else 0.0,
                "p99_latency_ms": (
                    float(np.percentile(e2e_latencies, 99)) if e2e_latencies else 0.0
                ),
                "slo_compliance_rate": (
                    sum(1 for r in success_results if r.met_slo) / len(success_results)
                    if success_results
                    else 0.0
                ),
            }

            # Add LLM-specific fields if applicable
            if request_type in (RequestType.LLM_CHAT.value, RequestType.LLM_GENERATE.value):
                ttfts = [r.ttft_ms for r in success_results if r.ttft_ms is not None]
                result[request_type]["avg_ttft_ms"] = float(np.mean(ttfts)) if ttfts else 0.0
                result[request_type]["total_tokens"] = sum(
                    r.output_token_count for r in success_results
                )

            # Add Embedding-specific fields if applicable
            if request_type == RequestType.EMBEDDING.value:
                result[request_type]["total_texts_embedded"] = sum(
                    r.total_texts_embedded for r in success_results
                )
                batch_sizes = [r.batch_size for r in success_results]
                result[request_type]["avg_batch_size"] = (
                    float(np.mean(batch_sizes)) if batch_sizes else 0.0
                )

        return result

    def get_summary_string(self) -> str:
        """Get a human-readable summary of collected metrics.

        Returns:
            Formatted summary string
        """
        metrics = self.compute_metrics()

        lines = [
            "=" * 60,
            "Hybrid Benchmark Metrics Summary",
            "=" * 60,
            "",
            f"Total Requests: {metrics.total_requests}",
            f"  - LLM: {metrics.llm_total_requests}",
            f"  - Embedding: {metrics.embedding_total_requests}",
            f"Duration: {metrics.duration_seconds:.2f}s",
            "",
            "Overall Performance:",
            f"  Throughput: {metrics.throughput_rps:.2f} req/s",
            f"  SLO Compliance: {metrics.slo_compliance_rate:.1%}",
            f"  Error Rate: {metrics.error_rate:.1%}",
            "",
            "LLM Performance:",
            f"  Throughput: {metrics.llm_throughput_rps:.2f} req/s",
            f"  Token Throughput: {metrics.llm_token_throughput_tps:.2f} tok/s",
            f"  TTFT (avg): {metrics.llm_ttft_avg_ms:.2f} ms",
            f"  E2E Latency (avg): {metrics.llm_e2e_latency_avg_ms:.2f} ms",
            f"  SLO Compliance: {metrics.llm_slo_compliance_rate:.1%}",
            "",
            "Embedding Performance:",
            f"  Throughput: {metrics.embedding_throughput_rps:.2f} req/s",
            f"  Texts/s: {metrics.embedding_throughput_texts_ps:.2f}",
            f"  Batch Efficiency: {metrics.embedding_batch_efficiency:.1%}",
            f"  E2E Latency (avg): {metrics.embedding_e2e_latency_avg_ms:.2f} ms",
            f"  SLO Compliance: {metrics.embedding_slo_compliance_rate:.1%}",
            "",
            "=" * 60,
        ]

        return "\n".join(lines)
