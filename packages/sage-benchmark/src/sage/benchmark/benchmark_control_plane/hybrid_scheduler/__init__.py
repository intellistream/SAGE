# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Hybrid Scheduler Benchmark Module
==================================

Benchmarking tools for evaluating hybrid (LLM + Embedding) scheduling policies
in sageLLM's Control Plane.

This module provides:
- HybridBenchmarkConfig: Hybrid-specific benchmark configuration
- HybridSLOConfig: SLO configuration with embedding support
- RequestType: Enum for request types (LLM_CHAT, LLM_GENERATE, EMBEDDING)
- HybridRequest: Request data class for mixed workloads
- HybridWorkloadGenerator: Mixed LLM/Embedding workload generation
- HybridBenchmarkClient: Client supporting both LLM and Embedding requests
- HybridRequestResult: Result data class for hybrid requests
- HybridRequestMetrics: Aggregated metrics for hybrid benchmark runs
- HybridMetricsCollector: Metrics collection for mixed workloads
- HybridBenchmarkRunner: Benchmark execution orchestration
- HybridPolicyResult: Results for a single policy run
- HybridBenchmarkResult: Complete benchmark results
- HybridBenchmarkReporter: Results output and visualization
"""

from .client import HybridBenchmarkClient, HybridRequestResult
from .config import HybridBenchmarkConfig, HybridSLOConfig, RequestType
from .metrics import HybridMetricsCollector, HybridRequestMetrics
from .reporter import HybridBenchmarkReporter
from .runner import HybridBenchmarkResult, HybridBenchmarkRunner, HybridPolicyResult
from .workload import HybridRequest, HybridWorkloadGenerator

__all__ = [
    # Config (Task 3A)
    "HybridBenchmarkConfig",
    "HybridSLOConfig",
    "RequestType",
    # Workload (Task 3A)
    "HybridRequest",
    "HybridWorkloadGenerator",
    # Client (Task 3A)
    "HybridBenchmarkClient",
    "HybridRequestResult",
    # Metrics (Task 3B)
    "HybridRequestMetrics",
    "HybridMetricsCollector",
    # Runner (Task 3B)
    "HybridBenchmarkRunner",
    "HybridPolicyResult",
    "HybridBenchmarkResult",
    # Reporter (Task 3B)
    "HybridBenchmarkReporter",
]
