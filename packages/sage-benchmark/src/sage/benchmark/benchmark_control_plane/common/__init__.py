# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Common components for Control Plane Benchmark
==============================================

This module provides shared components for both LLM-only and hybrid
(LLM + Embedding) scheduling benchmarks.

Components:
-----------
- base_config: Base configuration classes
- base_metrics: Base metrics classes
- gpu_monitor: GPU resource monitoring
- strategy_adapter: Adapter for control_plane/strategies/
"""

from .base_config import (
    ArrivalPattern,
    BaseBenchmarkConfig,
    BaseSLOConfig,
    SchedulingPolicy,
)
from .base_metrics import (
    BaseMetricsCollector,
    BaseRequestMetrics,
    BaseRequestResult,
)
from .gpu_monitor import GPUMetrics, GPUMonitor
from .strategy_adapter import StrategyAdapter

__all__ = [
    # Base config
    "BaseBenchmarkConfig",
    "BaseSLOConfig",
    "ArrivalPattern",
    "SchedulingPolicy",
    # Base metrics
    "BaseRequestMetrics",
    "BaseRequestResult",
    "BaseMetricsCollector",
    # GPU Monitor
    "GPUMonitor",
    "GPUMetrics",
    # Strategy Adapter
    "StrategyAdapter",
]
