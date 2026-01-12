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
    # Base classes
    BaseBenchmark,
    BaseLLMJudge,
    BaseMetric,
    BaseProfiler,
    # Exception
    EvalRegistryError,
    # Data types
    MetricResult,
    # Enums
    MetricType,
    ProfileResult,
    # Benchmark registry
    create_benchmark,
    # Judge registry
    create_judge,
    # Metric registry
    create_metric,
    # Profiler registry
    create_profiler,
    register_benchmark,
    register_judge,
    register_metric,
    register_profiler,
    registered_benchmarks,
    registered_judges,
    registered_metrics,
    registered_profilers,
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
