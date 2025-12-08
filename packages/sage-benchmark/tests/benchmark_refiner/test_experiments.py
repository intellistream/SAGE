# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Unit tests for benchmark_refiner experiments module.

Tests cover:
- RefinerExperimentConfig
- ExperimentResult
- AlgorithmMetrics
- BaseRefinerExperiment
- ComparisonExperiment variants
- RefinerExperimentRunner
"""

from __future__ import annotations

import tempfile

from sage.benchmark.benchmark_refiner.experiments import (
    AlgorithmMetrics,
    ComparisonExperiment,
    CompressionExperiment,
    DatasetType,
    ExperimentResult,
    LatencyExperiment,
    QualityExperiment,
    RefinerAlgorithm,
    RefinerExperimentConfig,
    RefinerExperimentRunner,
)


# =============================================================================
# Tests for RefinerAlgorithm Enum
# =============================================================================
class TestRefinerAlgorithm:
    """Tests for RefinerAlgorithm enum."""

    def test_algorithm_values(self) -> None:
        """Test algorithm enum values."""
        assert RefinerAlgorithm.BASELINE.value == "baseline"
        assert RefinerAlgorithm.LONGREFINER.value == "longrefiner"
        assert RefinerAlgorithm.REFORM.value == "reform"
        assert RefinerAlgorithm.PROVENCE.value == "provence"

    def test_algorithm_from_string(self) -> None:
        """Test creating algorithm from string."""
        algo = RefinerAlgorithm("baseline")
        assert algo == RefinerAlgorithm.BASELINE

    def test_available_algorithms(self) -> None:
        """Test available algorithms list."""
        available = RefinerAlgorithm.available()
        assert "baseline" in available
        assert "longrefiner" in available


# =============================================================================
# Tests for DatasetType Enum
# =============================================================================
class TestDatasetType:
    """Tests for DatasetType enum."""

    def test_dataset_values(self) -> None:
        """Test dataset enum values."""
        assert DatasetType.NQ.value == "nq"
        assert DatasetType.HOTPOTQA.value == "hotpotqa"
        assert DatasetType.TRIVIAQA.value == "triviaqa"


# =============================================================================
# Tests for RefinerExperimentConfig
# =============================================================================
class TestRefinerExperimentConfig:
    """Tests for RefinerExperimentConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default config creation."""
        config = RefinerExperimentConfig(name="test")
        assert config.name == "test"
        # Default algorithms is ["baseline", "longrefiner"]
        assert config.algorithms == ["baseline", "longrefiner"]
        assert config.max_samples == 100
        assert config.budget == 2048
        assert config.top_k == 100
        assert config.verbose is True

    def test_custom_config(self) -> None:
        """Test custom config creation."""
        config = RefinerExperimentConfig(
            name="custom_test",
            algorithms=["baseline", "longrefiner"],
            max_samples=50,
            budget=1024,
            dataset=DatasetType.HOTPOTQA,
        )
        assert config.name == "custom_test"
        assert config.algorithms == ["baseline", "longrefiner"]
        assert config.max_samples == 50
        assert config.budget == 1024

    def test_config_to_dict(self) -> None:
        """Test config serialization to dict."""
        config = RefinerExperimentConfig(
            name="test",
            algorithms=["baseline"],
            max_samples=10,
        )
        d = config.to_dict()

        assert d["name"] == "test"
        assert d["algorithms"] == ["baseline"]
        assert d["max_samples"] == 10
        assert "budget" in d

    def test_config_from_dict(self) -> None:
        """Test config creation from dict."""
        d = {
            "name": "from_dict_test",
            "algorithms": ["reform", "provence"],
            "max_samples": 25,
            "budget": 512,
        }
        config = RefinerExperimentConfig.from_dict(d)

        assert config.name == "from_dict_test"
        assert config.algorithms == ["reform", "provence"]
        assert config.max_samples == 25
        assert config.budget == 512

    def test_config_yaml_roundtrip(self) -> None:
        """Test config save/load YAML roundtrip."""
        original = RefinerExperimentConfig(
            name="yaml_test",
            description="Test YAML serialization",
            algorithms=["baseline", "longrefiner"],
            max_samples=50,
            budget=1024,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            original.save_yaml(f.name)
            loaded = RefinerExperimentConfig.from_yaml(f.name)

        assert loaded.name == original.name
        assert loaded.description == original.description
        assert loaded.algorithms == original.algorithms
        assert loaded.max_samples == original.max_samples
        assert loaded.budget == original.budget

    def test_config_validate(self) -> None:
        """Test config validation."""
        config = RefinerExperimentConfig(
            name="valid_test",
            algorithms=["baseline"],
            max_samples=10,
        )
        errors = config.validate()
        assert len(errors) == 0

    def test_config_validate_invalid(self) -> None:
        """Test config validation with invalid values."""
        config = RefinerExperimentConfig(
            name="invalid_test",
            algorithms=["unknown_algo"],
            max_samples=-1,
        )
        errors = config.validate()
        assert len(errors) > 0


# =============================================================================
# Tests for AlgorithmMetrics
# =============================================================================
class TestAlgorithmMetrics:
    """Tests for AlgorithmMetrics dataclass."""

    def test_default_metrics(self) -> None:
        """Test default metrics creation."""
        metrics = AlgorithmMetrics(algorithm="baseline")
        assert metrics.algorithm == "baseline"
        assert metrics.num_samples == 0
        assert metrics.avg_f1 == 0.0
        assert metrics.avg_total_time == 0.0
        assert metrics.avg_compression_rate == 0.0

    def test_metrics_with_values(self) -> None:
        """Test metrics with values."""
        metrics = AlgorithmMetrics(
            algorithm="longrefiner",
            num_samples=100,
            avg_f1=0.75,
            avg_total_time=0.150,
            avg_compression_rate=3.5,
            std_f1=0.05,
        )
        assert metrics.algorithm == "longrefiner"
        assert metrics.num_samples == 100
        assert metrics.avg_f1 == 0.75
        assert metrics.avg_total_time == 0.150
        assert metrics.avg_compression_rate == 3.5
        assert metrics.std_f1 == 0.05

    def test_metrics_to_dict(self) -> None:
        """Test metrics serialization."""
        metrics = AlgorithmMetrics(
            algorithm="reform",
            num_samples=50,
            avg_f1=0.80,
        )
        d = metrics.to_dict()

        assert d["algorithm"] == "reform"
        assert d["num_samples"] == 50
        assert d["quality"]["avg_f1"] == 0.80


# =============================================================================
# Tests for ExperimentResult
# =============================================================================
class TestExperimentResult:
    """Tests for ExperimentResult dataclass."""

    def test_default_result(self) -> None:
        """Test default result creation."""
        result = ExperimentResult(
            experiment_id="test-001",
            config={"name": "test"},
        )
        assert result.experiment_id == "test-001"
        assert result.success is True
        assert result.algorithm_metrics == {}
        assert result.raw_results == []

    def test_result_with_metrics(self) -> None:
        """Test result with algorithm metrics."""
        metrics = AlgorithmMetrics(algorithm="baseline", avg_f1=0.70)
        result = ExperimentResult(
            experiment_id="test-002",
            config={"name": "test"},
            algorithm_metrics={"baseline": metrics},
        )
        assert "baseline" in result.algorithm_metrics
        assert result.algorithm_metrics["baseline"].avg_f1 == 0.70

    def test_failed_result(self) -> None:
        """Test failed result."""
        result = ExperimentResult(
            experiment_id="test-003",
            config={"name": "failed_test"},
            success=False,
            error="Test error message",
        )
        assert result.success is False
        assert result.error == "Test error message"

    def test_result_to_dict(self) -> None:
        """Test result serialization."""
        result = ExperimentResult(
            experiment_id="test-004",
            config={"name": "test"},
            best_f1_algorithm="longrefiner",
        )
        d = result.to_dict()

        assert d["experiment_id"] == "test-004"
        assert d["summary"]["best_f1_algorithm"] == "longrefiner"


# =============================================================================
# Tests for RefinerExperimentRunner
# =============================================================================
class TestRefinerExperimentRunner:
    """Tests for RefinerExperimentRunner."""

    def test_runner_creation(self) -> None:
        """Test runner creation."""
        runner = RefinerExperimentRunner(verbose=False)
        assert runner.verbose is False

    def test_runner_verbose(self) -> None:
        """Test runner with verbose mode."""
        runner = RefinerExperimentRunner(verbose=True)
        assert runner.verbose is True

    def test_generate_latex_table_empty(self) -> None:
        """Test LaTeX table generation with empty results."""
        runner = RefinerExperimentRunner(verbose=False)
        result = ExperimentResult(
            experiment_id="empty-001",
            config={"name": "empty_test"},
        )
        latex = runner.generate_latex_table(result)
        assert "\\begin{tabular}" in latex
        assert "\\end{tabular}" in latex


# =============================================================================
# Tests for Experiment Classes
# =============================================================================
class TestComparisonExperiment:
    """Tests for ComparisonExperiment."""

    def test_experiment_creation(self) -> None:
        """Test experiment creation."""
        config = RefinerExperimentConfig(
            name="comparison_test",
            algorithms=["baseline", "longrefiner"],
        )
        exp = ComparisonExperiment(config)
        assert exp.config == config
        assert exp.config.name == "comparison_test"


class TestQualityExperiment:
    """Tests for QualityExperiment."""

    def test_experiment_creation(self) -> None:
        """Test quality experiment creation."""
        config = RefinerExperimentConfig(name="quality_test")
        exp = QualityExperiment(config)
        assert exp.config == config
        assert exp.config.name == "quality_test"


class TestLatencyExperiment:
    """Tests for LatencyExperiment."""

    def test_experiment_creation(self) -> None:
        """Test latency experiment creation."""
        config = RefinerExperimentConfig(name="latency_test")
        exp = LatencyExperiment(config)
        assert exp.config == config


class TestCompressionExperiment:
    """Tests for CompressionExperiment."""

    def test_experiment_creation(self) -> None:
        """Test compression experiment creation."""
        config = RefinerExperimentConfig(name="compression_test")
        exp = CompressionExperiment(config)
        assert exp.config == config
