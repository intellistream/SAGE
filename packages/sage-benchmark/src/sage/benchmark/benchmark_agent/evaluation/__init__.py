"""
Evaluation module for Agent Capability Benchmark.

This module provides metrics, analyzers, and report builders for evaluating
agent performance across three capabilities: tool selection, task planning,
and timing judgment.
"""

from pathlib import Path
from typing import Any, Dict, List, Protocol, Sequence

from pydantic import BaseModel, Field

__all__ = [
    "MetricOutput",
    "EvaluationReport",
    "Metric",
    "Analyzer",
    "ReportBuilder",
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
