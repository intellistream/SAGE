"""Evaluation module for SAGE.

This module provides the evaluation interface layer for model and pipeline evaluation.
Concrete implementations are provided by external packages (e.g., isage-eval).

Features:
- Evaluation metrics (Accuracy, BLEU, ROUGE, F1, etc.)
- LLM-as-a-Judge evaluation (Faithfulness, Relevance, Coherence)
- Performance profiling (Latency, Throughput, Memory)
- Benchmark suites (RAG, Agent, End-to-end)

Usage:
    from sage.libs.eval import (
        BaseMetric, BaseLLMJudge, BaseProfiler, BaseBenchmark,
        create_metric, create_judge, create_profiler, create_benchmark,
        MetricResult, MetricType
    )
"""

from .interface import (
    # Enums
    MetricType,
    # Data types
    MetricResult,
    ProfileResult,
    # Base classes
    BaseBenchmark,
    BaseLLMJudge,
    BaseMetric,
    BaseProfiler,
    # Metric registry
    create_metric,
    register_metric,
    registered_metrics,
    # Judge registry
    create_judge,
    register_judge,
    registered_judges,
    # Profiler registry
    create_profiler,
    register_profiler,
    registered_profilers,
    # Benchmark registry
    create_benchmark,
    register_benchmark,
    registered_benchmarks,
    # Exception
    EvalRegistryError,
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
    # Judge registry
    "register_judge",
    "create_judge",
    "registered_judges",
    # Profiler registry
    "register_profiler",
    "create_profiler",
    "registered_profilers",
    # Benchmark registry
    "register_benchmark",
    "create_benchmark",
    "registered_benchmarks",
    # Exception
    "EvalRegistryError",
]
