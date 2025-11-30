# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Base Metrics Module
===================

Provides base metrics classes that can be extended for both
LLM-only and hybrid scheduling benchmarks.

This module provides:
- BaseRequestResult: Base class for request results
- BaseRequestMetrics: Base class for aggregated metrics
- BaseMetricsCollector: Base class for metrics collection
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class BaseRequestResult:
    """Base result of a single benchmark request.

    Attributes:
        request_id: Unique request identifier
        priority: Request priority
        slo_deadline_ms: SLO deadline in milliseconds

        send_time: Time when request was sent (epoch seconds)
        completion_time: Time when request completed (epoch seconds)

        success: Whether the request succeeded
        error: Error message if request failed
        status_code: HTTP status code

        metadata: Additional metadata from the request
    """

    request_id: str
    priority: str
    slo_deadline_ms: int

    send_time: float = 0.0
    completion_time: float | None = None

    success: bool = False
    error: str | None = None
    status_code: int | None = None

    metadata: dict = field(default_factory=dict)

    @property
    def e2e_latency_ms(self) -> float | None:
        """End-to-end latency in milliseconds."""
        if self.send_time is not None and self.completion_time is not None:
            return (self.completion_time - self.send_time) * 1000
        return None

    @property
    def met_slo(self) -> bool:
        """Whether the request met its SLO deadline."""
        e2e = self.e2e_latency_ms
        if e2e is None:
            return False
        return e2e <= self.slo_deadline_ms

    def to_base_dict(self) -> dict[str, Any]:
        """Convert base result to dictionary."""
        return {
            "request_id": self.request_id,
            "priority": self.priority,
            "slo_deadline_ms": self.slo_deadline_ms,
            "send_time": self.send_time,
            "completion_time": self.completion_time,
            "e2e_latency_ms": self.e2e_latency_ms,
            "success": self.success,
            "error": self.error,
            "status_code": self.status_code,
            "met_slo": self.met_slo,
            "metadata": self.metadata,
        }


@dataclass
class BaseRequestMetrics:
    """Base aggregated metrics for a set of requests.

    Attributes:
        total_requests: Total number of requests
        completed_requests: Number of successfully completed requests
        failed_requests: Number of failed requests
        timeout_requests: Number of timed out requests

        duration_seconds: Total benchmark duration in seconds
        throughput_rps: Throughput in requests per second

        e2e_latency_avg_ms: Average end-to-end latency
        e2e_latency_p50_ms: 50th percentile (median) E2E latency
        e2e_latency_p95_ms: 95th percentile E2E latency
        e2e_latency_p99_ms: 99th percentile E2E latency
        e2e_latency_min_ms: Minimum E2E latency
        e2e_latency_max_ms: Maximum E2E latency

        slo_compliance_rate: Fraction of requests meeting SLO
        slo_by_priority: SLO compliance by priority level

        error_rate: Fraction of requests that failed
        timeout_rate: Fraction of requests that timed out

        metrics_by_priority: Metrics breakdown by priority
    """

    # Request counts
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0

    # Throughput
    duration_seconds: float = 0.0
    throughput_rps: float = 0.0

    # E2E Latency
    e2e_latency_avg_ms: float = 0.0
    e2e_latency_p50_ms: float = 0.0
    e2e_latency_p95_ms: float = 0.0
    e2e_latency_p99_ms: float = 0.0
    e2e_latency_min_ms: float = 0.0
    e2e_latency_max_ms: float = 0.0

    # SLO
    slo_compliance_rate: float = 0.0
    slo_by_priority: dict[str, float] = field(default_factory=dict)

    # Errors
    error_rate: float = 0.0
    timeout_rate: float = 0.0

    # Breakdown
    metrics_by_priority: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_base_dict(self) -> dict[str, Any]:
        """Convert base metrics to dictionary."""
        return {
            "request_counts": {
                "total": self.total_requests,
                "completed": self.completed_requests,
                "failed": self.failed_requests,
                "timeout": self.timeout_requests,
            },
            "throughput": {
                "duration_seconds": self.duration_seconds,
                "requests_per_second": self.throughput_rps,
            },
            "e2e_latency_ms": {
                "avg": self.e2e_latency_avg_ms,
                "p50": self.e2e_latency_p50_ms,
                "p95": self.e2e_latency_p95_ms,
                "p99": self.e2e_latency_p99_ms,
                "min": self.e2e_latency_min_ms,
                "max": self.e2e_latency_max_ms,
            },
            "slo": {
                "compliance_rate": self.slo_compliance_rate,
                "by_priority": self.slo_by_priority,
            },
            "errors": {
                "error_rate": self.error_rate,
                "timeout_rate": self.timeout_rate,
            },
            "metrics_by_priority": self.metrics_by_priority,
        }


class BaseMetricsCollector(ABC):
    """Base class for metrics collection and aggregation.

    This class takes raw request result objects and computes statistical
    aggregations including percentiles, throughput, and SLO compliance rates.
    """

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self._results: list = []
        self._start_time: float | None = None
        self._end_time: float | None = None

    def set_time_range(self, start_time: float, end_time: float) -> None:
        """Set the benchmark time range.

        Args:
            start_time: Benchmark start time (epoch seconds)
            end_time: Benchmark end time (epoch seconds)
        """
        self._start_time = start_time
        self._end_time = end_time

    def add_result(self, result: Any) -> None:
        """Add a request result to the collector.

        Args:
            result: RequestResult object
        """
        self._results.append(result)

    def add_results(self, results: list) -> None:
        """Add multiple request results.

        Args:
            results: List of RequestResult objects
        """
        self._results.extend(results)

    def clear(self) -> None:
        """Clear all collected results."""
        self._results = []
        self._start_time = None
        self._end_time = None

    @property
    def results(self) -> list:
        """Get collected results."""
        return self._results

    def _compute_base_metrics(self) -> BaseRequestMetrics:
        """Compute base aggregated metrics from collected results.

        Returns:
            BaseRequestMetrics with computed statistics
        """
        if not self._results:
            return BaseRequestMetrics()

        metrics = BaseRequestMetrics()

        # Count requests
        metrics.total_requests = len(self._results)
        metrics.completed_requests = sum(1 for r in self._results if r.success)
        metrics.failed_requests = sum(
            1 for r in self._results if not r.success and r.error != "Request timed out"
        )
        metrics.timeout_requests = sum(1 for r in self._results if r.error == "Request timed out")

        # Compute duration and throughput
        if self._start_time and self._end_time:
            metrics.duration_seconds = self._end_time - self._start_time
        else:
            # Estimate from request times
            send_times = [r.send_time for r in self._results if r.send_time]
            completion_times = [r.completion_time for r in self._results if r.completion_time]
            if send_times and completion_times:
                metrics.duration_seconds = max(completion_times) - min(send_times)

        if metrics.duration_seconds > 0:
            metrics.throughput_rps = metrics.completed_requests / metrics.duration_seconds

        # Compute E2E latency statistics
        e2e_latencies = [
            r.e2e_latency_ms for r in self._results if r.success and r.e2e_latency_ms is not None
        ]
        if e2e_latencies:
            metrics.e2e_latency_avg_ms = float(np.mean(e2e_latencies))
            metrics.e2e_latency_p50_ms = float(np.percentile(e2e_latencies, 50))
            metrics.e2e_latency_p95_ms = float(np.percentile(e2e_latencies, 95))
            metrics.e2e_latency_p99_ms = float(np.percentile(e2e_latencies, 99))
            metrics.e2e_latency_min_ms = float(np.min(e2e_latencies))
            metrics.e2e_latency_max_ms = float(np.max(e2e_latencies))

        # Compute SLO compliance
        slo_met = sum(1 for r in self._results if r.success and r.met_slo)
        if metrics.completed_requests > 0:
            metrics.slo_compliance_rate = slo_met / metrics.completed_requests

        # SLO by priority
        metrics.slo_by_priority = self._compute_slo_by_priority()

        # Error and timeout rates
        if metrics.total_requests > 0:
            metrics.error_rate = metrics.failed_requests / metrics.total_requests
            metrics.timeout_rate = metrics.timeout_requests / metrics.total_requests

        # Breakdown by priority
        metrics.metrics_by_priority = self._compute_metrics_by_group("priority")

        return metrics

    def _compute_slo_by_priority(self) -> dict[str, float]:
        """Compute SLO compliance rate by priority level.

        Returns:
            Dictionary mapping priority to compliance rate
        """
        priority_stats: dict[str, dict[str, int]] = {}

        for r in self._results:
            if not r.success:
                continue

            priority = r.priority
            if priority not in priority_stats:
                priority_stats[priority] = {"total": 0, "met_slo": 0}

            priority_stats[priority]["total"] += 1
            if r.met_slo:
                priority_stats[priority]["met_slo"] += 1

        result = {}
        for priority, stats in priority_stats.items():
            if stats["total"] > 0:
                result[priority] = stats["met_slo"] / stats["total"]
            else:
                result[priority] = 0.0

        return result

    def _compute_metrics_by_group(self, group_field: str) -> dict[str, dict[str, Any]]:
        """Compute basic metrics grouped by a field.

        Args:
            group_field: Field name to group by (e.g., "priority")

        Returns:
            Dictionary mapping group values to metrics
        """
        groups: dict[str, list] = {}

        for r in self._results:
            group_value = getattr(r, group_field, "unknown")
            if group_value not in groups:
                groups[group_value] = []
            groups[group_value].append(r)

        result = {}
        for group_value, group_results in groups.items():
            success_results = [r for r in group_results if r.success]
            e2e_latencies = [
                r.e2e_latency_ms for r in success_results if r.e2e_latency_ms is not None
            ]

            result[group_value] = {
                "total_requests": len(group_results),
                "completed_requests": len(success_results),
                "avg_latency_ms": float(np.mean(e2e_latencies)) if e2e_latencies else 0.0,
                "slo_compliance_rate": (
                    sum(1 for r in success_results if r.met_slo) / len(success_results)
                    if success_results
                    else 0.0
                ),
            }

        return result

    @abstractmethod
    def compute_metrics(self) -> BaseRequestMetrics:
        """Compute aggregated metrics from collected results.

        Subclasses should call _compute_base_metrics() and add type-specific metrics.

        Returns:
            Metrics object with all computed statistics
        """
        pass
