"""
Tests for Analyzer
"""

import json
import tempfile
from pathlib import Path

import pytest

from sage.benchmark.benchmark_memory.evaluation.accuracy.f1_score import F1Score
from sage.benchmark.benchmark_memory.evaluation.core.analyzer import Analyzer
from sage.benchmark.benchmark_memory.evaluation.core.metric_interface import BaseMetric


class DummyMetric(BaseMetric):
    """Dummy metric for testing"""

    def compute_single_question(self, predicted_answer, reference_answer, metadata=None):
        return 1.0 if predicted_answer == reference_answer else 0.5


class TestAnalyzer:
    """Test cases for Analyzer"""

    def setup_method(self):
        """Setup test fixture"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        self.results_dir = self.temp_path / "results"
        self.results_dir.mkdir()

        self.output_dir = self.temp_path / "output"

    def teardown_method(self):
        """Cleanup"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_result(self, task_id: str, num_questions: int = 2) -> None:
        """Helper to create test result file"""
        result = {
            "experiment_info": {"task_id": task_id},
            "test_results": [
                {
                    "test_index": 1,
                    "questions": [
                        {
                            "predicted_answer": f"answer{i}",
                            "reference_answer": f"answer{i}",
                        }
                        for i in range(num_questions)
                    ],
                }
            ],
        }

        file_path = self.results_dir / f"{task_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result, f)

    def test_initialization(self):
        """Test analyzer initialization"""
        analyzer = Analyzer(str(self.output_dir))
        assert analyzer.output_dir == self.output_dir
        assert analyzer.output_dir.exists()
        assert analyzer.loader is None
        assert analyzer.metrics == []
        assert analyzer.results_data == []

    def test_initialization_creates_output_dir(self):
        """Test that output directory is created if it doesn't exist"""
        output_path = self.temp_path / "new_output"
        Analyzer(str(output_path))
        assert output_path.exists()

    def test_load_results(self):
        """Test loading results"""
        self._create_test_result("test-001")
        self._create_test_result("test-002")

        analyzer = Analyzer(str(self.output_dir))
        analyzer.load_results(str(self.results_dir))

        assert analyzer.loader is not None
        assert len(analyzer.results_data) == 2

    def test_register_metric(self):
        """Test registering a metric"""
        analyzer = Analyzer(str(self.output_dir))
        metric = DummyMetric(name="Dummy", description="Test")

        analyzer.register_metric(metric)
        assert len(analyzer.metrics) == 1
        assert analyzer.metrics[0].name == "Dummy"

    def test_register_multiple_metrics(self):
        """Test registering multiple metrics"""
        analyzer = Analyzer(str(self.output_dir))
        metric1 = DummyMetric(name="Metric1", description="Test1")
        metric2 = F1Score()

        analyzer.register_metric(metric1)
        analyzer.register_metric(metric2)

        assert len(analyzer.metrics) == 2

    def test_compute_metrics_independent_mode(self):
        """Test computing metrics in independent mode"""
        self._create_test_result("test-001", num_questions=2)

        analyzer = Analyzer(str(self.output_dir))
        analyzer.load_results(str(self.results_dir))
        analyzer.register_metric(DummyMetric(name="Dummy", description="Test"))

        results = analyzer.compute_metrics(mode="independent")

        assert "test-001" in results
        assert "Dummy" in results["test-001"]

    def test_compute_metrics_no_results_loaded(self):
        """Test computing metrics without loading results"""
        analyzer = Analyzer(str(self.output_dir))
        analyzer.register_metric(DummyMetric(name="Dummy", description="Test"))

        results = analyzer.compute_metrics(mode="independent")
        assert results == {}

    def test_compute_metrics_no_metrics_registered(self):
        """Test computing metrics without registering metrics"""
        self._create_test_result("test-001")

        analyzer = Analyzer(str(self.output_dir))
        analyzer.load_results(str(self.results_dir))

        results = analyzer.compute_metrics(mode="independent")
        assert "test-001" in results
        assert results["test-001"] == {}

    def test_compute_metrics_unsupported_mode(self):
        """Test computing metrics with unsupported mode"""
        analyzer = Analyzer(str(self.output_dir))

        with pytest.raises(ValueError, match="不支持的模式"):
            analyzer.compute_metrics(mode="unsupported")

    def test_compute_metrics_aggregate_mode_not_implemented(self):
        """Test that aggregate mode raises NotImplementedError"""
        analyzer = Analyzer(str(self.output_dir))

        with pytest.raises(NotImplementedError, match="aggregate 模式尚未实现"):
            analyzer.compute_metrics(mode="aggregate")

    def test_workflow_complete(self):
        """Test complete workflow: load, register, compute"""
        # Create test data
        self._create_test_result("task-001", num_questions=3)
        self._create_test_result("task-002", num_questions=2)

        # Initialize analyzer
        analyzer = Analyzer(str(self.output_dir))

        # Load results
        analyzer.load_results(str(self.results_dir))
        assert len(analyzer.results_data) == 2

        # Register metrics
        analyzer.register_metric(F1Score())
        analyzer.register_metric(DummyMetric(name="Dummy", description="Test"))
        assert len(analyzer.metrics) == 2

        # Compute metrics
        results = analyzer.compute_metrics(mode="independent")

        # Verify results
        assert "task-001" in results
        assert "task-002" in results
        assert "F1" in results["task-001"]
        assert "Dummy" in results["task-001"]

    def test_multiple_test_rounds(self):
        """Test with multiple test rounds"""
        result = {
            "experiment_info": {"task_id": "multi-round"},
            "test_results": [
                {
                    "test_index": 1,
                    "questions": [
                        {"predicted_answer": "a1", "reference_answer": "a1"},
                    ],
                },
                {
                    "test_index": 2,
                    "questions": [
                        {"predicted_answer": "a2", "reference_answer": "wrong"},
                    ],
                },
            ],
        }

        file_path = self.results_dir / "multi.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result, f)

        analyzer = Analyzer(str(self.output_dir))
        analyzer.load_results(str(self.results_dir))
        analyzer.register_metric(F1Score())

        results = analyzer.compute_metrics(mode="independent")
        assert "multi-round" in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
