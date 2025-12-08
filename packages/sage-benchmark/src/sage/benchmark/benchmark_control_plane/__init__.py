# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project
"""
benchmark_control_plane - sageLLM Scheduling Policy Benchmark
==============================================================

This module provides benchmarking tools for evaluating different scheduling policies
in sageLLM's Control Plane. It measures performance metrics like latency, throughput,
and SLO compliance across various scheduling strategies.

Module Structure (Post-Refactor):
---------------------------------
- common/: Shared base classes and utilities
    - base_config: Base configuration classes
    - base_metrics: Base metrics collection classes
    - gpu_monitor: GPU monitoring utilities
    - strategy_adapter: Scheduling strategy interface
- llm_scheduler/: LLM-specific benchmark implementation
    - config: LLM benchmark configuration
    - workload: LLM workload generation
    - client: LLM benchmark client
    - metrics: LLM metrics collection
    - runner: LLM benchmark runner
    - reporter: LLM results reporting
- visualization/: Report generation and visualization
    - templates/: HTML templates for reports
- experiments/: Predefined experiment templates (Task 5)
- hybrid_scheduler/: Hybrid LLM+Embedding scheduler (Task 3)

Usage:
------
From command line:
    sage-cp-bench run --control-plane http://localhost:8888 --policy aegaeon --requests 1000

From Python:
    from sage.benchmark.benchmark_control_plane import BenchmarkRunner, BenchmarkConfig
    config = BenchmarkConfig(control_plane_url="http://localhost:8888", ...)
    runner = BenchmarkRunner(config)
    results = await runner.run()

Or use the new prefixed names:
    from sage.benchmark.benchmark_control_plane.llm_scheduler import (
        LLMBenchmarkRunner,
        LLMBenchmarkConfig,
    )

Supported Scheduling Policies:
- fifo: First-In-First-Out scheduling
- priority: Priority-based scheduling
- slo_aware: SLO-deadline aware scheduling
- cost_optimized: Cost-optimized scheduling
- adaptive: Adaptive scheduling based on system state
- aegaeon: Advanced scheduling with multiple optimizations
- hybrid: Hybrid scheduling for mixed LLM/Embedding workloads
"""

# =============================================================================
# Common components (shared across all scheduler types)
# =============================================================================
from .common import (
    # Base configuration
    ArrivalPattern,
    BaseBenchmarkConfig,
    BaseMetricsCollector,
    # Base metrics
    BaseRequestMetrics,
    BaseRequestResult,
    BaseSLOConfig,
    # GPU monitoring
    GPUMetrics,
    GPUMonitor,
    SchedulingPolicy,
    # Strategy adapter
    StrategyAdapter,
)

# =============================================================================
# LLM Scheduler components (backward compatible imports)
# =============================================================================
from .llm_scheduler import (
    # New prefixed names
    LLMBenchmarkClient,
    LLMBenchmarkConfig,
    LLMBenchmarkReporter,
    LLMBenchmarkResult,
    LLMBenchmarkRunner,
    LLMMetricsCollector,
    LLMPolicyResult,
    LLMRequest,
    LLMRequestMetrics,
    LLMRequestResult,
    LLMSLOConfig,
    LLMWorkloadGenerator,
)

# =============================================================================
# Backward compatibility aliases (deprecated, use LLM* versions)
# =============================================================================
# These maintain API compatibility with existing code
BenchmarkConfig = LLMBenchmarkConfig
BenchmarkClient = LLMBenchmarkClient
MetricsCollector = LLMMetricsCollector
RequestMetrics = LLMRequestMetrics
BenchmarkRunner = LLMBenchmarkRunner
BenchmarkReporter = LLMBenchmarkReporter
WorkloadGenerator = LLMWorkloadGenerator

# =============================================================================
# Public API
# =============================================================================
__all__ = [
    # -------------------------------------------------------------------------
    # Common components
    # -------------------------------------------------------------------------
    # Base configuration
    "BaseBenchmarkConfig",
    "BaseSLOConfig",
    "ArrivalPattern",
    "SchedulingPolicy",
    # Base metrics
    "BaseRequestResult",
    "BaseRequestMetrics",
    "BaseMetricsCollector",
    # GPU monitoring
    "GPUMonitor",
    "GPUMetrics",
    # Strategy adapter
    "StrategyAdapter",
    # -------------------------------------------------------------------------
    # LLM Scheduler (new prefixed names)
    # -------------------------------------------------------------------------
    "LLMBenchmarkConfig",
    "LLMSLOConfig",
    "LLMRequest",
    "LLMWorkloadGenerator",
    "LLMBenchmarkClient",
    "LLMRequestResult",
    "LLMMetricsCollector",
    "LLMRequestMetrics",
    "LLMBenchmarkRunner",
    "LLMPolicyResult",
    "LLMBenchmarkResult",
    "LLMBenchmarkReporter",
    # -------------------------------------------------------------------------
    # Backward compatibility aliases (deprecated)
    # -------------------------------------------------------------------------
    "BenchmarkConfig",
    "BenchmarkClient",
    "MetricsCollector",
    "RequestMetrics",
    "BenchmarkRunner",
    "BenchmarkReporter",
    "WorkloadGenerator",
]
