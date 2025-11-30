"""
Evaluation pipeline orchestrator.

Coordinates metrics computation, analysis, and report generation.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ..experiments.base_experiment import ExperimentConfig, ExperimentResult
from . import EvaluationReport
from .analyzers import PlanningAnalyzer, TimingAnalyzer, ToolSelectionAnalyzer
from .metrics import load_metrics
from .report_builder import create_report_builders

logger = logging.getLogger(__name__)


class EvaluationPipeline:
    """
    Pipeline for evaluating experiment results.

    Orchestrates:
    1. Metric computation
    2. Detailed analysis
    3. Report generation
    """

    def __init__(self, metrics: list[Any], analyzers: list[Any], report_builders: dict[str, Any]):
        """
        Initialize pipeline.

        Args:
            metrics: List of metric instances
            analyzers: List of analyzer instances
            report_builders: Dict mapping format to builder instance
        """
        self.metrics = metrics
        self.analyzers = analyzers
        self.report_builders = report_builders

    @classmethod
    def from_config(
        cls, config: ExperimentConfig, metrics_registry: Any = None
    ) -> "EvaluationPipeline":
        """
        Create pipeline from experiment config.

        Args:
            config: Experiment configuration
            metrics_registry: Optional custom metrics registry

        Returns:
            Initialized EvaluationPipeline
        """
        # Load metrics
        metric_names = config.metrics if config.metrics else []
        metrics = load_metrics(metric_names)

        # Create task-specific analyzer
        task = config.experiment
        analyzers = []

        if task == "tool_selection":
            analyzers.append(ToolSelectionAnalyzer())
        elif task == "planning":
            analyzers.append(PlanningAnalyzer())
        elif task == "timing_detection":
            analyzers.append(TimingAnalyzer())

        # Create report builders
        report_formats = (
            config.report.format if hasattr(config.report, "format") else ["json", "markdown"]
        )
        builders = create_report_builders(report_formats)

        return cls(metrics=metrics, analyzers=analyzers, report_builders=builders)

    def evaluate(self, result: ExperimentResult, config: ExperimentConfig) -> EvaluationReport:
        """
        Evaluate experiment result.

        Args:
            result: Experiment result to evaluate
            config: Experiment configuration

        Returns:
            EvaluationReport with metrics and analysis
        """
        logger.info(f"Evaluating experiment: {result.experiment_id}")

        # Extract predictions and references based on task type
        predictions, references = self._extract_pred_ref(result)

        # Compute metrics
        logger.info(f"Computing {len(self.metrics)} metrics...")
        metric_results = {}
        metric_details = {}

        for metric in self.metrics:
            try:
                logger.debug(f"Computing metric: {metric.name}")
                output = metric.compute(predictions, references)
                metric_results[metric.name] = output.value
                metric_details[metric.name] = output.details
            except Exception as e:
                logger.error(f"Error computing metric {metric.name}: {e}")
                metric_results[metric.name] = 0.0
                metric_details[metric.name] = {"error": str(e)}

        # Run analyzers
        logger.info(f"Running {len(self.analyzers)} analyzers...")
        breakdowns = {}

        for analyzer in self.analyzers:
            try:
                logger.debug(f"Running analyzer: {analyzer.name}")
                analysis = analyzer.analyze(predictions, references, result.metadata)
                breakdowns[analyzer.name] = analysis
            except Exception as e:
                logger.error(f"Error in analyzer {analyzer.name}: {e}")
                breakdowns[analyzer.name] = {"error": str(e)}

        # Add metric details to breakdowns
        if metric_details:
            breakdowns["metric_details"] = metric_details

        # Create evaluation report
        report = EvaluationReport(
            task=result.task,
            experiment_id=result.experiment_id,
            metrics=metric_results,
            breakdowns=breakdowns,
            artifacts={},
            timestamp=datetime.utcnow().isoformat(),
        )

        # Generate and save reports
        output_dir = Path(config.report.path) / result.experiment_id
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating reports in {output_dir}")
        for format_name, builder in self.report_builders.items():
            try:
                output_file = output_dir / f"evaluation_report.{format_name}"
                saved_path = builder.build(report, output_file)
                report.artifacts[f"report_{format_name}"] = saved_path
                logger.info(f"Saved {format_name} report to: {saved_path}")
            except Exception as e:
                logger.error(f"Error building {format_name} report: {e}")

        logger.info(f"Evaluation complete. Overall metrics: {metric_results}")

        return report

    def _extract_pred_ref(self, result: ExperimentResult):
        """
        Extract predictions and references from result.

        Args:
            result: ExperimentResult

        Returns:
            Tuple of (predictions, references)
        """
        task = result.task

        if task == "tool_selection":
            # Extract tool ID lists
            predictions = []
            for pred in result.predictions:
                pred_tools = pred.get("predicted_tools", pred.get("tools", []))
                # Handle both list of dicts and list of strings
                if pred_tools and isinstance(pred_tools[0], dict):
                    pred_tools = [t.get("tool_id", t.get("id")) for t in pred_tools]
                predictions.append(pred_tools)

            references = []
            for ref in result.references:
                ref_tools = ref.get("ground_truth_tools", ref.get("tools", ref.get("top_k", [])))
                references.append(ref_tools)

        elif task == "planning":
            # Extract tool sequences
            predictions = [
                pred.get("tool_sequence", pred.get("steps", [])) for pred in result.predictions
            ]
            references = [
                ref.get("tool_sequence", ref.get("steps", [])) for ref in result.references
            ]

        elif task == "timing_detection":
            # Extract boolean decisions
            predictions = [
                pred.get("should_call_tool", pred.get("decision", False))
                for pred in result.predictions
            ]
            references = [
                ref.get("should_call_tool", ref.get("decision", False)) for ref in result.references
            ]

        else:
            raise ValueError(f"Unknown task type: {task}")

        return predictions, references


def save_report(report: EvaluationReport, output_dir: Path, formats: list[str] = None):
    """
    Save evaluation report to files.

    Args:
        report: EvaluationReport to save
        output_dir: Directory to save reports
        formats: List of formats to save (default: ["json", "markdown"])
    """
    formats = formats or ["json", "markdown"]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    builders = create_report_builders(formats)

    for format_name, builder in builders.items():
        output_file = output_dir / f"evaluation_report.{format_name}"
        builder.build(report, output_file)
        logger.info(f"Saved {format_name} report to: {output_file}")
