"""
Core metrics for agent capability evaluation.

Implements metrics for tool selection, task planning, and timing judgment.
"""

import time
from typing import Any, Sequence

import numpy as np

from . import MetricOutput


class MetricRegistry:
    """Registry for metric implementations."""

    _metrics: dict[str, type] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a metric class."""

        def decorator(metric_class):
            cls._metrics[name] = metric_class
            return metric_class

        return decorator

    @classmethod
    def get(cls, name: str, **kwargs):
        """Get metric instance by name."""
        if name not in cls._metrics:
            raise ValueError(f"Unknown metric: {name}")
        return cls._metrics[name](**kwargs)

    @classmethod
    def list_metrics(cls) -> list[str]:
        """List all registered metric names."""
        return list(cls._metrics.keys())


@MetricRegistry.register("top_k_accuracy")
class TopKAccuracyMetric:
    """
    Top-K accuracy for tool selection.

    Measures if any predicted tool matches the ground truth within top-K.
    """

    name = "top_k_accuracy"

    def __init__(self, k: int = 5):
        """
        Initialize metric.

        Args:
            k: Number of top predictions to consider
        """
        self.k = k

    def compute(
        self, predictions: Sequence[list[str]], references: Sequence[list[str]]
    ) -> MetricOutput:
        """
        Compute top-k accuracy.

        Args:
            predictions: List of predicted tool ID lists
            references: List of reference tool ID lists

        Returns:
            MetricOutput with accuracy value
        """
        start_time = time.time()

        hits = 0
        for pred, ref in zip(predictions, references):
            pred_top_k = pred[: self.k] if isinstance(pred, list) else [pred]
            ref_set = set(ref) if isinstance(ref, list) else {ref}

            if any(p in ref_set for p in pred_top_k):
                hits += 1

        accuracy = hits / len(predictions) if len(predictions) > 0 else 0.0
        elapsed = time.time() - start_time

        return MetricOutput(
            value=accuracy,
            details={
                "k": self.k,
                "total_samples": len(predictions),
                "hits": hits,
                "compute_time_seconds": elapsed,
            },
        )


@MetricRegistry.register("recall_at_k")
class RecallAtKMetric:
    """
    Recall@K for tool selection.

    Measures what fraction of relevant tools are retrieved in top-K.
    """

    name = "recall_at_k"

    def __init__(self, k: int = 5):
        """
        Initialize metric.

        Args:
            k: Number of top predictions to consider
        """
        self.k = k

    def compute(
        self, predictions: Sequence[list[str]], references: Sequence[list[str]]
    ) -> MetricOutput:
        """
        Compute recall@k.

        Args:
            predictions: List of predicted tool ID lists
            references: List of reference tool ID lists

        Returns:
            MetricOutput with recall value
        """
        start_time = time.time()

        recalls = []
        for pred, ref in zip(predictions, references):
            pred_top_k = set(pred[: self.k]) if isinstance(pred, list) else {pred}
            ref_set = set(ref) if isinstance(ref, list) else {ref}

            if len(ref_set) == 0:
                recalls.append(0.0)
            else:
                recall = len(pred_top_k & ref_set) / len(ref_set)
                recalls.append(recall)

        avg_recall = np.mean(recalls) if len(recalls) > 0 else 0.0
        elapsed = time.time() - start_time

        return MetricOutput(
            value=float(avg_recall),
            details={
                "k": self.k,
                "total_samples": len(predictions),
                "per_sample_recalls": recalls,
                "compute_time_seconds": elapsed,
            },
        )


@MetricRegistry.register("plan_success_rate")
class PlanSuccessRateMetric:
    """
    Plan success rate for task planning.

    Measures if the predicted tool sequence exactly matches reference.
    """

    name = "plan_success_rate"

    def __init__(self, allow_partial: bool = False):
        """
        Initialize metric.

        Args:
            allow_partial: If True, count partial sequence matches
        """
        self.allow_partial = allow_partial

    def compute(
        self, predictions: Sequence[list[str]], references: Sequence[list[str]]
    ) -> MetricOutput:
        """
        Compute plan success rate.

        Args:
            predictions: List of predicted tool sequences
            references: List of reference tool sequences

        Returns:
            MetricOutput with success rate
        """
        start_time = time.time()

        successes = 0
        partial_matches = []

        for pred, ref in zip(predictions, references):
            if pred == ref:
                successes += 1
                partial_matches.append(1.0)
            elif self.allow_partial:
                # Compute longest common subsequence ratio
                min_len = min(len(pred), len(ref))
                matches = sum(1 for p, r in zip(pred[:min_len], ref[:min_len]) if p == r)
                ratio = matches / len(ref) if len(ref) > 0 else 0.0
                partial_matches.append(ratio)
            else:
                partial_matches.append(0.0)

        success_rate = successes / len(predictions) if len(predictions) > 0 else 0.0
        elapsed = time.time() - start_time

        return MetricOutput(
            value=success_rate,
            details={
                "total_samples": len(predictions),
                "exact_matches": successes,
                "allow_partial": self.allow_partial,
                "partial_match_scores": partial_matches,
                "avg_partial_score": float(np.mean(partial_matches)) if partial_matches else 0.0,
                "compute_time_seconds": elapsed,
            },
        )


@MetricRegistry.register("timing_f1")
class TimingF1Metric:
    """
    F1 score for timing judgment.

    Measures binary classification performance for tool invocation timing.
    """

    name = "timing_f1"

    def compute(self, predictions: Sequence[bool], references: Sequence[bool]) -> MetricOutput:
        """
        Compute F1 score.

        Args:
            predictions: List of predicted decisions (True = call tool)
            references: List of reference decisions

        Returns:
            MetricOutput with F1 score
        """
        start_time = time.time()

        # Convert to numpy arrays for vectorized computation
        preds = np.array(predictions, dtype=bool)
        refs = np.array(references, dtype=bool)

        # Compute confusion matrix components
        true_positives = np.sum(preds & refs)
        false_positives = np.sum(preds & ~refs)
        false_negatives = np.sum(~preds & refs)
        true_negatives = np.sum(~preds & ~refs)

        # Compute precision, recall, F1
        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        accuracy = (
            (true_positives + true_negatives) / len(predictions) if len(predictions) > 0 else 0.0
        )
        elapsed = time.time() - start_time

        return MetricOutput(
            value=float(f1),
            details={
                "precision": float(precision),
                "recall": float(recall),
                "accuracy": float(accuracy),
                "true_positives": int(true_positives),
                "false_positives": int(false_positives),
                "false_negatives": int(false_negatives),
                "true_negatives": int(true_negatives),
                "total_samples": len(predictions),
                "compute_time_seconds": elapsed,
            },
        )


@MetricRegistry.register("timing_precision")
class TimingPrecisionMetric:
    """Precision for timing judgment."""

    name = "timing_precision"

    def compute(self, predictions: Sequence[bool], references: Sequence[bool]) -> MetricOutput:
        """Compute precision."""
        preds = np.array(predictions, dtype=bool)
        refs = np.array(references, dtype=bool)

        true_positives = np.sum(preds & refs)
        false_positives = np.sum(preds & ~refs)

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )

        return MetricOutput(
            value=float(precision),
            details={
                "true_positives": int(true_positives),
                "false_positives": int(false_positives),
            },
        )


@MetricRegistry.register("timing_recall")
class TimingRecallMetric:
    """Recall for timing judgment."""

    name = "timing_recall"

    def compute(self, predictions: Sequence[bool], references: Sequence[bool]) -> MetricOutput:
        """Compute recall."""
        preds = np.array(predictions, dtype=bool)
        refs = np.array(references, dtype=bool)

        true_positives = np.sum(preds & refs)
        false_negatives = np.sum(~preds & refs)

        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )

        return MetricOutput(
            value=float(recall),
            details={
                "true_positives": int(true_positives),
                "false_negatives": int(false_negatives),
            },
        )


def load_metrics(metric_names: list[str], **kwargs) -> list[Any]:
    """
    Load metric instances from names.

    Args:
        metric_names: List of metric names to load
        **kwargs: Additional parameters for metric initialization

    Returns:
        List of instantiated metrics
    """
    metrics = []
    for name in metric_names:
        # Parse metric name with parameters (e.g., "top_k_accuracy@10")
        if "@" in name:
            metric_name, param = name.split("@")
            k = int(param)
            metric = MetricRegistry.get(metric_name, k=k, **kwargs)
        else:
            metric = MetricRegistry.get(name, **kwargs)
        metrics.append(metric)

    return metrics
