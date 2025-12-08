# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
LLM Scheduler Benchmark Module
==============================

Benchmarking tools for evaluating LLM-only scheduling policies
in sageLLM's Control Plane.

This module provides:
- LLMBenchmarkConfig: LLM-specific benchmark configuration
- LLMWorkloadGenerator: LLM request workload generation
- LLMBenchmarkClient: Async HTTP client for LLM requests
- LLMMetricsCollector: LLM-specific metrics collection
- LLMBenchmarkRunner: Benchmark execution orchestration
- LLMBenchmarkReporter: Results output and visualization

Usage:
------
    from sage.benchmark.benchmark_control_plane.llm_scheduler import (
        LLMBenchmarkConfig,
        LLMBenchmarkRunner,
    )

    config = LLMBenchmarkConfig(
        control_plane_url="http://localhost:8888",
        policies=["fifo", "priority", "slo_aware"],
        num_requests=1000,
    )
    runner = LLMBenchmarkRunner(config)
    results = await runner.run()
"""

from .client import LLMBenchmarkClient, LLMRequestResult
from .config import LLMBenchmarkConfig, LLMSLOConfig
from .metrics import LLMMetricsCollector, LLMRequestMetrics
from .reporter import LLMBenchmarkReporter
from .runner import LLMBenchmarkResult, LLMBenchmarkRunner, LLMPolicyResult
from .workload import LLMRequest, LLMWorkloadGenerator

__all__ = [
    # Config
    "LLMBenchmarkConfig",
    "LLMSLOConfig",
    # Workload
    "LLMRequest",
    "LLMWorkloadGenerator",
    # Client
    "LLMBenchmarkClient",
    "LLMRequestResult",
    # Metrics
    "LLMRequestMetrics",
    "LLMMetricsCollector",
    # Runner
    "LLMBenchmarkRunner",
    "LLMPolicyResult",
    "LLMBenchmarkResult",
    # Reporter
    "LLMBenchmarkReporter",
]
