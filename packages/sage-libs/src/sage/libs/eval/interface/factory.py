"""Factory and registry for evaluation implementations.

This module provides a registry pattern for evaluation components.
External packages (like isage-eval) can register their implementations here.

Example:
    # Register implementations
    from sage.libs.eval.interface import (
        register_metric,
        register_judge,
        register_profiler,
        register_benchmark,
    )
    register_metric("accuracy", AccuracyMetric)
    register_judge("faithfulness", FaithfulnessJudge)
    register_profiler("latency", LatencyProfiler)
    register_benchmark("rag_qa", RAGQABenchmark)

    # Create instances
    from sage.libs.eval.interface import (
        create_metric,
        create_judge,
        create_profiler,
        create_benchmark,
    )
    metric = create_metric("accuracy")
    judge = create_judge("faithfulness", model="gpt-4")
    profiler = create_profiler("latency")
    benchmark = create_benchmark("rag_qa")
"""

from typing import Any

from .base import BaseBenchmark, BaseLLMJudge, BaseMetric, BaseProfiler

_METRIC_REGISTRY: dict[str, type[BaseMetric]] = {}
_JUDGE_REGISTRY: dict[str, type[BaseLLMJudge]] = {}
_PROFILER_REGISTRY: dict[str, type[BaseProfiler]] = {}
_BENCHMARK_REGISTRY: dict[str, type[BaseBenchmark]] = {}


class EvalRegistryError(Exception):
    """Error raised when registry operations fail."""

    pass


# ========================================
# Metric Registry
# ========================================


def register_metric(name: str, cls: type[BaseMetric]) -> None:
    """Register an evaluation metric implementation.

    Args:
        name: Unique identifier (e.g., "accuracy", "bleu", "rouge")
        cls: Metric class (should inherit from BaseMetric)

    Raises:
        EvalRegistryError: If name already registered
    """
    if name in _METRIC_REGISTRY:
        raise EvalRegistryError(f"Metric '{name}' already registered")

    if not issubclass(cls, BaseMetric):
        raise TypeError(f"Class must inherit from BaseMetric, got {cls}")

    _METRIC_REGISTRY[name] = cls


def create_metric(name: str, **kwargs: Any) -> BaseMetric:
    """Create a metric instance by name.

    Args:
        name: Name of the registered metric
        **kwargs: Arguments to pass to the metric constructor

    Returns:
        Instance of the metric

    Raises:
        EvalRegistryError: If metric not found
    """
    if name not in _METRIC_REGISTRY:
        available = ", ".join(_METRIC_REGISTRY.keys()) if _METRIC_REGISTRY else "none"
        raise EvalRegistryError(
            f"Metric '{name}' not found. Available: {available}. Did you install 'isage-eval'?"
        )

    cls = _METRIC_REGISTRY[name]
    return cls(**kwargs)


def registered_metrics() -> list[str]:
    """Get list of registered metric names."""
    return list(_METRIC_REGISTRY.keys())


def unregister_metric(name: str) -> None:
    """Unregister a metric (for testing)."""
    _METRIC_REGISTRY.pop(name, None)


# ========================================
# LLM Judge Registry
# ========================================


def register_judge(name: str, cls: type[BaseLLMJudge]) -> None:
    """Register an LLM judge implementation.

    Args:
        name: Unique identifier (e.g., "faithfulness", "relevance", "coherence")
        cls: Judge class (should inherit from BaseLLMJudge)

    Raises:
        EvalRegistryError: If name already registered
    """
    if name in _JUDGE_REGISTRY:
        raise EvalRegistryError(f"Judge '{name}' already registered")

    if not issubclass(cls, BaseLLMJudge):
        raise TypeError(f"Class must inherit from BaseLLMJudge, got {cls}")

    _JUDGE_REGISTRY[name] = cls


def create_judge(name: str, **kwargs: Any) -> BaseLLMJudge:
    """Create a judge instance by name.

    Args:
        name: Name of the registered judge
        **kwargs: Arguments to pass to the judge constructor

    Returns:
        Instance of the judge

    Raises:
        EvalRegistryError: If judge not found
    """
    if name not in _JUDGE_REGISTRY:
        available = ", ".join(_JUDGE_REGISTRY.keys()) if _JUDGE_REGISTRY else "none"
        raise EvalRegistryError(
            f"Judge '{name}' not found. Available: {available}. Did you install 'isage-eval'?"
        )

    cls = _JUDGE_REGISTRY[name]
    return cls(**kwargs)


def registered_judges() -> list[str]:
    """Get list of registered judge names."""
    return list(_JUDGE_REGISTRY.keys())


def unregister_judge(name: str) -> None:
    """Unregister a judge (for testing)."""
    _JUDGE_REGISTRY.pop(name, None)


# ========================================
# Profiler Registry
# ========================================


def register_profiler(name: str, cls: type[BaseProfiler]) -> None:
    """Register a profiler implementation.

    Args:
        name: Unique identifier (e.g., "latency", "throughput", "memory", "gpu")
        cls: Profiler class (should inherit from BaseProfiler)

    Raises:
        EvalRegistryError: If name already registered
    """
    if name in _PROFILER_REGISTRY:
        raise EvalRegistryError(f"Profiler '{name}' already registered")

    if not issubclass(cls, BaseProfiler):
        raise TypeError(f"Class must inherit from BaseProfiler, got {cls}")

    _PROFILER_REGISTRY[name] = cls


def create_profiler(name: str, **kwargs: Any) -> BaseProfiler:
    """Create a profiler instance by name.

    Args:
        name: Name of the registered profiler
        **kwargs: Arguments to pass to the profiler constructor

    Returns:
        Instance of the profiler

    Raises:
        EvalRegistryError: If profiler not found
    """
    if name not in _PROFILER_REGISTRY:
        available = ", ".join(_PROFILER_REGISTRY.keys()) if _PROFILER_REGISTRY else "none"
        raise EvalRegistryError(
            f"Profiler '{name}' not found. Available: {available}. Did you install 'isage-eval'?"
        )

    cls = _PROFILER_REGISTRY[name]
    return cls(**kwargs)


def registered_profilers() -> list[str]:
    """Get list of registered profiler names."""
    return list(_PROFILER_REGISTRY.keys())


def unregister_profiler(name: str) -> None:
    """Unregister a profiler (for testing)."""
    _PROFILER_REGISTRY.pop(name, None)


# ========================================
# Benchmark Registry
# ========================================


def register_benchmark(name: str, cls: type[BaseBenchmark]) -> None:
    """Register a benchmark implementation.

    Args:
        name: Unique identifier (e.g., "rag_qa", "agent_tool_use", "latency")
        cls: Benchmark class (should inherit from BaseBenchmark)

    Raises:
        EvalRegistryError: If name already registered
    """
    if name in _BENCHMARK_REGISTRY:
        raise EvalRegistryError(f"Benchmark '{name}' already registered")

    if not issubclass(cls, BaseBenchmark):
        raise TypeError(f"Class must inherit from BaseBenchmark, got {cls}")

    _BENCHMARK_REGISTRY[name] = cls


def create_benchmark(name: str, **kwargs: Any) -> BaseBenchmark:
    """Create a benchmark instance by name.

    Args:
        name: Name of the registered benchmark
        **kwargs: Arguments to pass to the benchmark constructor

    Returns:
        Instance of the benchmark

    Raises:
        EvalRegistryError: If benchmark not found
    """
    if name not in _BENCHMARK_REGISTRY:
        available = ", ".join(_BENCHMARK_REGISTRY.keys()) if _BENCHMARK_REGISTRY else "none"
        raise EvalRegistryError(
            f"Benchmark '{name}' not found. Available: {available}. Did you install 'isage-eval'?"
        )

    cls = _BENCHMARK_REGISTRY[name]
    return cls(**kwargs)


def registered_benchmarks() -> list[str]:
    """Get list of registered benchmark names."""
    return list(_BENCHMARK_REGISTRY.keys())


def unregister_benchmark(name: str) -> None:
    """Unregister a benchmark (for testing)."""
    _BENCHMARK_REGISTRY.pop(name, None)


__all__ = [
    "EvalRegistryError",
    # Metric
    "register_metric",
    "create_metric",
    "registered_metrics",
    "unregister_metric",
    # Judge
    "register_judge",
    "create_judge",
    "registered_judges",
    "unregister_judge",
    # Profiler
    "register_profiler",
    "create_profiler",
    "registered_profilers",
    "unregister_profiler",
    # Benchmark
    "register_benchmark",
    "create_benchmark",
    "registered_benchmarks",
    "unregister_benchmark",
]
