"""
Unit tests for agent benchmark evaluation module.

Tests metrics computation, analyzers, report building, and pipeline orchestration.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from sage.benchmark.benchmark_agent.evaluation import (
    EvaluationReport,
)
from sage.benchmark.benchmark_agent.evaluation.analyzers import (
    PlanningAnalyzer,
    TimingAnalyzer,
    ToolSelectionAnalyzer,
)
from sage.benchmark.benchmark_agent.evaluation.evaluator import (
    EvaluationPipeline,
    save_report,
)
from sage.benchmark.benchmark_agent.evaluation.metrics import (
    MetricRegistry,
    PlanSuccessRateMetric,
    RecallAtKMetric,
    TimingF1Metric,
    TopKAccuracyMetric,
    load_metrics,
)
from sage.benchmark.benchmark_agent.evaluation.report_builder import (
    JsonReportBuilder,
    MarkdownReportBuilder,
    create_report_builders,
)
from sage.benchmark.benchmark_agent.experiments.base_experiment import (
    ExperimentResult,
    ReportConfig,
    ToolSelectionConfig,
)


class TestMetrics:
    """Test metric implementations."""

    def test_top_k_accuracy_perfect(self):
        """Test top-k accuracy with perfect predictions."""
        metric = TopKAccuracyMetric(k=3)

        predictions = [
            ["tool1", "tool2", "tool3"],
            ["toolA", "toolB", "toolC"],
        ]
        references = [
            ["tool1"],
            ["toolB"],
        ]

        result = metric.compute(predictions, references)

        assert result.value == 1.0
        assert result.details["k"] == 3
        assert result.details["hits"] == 2
        assert result.details["total_samples"] == 2

    def test_top_k_accuracy_partial(self):
        """Test top-k accuracy with partial matches."""
        metric = TopKAccuracyMetric(k=2)

        predictions = [
            ["tool1", "tool2"],
            ["toolX", "toolY"],
            ["toolA", "toolB"],
        ]
        references = [
            ["tool1"],
            ["toolZ"],
            ["toolB"],
        ]

        result = metric.compute(predictions, references)

        assert result.value == pytest.approx(2 / 3)
        assert result.details["hits"] == 2

    def test_recall_at_k(self):
        """Test recall@k metric."""
        metric = RecallAtKMetric(k=3)

        predictions = [
            ["tool1", "tool2", "tool3"],
            ["toolA", "toolB", "toolC"],
        ]
        references = [
            ["tool1", "tool2", "tool4"],
            ["toolA"],
        ]

        result = metric.compute(predictions, references)

        # First: 2/3, Second: 1/1 -> avg = 5/6
        expected_recall = (2 / 3 + 1.0) / 2
        assert result.value == pytest.approx(expected_recall)

    def test_plan_success_rate_exact(self):
        """Test plan success rate with exact matches."""
        metric = PlanSuccessRateMetric(allow_partial=False)

        predictions = [
            ["tool1", "tool2", "tool3"],
            ["toolA", "toolB"],
            ["toolX", "toolY"],
        ]
        references = [
            ["tool1", "tool2", "tool3"],
            ["toolA", "toolB"],
            ["toolX", "toolZ"],
        ]

        result = metric.compute(predictions, references)

        assert result.value == pytest.approx(2 / 3)
        assert result.details["exact_matches"] == 2

    def test_plan_success_rate_partial(self):
        """Test plan success rate with partial matching."""
        metric = PlanSuccessRateMetric(allow_partial=True)

        predictions = [
            ["tool1", "tool2", "tool3"],
            ["toolA", "toolX"],
        ]
        references = [
            ["tool1", "tool2", "tool4"],
            ["toolA", "toolB"],
        ]

        result = metric.compute(predictions, references)

        # No exact matches, but partial scores
        assert result.details["exact_matches"] == 0
        assert result.details["avg_partial_score"] > 0

    def test_timing_f1(self):
        """Test timing F1 metric."""
        metric = TimingF1Metric()

        predictions = [True, True, False, False, True]
        references = [True, False, False, True, True]

        result = metric.compute(predictions, references)

        # TP=2, FP=1, FN=1, TN=1
        # Precision=2/3, Recall=2/3, F1=2/3
        assert result.details["true_positives"] == 2
        assert result.details["false_positives"] == 1
        assert result.details["false_negatives"] == 1
        assert result.details["true_negatives"] == 1
        assert result.value == pytest.approx(2 / 3)

    def test_metric_registry(self):
        """Test metric registry."""
        metric_names = MetricRegistry.list_metrics()

        assert "top_k_accuracy" in metric_names
        assert "recall_at_k" in metric_names
        assert "plan_success_rate" in metric_names
        assert "timing_f1" in metric_names

        # Test getting metric
        metric = MetricRegistry.get("top_k_accuracy", k=10)
        assert metric.k == 10

    def test_load_metrics(self):
        """Test loading metrics from names."""
        metric_names = ["top_k_accuracy", "recall_at_k@10"]
        metrics = load_metrics(metric_names)

        assert len(metrics) == 2
        assert metrics[0].name == "top_k_accuracy"
        assert metrics[1].k == 10


class TestAnalyzers:
    """Test analyzer implementations."""

    def test_tool_selection_analyzer(self):
        """Test tool selection analyzer."""
        analyzer = ToolSelectionAnalyzer()

        predictions = [
            ["finance_banking_001", "finance_banking_002"],
            ["travel_booking_001"],
        ]
        references = [
            ["finance_banking_001", "finance_payment_001"],
            ["travel_booking_001"],
        ]

        result = analyzer.analyze(predictions, references, {})

        assert "error_patterns" in result
        assert "tool_coverage" in result
        assert "selection_accuracy" in result
        assert result["error_patterns"]["all_correct"] == 1

    def test_planning_analyzer(self):
        """Test planning analyzer."""
        analyzer = PlanningAnalyzer()

        predictions = [
            ["tool1", "tool2", "tool3"],
            ["toolA", "toolB"],
        ]
        references = [
            ["tool1", "tool2", "tool3"],
            ["toolA", "toolX", "toolY"],
        ]

        result = analyzer.analyze(predictions, references, {})

        assert "exact_match_rate" in result
        assert "step_correctness" in result
        assert "failure_modes" in result
        assert result["exact_match_rate"] == 0.5
        assert result["failure_modes"]["perfect"] == 1
        assert result["failure_modes"]["too_short"] == 1

    def test_timing_analyzer(self):
        """Test timing analyzer."""
        analyzer = TimingAnalyzer()

        predictions = [True, True, False, False]
        references = [True, False, False, True]

        result = analyzer.analyze(predictions, references, {})

        assert "confusion_matrix" in result
        assert "rates" in result
        assert "class_distribution" in result
        assert result["confusion_matrix"]["true_positives"] == 1
        assert result["confusion_matrix"]["false_positives"] == 1

    def test_timing_analyzer_with_confidence(self):
        """Test timing analyzer with confidence scores."""
        analyzer = TimingAnalyzer()

        predictions = [True, True, False, False]
        references = [True, False, False, True]
        metadata = {"confidences": [0.9, 0.6, 0.3, 0.4]}

        result = analyzer.analyze(predictions, references, metadata)

        assert "confidence_analysis" in result
        assert "mean_confidence_overall" in result["confidence_analysis"]
        assert "threshold_sensitivity" in result["confidence_analysis"]


class TestReportBuilders:
    """Test report builder implementations."""

    def test_json_report_builder(self):
        """Test JSON report building."""
        builder = JsonReportBuilder()

        report = EvaluationReport(
            task="tool_selection",
            experiment_id="test_exp_001",
            metrics={"top_k_accuracy": 0.85, "recall@5": 0.75},
            breakdowns={"test": {"value": 123}},
            artifacts={},
            timestamp=datetime.utcnow().isoformat(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.json"
            saved_path = builder.build(report, output_path)

            assert saved_path.exists()

            # Verify content
            with open(saved_path) as f:
                data = json.load(f)

            assert data["task"] == "tool_selection"
            assert data["metrics"]["top_k_accuracy"] == 0.85

    def test_markdown_report_builder(self):
        """Test Markdown report building."""
        builder = MarkdownReportBuilder()

        report = EvaluationReport(
            task="planning",
            experiment_id="test_exp_002",
            metrics={"plan_success": 0.90},
            breakdowns={"analysis": {"exact_matches": 45, "partial_matches": 5}},
            artifacts={},
            timestamp=datetime.utcnow().isoformat(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.md"
            saved_path = builder.build(report, output_path)

            assert saved_path.exists()

            # Verify content
            content = saved_path.read_text()
            assert "# Evaluation Report: Planning" in content
            assert "test_exp_002" in content
            assert "0.9000" in content

    def test_create_report_builders(self):
        """Test report builder factory."""
        builders = create_report_builders(["json", "markdown"])

        assert "json" in builders
        assert "markdown" in builders
        assert isinstance(builders["json"], JsonReportBuilder)
        assert isinstance(builders["markdown"], MarkdownReportBuilder)


class TestEvaluationPipeline:
    """Test evaluation pipeline orchestration."""

    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        metrics = [TopKAccuracyMetric(k=5)]
        analyzers = [ToolSelectionAnalyzer()]
        builders = create_report_builders(["json"])

        pipeline = EvaluationPipeline(metrics, analyzers, builders)

        assert len(pipeline.metrics) == 1
        assert len(pipeline.analyzers) == 1
        assert "json" in pipeline.report_builders

    def test_pipeline_from_config(self):
        """Test creating pipeline from config."""
        config = ToolSelectionConfig(
            metrics=["top_k_accuracy", "recall_at_k"],
            report=ReportConfig(format=["json", "markdown"]),
        )

        pipeline = EvaluationPipeline.from_config(config)

        assert len(pipeline.metrics) == 2
        assert len(pipeline.analyzers) == 1
        assert "json" in pipeline.report_builders
        assert "markdown" in pipeline.report_builders

    def test_pipeline_evaluate(self):
        """Test full pipeline evaluation."""
        # Create experiment result
        result = ExperimentResult(
            task="tool_selection",
            experiment_id="test_001",
            config={},
            predictions=[
                {"predicted_tools": ["tool1", "tool2", "tool3"]},
                {"predicted_tools": ["toolA", "toolB"]},
            ],
            references=[
                {"tools": ["tool1", "tool4"]},
                {"tools": ["toolA"]},
            ],
            metadata={},
        )

        # Create config
        config = ToolSelectionConfig(
            metrics=["top_k_accuracy"], report=ReportConfig(format=["json"])
        )

        # Create and run pipeline
        with tempfile.TemporaryDirectory() as tmpdir:
            config.report.path = tmpdir
            pipeline = EvaluationPipeline.from_config(config)
            report = pipeline.evaluate(result, config)

            assert report.task == "tool_selection"
            assert "top_k_accuracy" in report.metrics
            assert len(report.artifacts) > 0


class TestIntegration:
    """Integration tests."""

    def test_end_to_end_tool_selection(self):
        """Test end-to-end tool selection evaluation."""
        # Mock experiment result
        result = ExperimentResult(
            task="tool_selection",
            experiment_id="integration_test_001",
            config={},
            predictions=[
                {"predicted_tools": ["finance_banking_001", "finance_payment_001"]},
                {"predicted_tools": ["travel_booking_001"]},
            ],
            references=[
                {"tools": ["finance_banking_001"]},
                {"tools": ["travel_booking_001"]},
            ],
            metadata={},
        )

        config = ToolSelectionConfig(
            metrics=["top_k_accuracy", "recall_at_k"],
            report=ReportConfig(format=["json", "markdown"]),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config.report.path = tmpdir
            pipeline = EvaluationPipeline.from_config(config)
            report = pipeline.evaluate(result, config)

            # Verify metrics
            assert report.metrics["top_k_accuracy"] == 1.0

            # Verify artifacts created
            assert len(report.artifacts) == 2

            # Verify files exist
            for artifact_path in report.artifacts.values():
                assert Path(artifact_path).exists()

    def test_save_report_function(self):
        """Test save_report utility function."""
        report = EvaluationReport(
            task="timing_detection",
            experiment_id="save_test",
            metrics={"f1": 0.88},
            breakdowns={},
            artifacts={},
            timestamp=datetime.utcnow().isoformat(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            save_report(report, Path(tmpdir), formats=["json", "markdown"])

            assert (Path(tmpdir) / "evaluation_report.json").exists()
            assert (Path(tmpdir) / "evaluation_report.markdown").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
