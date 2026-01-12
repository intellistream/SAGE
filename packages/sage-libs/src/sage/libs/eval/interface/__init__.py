"""Evaluation interface layer for SAGE.

This module provides abstract interfaces for model evaluation components.
Concrete implementations are provided by external packages (e.g., isage-eval).

Architecture:
    - base.py: Abstract base classes (BaseMetric, BaseLLMJudge, BaseProfiler, BaseBenchmark)
    - factory.py: Registry and factory functions
    - External packages register their implementations at import time

Usage:
    # Option 1: Direct instantiation (if you know the implementation)
    from isage_eval import AccuracyMetric, FaithfulnessJudge
    metric = AccuracyMetric()
    judge = FaithfulnessJudge(model="gpt-4")

    # Option 2: Factory pattern (more flexible)
    from sage.libs.eval.interface import create_metric, create_judge
    metric = create_metric("accuracy")
    judge = create_judge("faithfulness", model="gpt-4")

    # Evaluate
    result = metric.compute(predictions, references)
    score = judge.judge(response, context=context)
"""

# Base classes and data types
from .base import (
    BaseBenchmark,
    BaseLLMJudge,
    BaseMetric,
    BaseProfiler,
    MetricResult,
    MetricType,
    ProfileResult,
)

# Factory functions
from .factory import (
    EvalRegistryError,
    create_benchmark,
    create_judge,
    create_metric,
    create_profiler,
    register_benchmark,
    register_judge,
    register_metric,
    register_profiler,
    registered_benchmarks,
    registered_judges,
    registered_metrics,
    registered_profilers,
    unregister_benchmark,
    unregister_judge,
    unregister_metric,
    unregister_profiler,
)

__all__ = [
    # Enums
    "MetricType",
    # Data types
    "MetricResult",
    "ProfileResult",
    # Base classes
    "BaseMetric",
    "BaseLLMJudge",
    "BaseProfiler",
    "BaseBenchmark",
    # Metric registry
    "register_metric",
    "create_metric",
    "registered_metrics",
    "unregister_metric",
    # Judge registry
    "register_judge",
    "create_judge",
    "registered_judges",
    "unregister_judge",
    # Profiler registry
    "register_profiler",
    "create_profiler",
    "registered_profilers",
    "unregister_profiler",
    # Benchmark registry
    "register_benchmark",
    "create_benchmark",
    "registered_benchmarks",
    "unregister_benchmark",
    # Exception
    "EvalRegistryError",
]
