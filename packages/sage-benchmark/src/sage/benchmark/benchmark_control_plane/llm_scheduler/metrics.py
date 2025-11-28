# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
LLM Metrics Collection Module
=============================

Collects and aggregates performance metrics from LLM benchmark runs.

This module provides:
- LLMRequestMetrics: LLM-specific metrics dataclass
- LLMMetricsCollector: Aggregates metrics across LLM requests
- Statistical calculations for latency percentiles, throughput, SLO compliance
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..common.base_metrics import BaseMetricsCollector, BaseRequestMetrics


@dataclass
class LLMRequestMetrics(BaseRequestMetrics):
    """LLM-specific aggregated metrics for a set of requests.

    Extends BaseRequestMetrics with LLM-specific fields.

    Attributes:
        token_throughput_tps: Token throughput in tokens per second
        ttft_avg_ms: Average time to first token
        ttft_p50_ms: 50th percentile TTFT
        ttft_p95_ms: 95th percentile TTFT
        ttft_p99_ms: 99th percentile TTFT
        tbt_avg_ms: Average time between tokens
        tbt_p95_ms: 95th percentile TBT
        metrics_by_model: Metrics breakdown by model
    """

    # Token throughput
    token_throughput_tps: float = 0.0

    # TTFT
    ttft_avg_ms: float = 0.0
    ttft_p50_ms: float = 0.0
    ttft_p95_ms: float = 0.0
    ttft_p99_ms: float = 0.0

    # TBT (Time Between Tokens)
    tbt_avg_ms: float = 0.0
    tbt_p95_ms: float = 0.0

    # Model breakdown
    metrics_by_model: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        base = self.to_base_dict()
        base["throughput"]["tokens_per_second"] = self.token_throughput_tps
        base["ttft_ms"] = {
            "avg": self.ttft_avg_ms,
            "p50": self.ttft_p50_ms,
            "p95": self.ttft_p95_ms,
            "p99": self.ttft_p99_ms,
        }
        base["tbt_ms"] = {
            "avg": self.tbt_avg_ms,
            "p95": self.tbt_p95_ms,
        }
        base["metrics_by_model"] = self.metrics_by_model
        return base


class LLMMetricsCollector(BaseMetricsCollector):
    """Collects and aggregates metrics from LLM request results.

    This class takes raw LLMRequestResult objects and computes statistical
    aggregations including percentiles, throughput, and SLO compliance rates.
    """

    def compute_metrics(self) -> LLMRequestMetrics:
        """Compute aggregated metrics from collected results.

        Returns:
            LLMRequestMetrics with all computed statistics
        """
        if not self._results:
            return LLMRequestMetrics()

        # Start with base metrics
        base = self._compute_base_metrics()

        # Create LLM metrics and copy base values
        metrics = LLMRequestMetrics(
            total_requests=base.total_requests,
            completed_requests=base.completed_requests,
            failed_requests=base.failed_requests,
            timeout_requests=base.timeout_requests,
            duration_seconds=base.duration_seconds,
            throughput_rps=base.throughput_rps,
            e2e_latency_avg_ms=base.e2e_latency_avg_ms,
            e2e_latency_p50_ms=base.e2e_latency_p50_ms,
            e2e_latency_p95_ms=base.e2e_latency_p95_ms,
            e2e_latency_p99_ms=base.e2e_latency_p99_ms,
            e2e_latency_min_ms=base.e2e_latency_min_ms,
            e2e_latency_max_ms=base.e2e_latency_max_ms,
            slo_compliance_rate=base.slo_compliance_rate,
            slo_by_priority=base.slo_by_priority,
            error_rate=base.error_rate,
            timeout_rate=base.timeout_rate,
            metrics_by_priority=base.metrics_by_priority,
        )

        # Compute token throughput
        if metrics.duration_seconds > 0:
            total_tokens = sum(
                r.output_token_count for r in self._results if r.success
            )
            metrics.token_throughput_tps = total_tokens / metrics.duration_seconds

        # Compute TTFT statistics
        ttft_values = [
            r.ttft_ms for r in self._results if r.success and r.ttft_ms is not None
        ]
        if ttft_values:
            metrics.ttft_avg_ms = float(np.mean(ttft_values))
            metrics.ttft_p50_ms = float(np.percentile(ttft_values, 50))
            metrics.ttft_p95_ms = float(np.percentile(ttft_values, 95))
            metrics.ttft_p99_ms = float(np.percentile(ttft_values, 99))

        # Compute TBT statistics
        all_itls: list[float] = []
        for r in self._results:
            if r.success and hasattr(r, "inter_token_latencies") and r.inter_token_latencies:
                all_itls.extend(r.inter_token_latencies)

        if all_itls:
            metrics.tbt_avg_ms = float(np.mean(all_itls))
            metrics.tbt_p95_ms = float(np.percentile(all_itls, 95))

        # Breakdown by model
        metrics.metrics_by_model = self._compute_metrics_by_model()

        return metrics

    def _compute_metrics_by_model(self) -> dict[str, dict[str, Any]]:
        """Compute metrics grouped by model.

        Returns:
            Dictionary mapping model names to metrics
        """
        groups: dict[str, list] = {}

        for r in self._results:
            model_name = getattr(r, "model_name", "unknown")
            if model_name not in groups:
                groups[model_name] = []
            groups[model_name].append(r)

        result = {}
        for model_name, model_results in groups.items():
            success_results = [r for r in model_results if r.success]
            e2e_latencies = [
                r.e2e_latency_ms for r in success_results if r.e2e_latency_ms is not None
            ]
            ttft_values = [
                r.ttft_ms for r in success_results if hasattr(r, "ttft_ms") and r.ttft_ms is not None
            ]
            total_tokens = sum(
                r.output_token_count for r in success_results if hasattr(r, "output_token_count")
            )

            result[model_name] = {
                "total_requests": len(model_results),
                "completed_requests": len(success_results),
                "avg_latency_ms": float(np.mean(e2e_latencies)) if e2e_latencies else 0.0,
                "avg_ttft_ms": float(np.mean(ttft_values)) if ttft_values else 0.0,
                "total_tokens": total_tokens,
                "slo_compliance_rate": (
                    sum(1 for r in success_results if r.met_slo) / len(success_results)
                    if success_results
                    else 0.0
                ),
            }

        return result


# Backward compatibility aliases
RequestMetrics = LLMRequestMetrics
MetricsCollector = LLMMetricsCollector

__all__ = [
    "LLMRequestMetrics",
    "LLMMetricsCollector",
    # Backward compatibility
    "RequestMetrics",
    "MetricsCollector",
]
