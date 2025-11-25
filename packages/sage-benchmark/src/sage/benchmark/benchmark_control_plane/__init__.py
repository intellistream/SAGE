"""
benchmark_control_plane - sageLLM Scheduling Policy Benchmark
==============================================================

This module provides benchmarking tools for evaluating different scheduling policies
in sageLLM's Control Plane. It measures performance metrics like latency, throughput,
and SLO compliance across various scheduling strategies.

Components:
-----------
- config: Benchmark configuration and parameter definitions
- workload: Workload generation (synthetic and dataset-based)
- client: Async HTTP client for Control Plane communication
- metrics: Performance metrics collection and aggregation
- runner: Benchmark execution orchestration
- reporter: Results output and visualization
- cli: Command line interface

Usage:
------
From command line:
    sage-bench run --control-plane http://localhost:8080 --policy aegaeon --requests 1000

From Python:
    from sage.benchmark.benchmark_control_plane import BenchmarkRunner, BenchmarkConfig
    config = BenchmarkConfig(control_plane_url="http://localhost:8080", ...)
    runner = BenchmarkRunner(config)
    results = await runner.run()

Supported Scheduling Policies:
- fifo: First-In-First-Out scheduling
- priority: Priority-based scheduling
- slo_aware: SLO-deadline aware scheduling
- cost_optimized: Cost-optimized scheduling
- adaptive: Adaptive scheduling based on system state
- aegaeon: Advanced scheduling with multiple optimizations
"""

from .client import BenchmarkClient
from .config import BenchmarkConfig
from .metrics import MetricsCollector, RequestMetrics
from .reporter import BenchmarkReporter
from .runner import BenchmarkRunner
from .workload import WorkloadGenerator

__all__ = [
    "BenchmarkConfig",
    "BenchmarkClient",
    "MetricsCollector",
    "RequestMetrics",
    "BenchmarkRunner",
    "BenchmarkReporter",
    "WorkloadGenerator",
]
