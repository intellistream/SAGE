"""
Evaluation module for Agent Capability Benchmark.

This module provides metrics, analyzers, and report builders for evaluating
agent performance across three capabilities: tool selection, task planning,
and timing judgment.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence

from pydantic import BaseModel, Field

__all__ = [
    "MetricOutput",
    "EvaluationReport",
    "Metric",
    "Analyzer",
    "ReportBuilder",
    "compute_metrics",
    "MetricRegistry",
]


class MetricOutput(BaseModel):
    """Output from a metric computation."""

    value: float
    details: dict[str, Any] = Field(default_factory=dict)


class EvaluationReport(BaseModel):
    """Complete evaluation report with metrics, breakdowns, and artifacts."""

    task: str
    experiment_id: str
    metrics: dict[str, float]
    breakdowns: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Path] = Field(default_factory=dict)
    timestamp: str

    class Config:
        arbitrary_types_allowed = True


class Metric(Protocol):
    """Protocol for metric implementations."""

    name: str

    def compute(self, predictions: Sequence[Any], references: Sequence[Any]) -> MetricOutput:
        """
        Compute metric from predictions and references.

        Args:
            predictions: Model predictions
            references: Ground truth references

        Returns:
            MetricOutput with value and optional details
        """
        ...


class Analyzer(Protocol):
    """Protocol for analyzer implementations."""

    name: str

    def analyze(
        self, predictions: Sequence[Any], references: Sequence[Any], metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze predictions and produce breakdowns.

        Args:
            predictions: Model predictions
            references: Ground truth references
            metadata: Additional context from experiment

        Returns:
            Dictionary with analysis results
        """
        ...


class ReportBuilder(Protocol):
    """Protocol for report builder implementations."""

    def build(self, report: EvaluationReport, output_path: Path) -> Path:
        """
        Build and save report to file.

        Args:
            report: EvaluationReport to format
            output_path: Path to save report

        Returns:
            Path to saved report file
        """
        ...


# Import metric registry after defining base classes
from sage.benchmark.benchmark_agent.evaluation.metrics import MetricRegistry


def compute_metrics(
    task: str,
    predictions: list[dict[str, Any]],
    references: list[dict[str, Any]],
    metrics: list[str],
    k: int = 5,
) -> dict[str, float]:
    """
    Compute evaluation metrics for experiment results.

    Args:
        task: Task type ('tool_selection', 'planning', 'timing_detection')
        predictions: List of prediction dictionaries
        references: List of reference dictionaries
        metrics: List of metric names to compute
        k: Top-k parameter for ranking metrics

    Returns:
        Dictionary mapping metric names to values
    """
    results = {}

    if task == "tool_selection":
        # Extract tool lists from predictions and references
        pred_tools = []
        ref_tools = []

        for pred, ref in zip(predictions, references):
            # Get predicted tool IDs
            if "predicted_tools" in pred:
                tools = pred["predicted_tools"]
                if tools and isinstance(tools[0], dict):
                    pred_tools.append([t["tool_id"] for t in tools])
                else:
                    pred_tools.append(tools if tools else [])
            else:
                pred_tools.append([])

            # Get reference tool IDs
            if "ground_truth_tools" in ref:
                ref_tools.append(ref["ground_truth_tools"])
            elif "top_k" in ref:
                ref_tools.append(ref["top_k"])
            else:
                ref_tools.append([])

        # Compute each metric
        for metric_name in metrics:
            try:
                if metric_name in ("top_k_accuracy", "recall_at_k", "precision_at_k"):
                    metric = MetricRegistry.get(metric_name, k=k)
                elif metric_name == "mrr":
                    metric = MetricRegistry.get("mrr")
                else:
                    continue

                output = metric.compute(pred_tools, ref_tools)
                results[metric_name] = output.value
            except Exception as e:
                results[metric_name] = 0.0
                results[f"{metric_name}_error"] = str(e)

    elif task == "timing_detection":
        # Extract boolean decisions
        pred_decisions = []
        ref_decisions = []

        for pred, ref in zip(predictions, references):
            pred_decisions.append(pred.get("should_call_tool", False))
            ref_decisions.append(ref.get("should_call_tool", False))

        for metric_name in metrics:
            try:
                metric = MetricRegistry.get(metric_name)
                output = metric.compute(pred_decisions, ref_decisions)
                results[metric_name] = output.value
            except Exception:
                results[metric_name] = 0.0

    elif task == "planning":
        # Extract tool sequences
        pred_sequences = []
        ref_sequences = []

        for pred, ref in zip(predictions, references):
            pred_sequences.append(pred.get("tool_sequence", []))
            ref_sequences.append(ref.get("tool_sequence", []))

        for metric_name in metrics:
            try:
                metric = MetricRegistry.get(metric_name)
                output = metric.compute(pred_sequences, ref_sequences)
                results[metric_name] = output.value
            except Exception:
                results[metric_name] = 0.0

    return results
