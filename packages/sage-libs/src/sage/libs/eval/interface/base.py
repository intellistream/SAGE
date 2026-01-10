"""Base classes and interfaces for evaluation.

This module defines abstract interfaces for model evaluation:
- BaseMetric: Evaluation metric base class
- BaseProfiler: Performance profiling base class
- BaseBenchmark: Benchmark suite base class
- MetricResult: Standardized metric result

Implementations are provided by the external 'isage-eval' package.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MetricType(Enum):
    """Types of evaluation metrics."""

    # Text/NLP metrics
    ACCURACY = "accuracy"
    F1_SCORE = "f1_score"
    PRECISION = "precision"
    RECALL = "recall"
    BLEU = "bleu"
    ROUGE = "rouge"
    METEOR = "meteor"
    BERT_SCORE = "bert_score"
    PERPLEXITY = "perplexity"

    # LLM-specific metrics
    FAITHFULNESS = "faithfulness"
    RELEVANCE = "relevance"
    COHERENCE = "coherence"
    FLUENCY = "fluency"
    TOXICITY = "toxicity"
    BIAS = "bias"

    # Retrieval metrics
    MRR = "mrr"  # Mean Reciprocal Rank
    NDCG = "ndcg"  # Normalized Discounted Cumulative Gain
    MAP = "map"  # Mean Average Precision
    HIT_RATE = "hit_rate"

    # Performance metrics
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY_USAGE = "memory_usage"
    FLOPS = "flops"

    # Custom
    CUSTOM = "custom"


@dataclass
class MetricResult:
    """Standardized metric evaluation result."""

    name: str
    value: float
    metric_type: MetricType = MetricType.CUSTOM

    # Optional details
    confidence_interval: Optional[tuple[float, float]] = None
    sample_size: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"{self.name}: {self.value:.4f}"


@dataclass
class ProfileResult:
    """Performance profiling result."""

    # Timing
    total_time_ms: float
    mean_latency_ms: float
    p50_latency_ms: float
    p90_latency_ms: float
    p99_latency_ms: float

    # Throughput
    samples_per_second: float
    tokens_per_second: Optional[float] = None

    # Resource usage
    peak_memory_mb: Optional[float] = None
    avg_gpu_utilization: Optional[float] = None

    # Metadata
    num_samples: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseMetric(ABC):
    """Abstract base class for evaluation metrics.

    Examples of implementations:
    - AccuracyMetric: Classification accuracy
    - BLEUMetric: BLEU score for text generation
    - ROUGEMetric: ROUGE scores for summarization
    - FaithfulnessMetric: LLM-as-judge faithfulness
    - RelevanceMetric: RAG retrieval relevance
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the metric name."""
        pass

    @property
    def metric_type(self) -> MetricType:
        """Return the metric type."""
        return MetricType.CUSTOM

    @abstractmethod
    def compute(
        self,
        predictions: list[Any],
        references: list[Any],
        **kwargs: Any,
    ) -> MetricResult:
        """Compute the metric value.

        Args:
            predictions: Model predictions/outputs
            references: Ground truth references
            **kwargs: Metric-specific parameters

        Returns:
            MetricResult with computed value and metadata
        """
        pass

    def compute_batch(
        self,
        predictions: list[Any],
        references: list[Any],
        batch_size: int = 32,
        **kwargs: Any,
    ) -> MetricResult:
        """Compute metric over large datasets in batches.

        Default implementation calls compute() once.
        Override for more efficient batch processing.

        Args:
            predictions: All predictions
            references: All references
            batch_size: Batch size for processing
            **kwargs: Additional parameters

        Returns:
            Aggregated MetricResult
        """
        return self.compute(predictions, references, **kwargs)

    def supports_streaming(self) -> bool:
        """Whether this metric supports streaming computation."""
        return False


class BaseLLMJudge(ABC):
    """Abstract base class for LLM-as-a-Judge evaluation.

    Uses an LLM to evaluate quality of generated text.

    Examples of implementations:
    - FaithfulnessJudge: Evaluate factual accuracy
    - RelevanceJudge: Evaluate answer relevance
    - CoherenceJudge: Evaluate text coherence
    - SafetyJudge: Evaluate content safety
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the judge name."""
        pass

    @property
    @abstractmethod
    def criteria(self) -> str:
        """Return the evaluation criteria description."""
        pass

    @abstractmethod
    def judge(
        self,
        response: str,
        context: Optional[str] = None,
        question: Optional[str] = None,
        reference: Optional[str] = None,
        **kwargs: Any,
    ) -> MetricResult:
        """Judge a single response.

        Args:
            response: The response to evaluate
            context: Optional context/documents used
            question: Optional original question
            reference: Optional reference answer
            **kwargs: Additional parameters

        Returns:
            MetricResult with score and reasoning
        """
        pass

    def judge_batch(
        self,
        responses: list[str],
        contexts: Optional[list[str]] = None,
        questions: Optional[list[str]] = None,
        references: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> list[MetricResult]:
        """Judge multiple responses.

        Default implementation calls judge() for each response.
        Override for batch LLM calls.

        Args:
            responses: Responses to evaluate
            contexts: Corresponding contexts
            questions: Corresponding questions
            references: Corresponding references
            **kwargs: Additional parameters

        Returns:
            List of MetricResults
        """
        results = []
        contexts = contexts or [None] * len(responses)
        questions = questions or [None] * len(responses)
        references = references or [None] * len(responses)

        for resp, ctx, q, ref in zip(responses, contexts, questions, references):
            results.append(self.judge(resp, ctx, q, ref, **kwargs))

        return results


class BaseProfiler(ABC):
    """Abstract base class for performance profiling.

    Examples of implementations:
    - LatencyProfiler: Measure inference latency
    - ThroughputProfiler: Measure throughput (samples/sec)
    - MemoryProfiler: Track memory usage
    - GPUProfiler: Monitor GPU utilization
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the profiler name."""
        pass

    @abstractmethod
    def start(self) -> None:
        """Start profiling."""
        pass

    @abstractmethod
    def stop(self) -> ProfileResult:
        """Stop profiling and return results.

        Returns:
            ProfileResult with timing and resource metrics
        """
        pass

    def profile(self, func: Any, *args: Any, **kwargs: Any) -> tuple[Any, ProfileResult]:
        """Profile a function call.

        Args:
            func: Function to profile
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Tuple of (function result, ProfileResult)
        """
        self.start()
        result = func(*args, **kwargs)
        profile_result = self.stop()
        return result, profile_result

    def warmup(self, func: Any, num_warmup: int = 3, *args: Any, **kwargs: Any) -> None:
        """Run warmup iterations before profiling.

        Args:
            func: Function to warm up
            num_warmup: Number of warmup iterations
            *args: Function arguments
            **kwargs: Function keyword arguments
        """
        for _ in range(num_warmup):
            func(*args, **kwargs)


class BaseBenchmark(ABC):
    """Abstract base class for benchmark suites.

    Examples of implementations:
    - RAGBenchmark: Evaluate RAG pipeline quality
    - AgentBenchmark: Evaluate agent capabilities
    - LatencyBenchmark: Compare model latencies
    - AccuracyBenchmark: Compare model accuracies
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the benchmark name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return the benchmark description."""
        pass

    @abstractmethod
    def run(self, model: Any, **kwargs: Any) -> dict[str, MetricResult]:
        """Run the benchmark on a model.

        Args:
            model: Model to benchmark
            **kwargs: Benchmark-specific parameters

        Returns:
            Dictionary mapping metric names to results
        """
        pass

    def compare(
        self,
        models: dict[str, Any],
        **kwargs: Any,
    ) -> dict[str, dict[str, MetricResult]]:
        """Compare multiple models on the benchmark.

        Args:
            models: Dictionary mapping model names to model instances
            **kwargs: Benchmark parameters

        Returns:
            Nested dict: model_name -> metric_name -> MetricResult
        """
        results = {}
        for model_name, model in models.items():
            results[model_name] = self.run(model, **kwargs)
        return results

    def get_leaderboard(
        self,
        results: dict[str, dict[str, MetricResult]],
        sort_by: str,
        ascending: bool = False,
    ) -> list[tuple[str, float]]:
        """Generate a leaderboard from comparison results.

        Args:
            results: Results from compare()
            sort_by: Metric name to sort by
            ascending: Sort order

        Returns:
            List of (model_name, score) tuples, sorted
        """
        scores = []
        for model_name, metrics in results.items():
            if sort_by in metrics:
                scores.append((model_name, metrics[sort_by].value))

        return sorted(scores, key=lambda x: x[1], reverse=not ascending)


__all__ = [
    # Enums
    "MetricType",
    # Data classes
    "MetricResult",
    "ProfileResult",
    # Base classes
    "BaseMetric",
    "BaseLLMJudge",
    "BaseProfiler",
    "BaseBenchmark",
]
