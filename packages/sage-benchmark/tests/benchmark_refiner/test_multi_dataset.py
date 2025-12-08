# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Unit tests for multi-dataset support in benchmark_refiner.

Tests cover:
- RefinerExperimentConfig with datasets field
- ComparisonExperiment with multiple datasets
- DatasetResult and MultiDatasetExperimentResult
- CLI --datasets argument parsing

Note: These tests use mocks to avoid calling real Pipelines which would
involve time.sleep() and actual model loading.
"""

from __future__ import annotations

import tempfile
from typing import Any
from unittest.mock import patch

from sage.benchmark.benchmark_refiner.experiments import (
    AVAILABLE_DATASETS,
    AlgorithmMetrics,
    ComparisonExperiment,
    DatasetResult,
    ExperimentResult,
    MultiDatasetExperimentResult,
    RefinerExperimentConfig,
    RefinerExperimentRunner,
)


# =============================================================================
# Tests for AVAILABLE_DATASETS constant
# =============================================================================
class TestAvailableDatasets:
    """Tests for AVAILABLE_DATASETS constant."""

    def test_contains_expected_datasets(self) -> None:
        """Test that AVAILABLE_DATASETS contains expected datasets."""
        expected = ["nq", "hotpotqa", "triviaqa", "2wikimultihopqa", "asqa"]
        for ds in expected:
            assert ds in AVAILABLE_DATASETS, f"Expected {ds} in AVAILABLE_DATASETS"

    def test_is_list(self) -> None:
        """Test that AVAILABLE_DATASETS is a list."""
        assert isinstance(AVAILABLE_DATASETS, list)

    def test_not_empty(self) -> None:
        """Test that AVAILABLE_DATASETS is not empty."""
        assert len(AVAILABLE_DATASETS) > 0


# =============================================================================
# Tests for RefinerExperimentConfig with datasets field
# =============================================================================
class TestRefinerExperimentConfigDatasets:
    """Tests for RefinerExperimentConfig datasets field."""

    def test_default_datasets(self) -> None:
        """Test that default datasets is ['nq']."""
        config = RefinerExperimentConfig(name="test")
        assert config.datasets == ["nq"]

    def test_single_dataset(self) -> None:
        """Test config with a single dataset."""
        config = RefinerExperimentConfig(
            name="single_ds_test",
            datasets=["hotpotqa"],
        )
        assert config.datasets == ["hotpotqa"]

    def test_multiple_datasets(self) -> None:
        """Test config with multiple datasets."""
        config = RefinerExperimentConfig(
            name="multi_ds_test",
            datasets=["nq", "hotpotqa", "2wikimultihopqa"],
        )
        assert len(config.datasets) == 3
        assert "nq" in config.datasets
        assert "hotpotqa" in config.datasets
        assert "2wikimultihopqa" in config.datasets

    def test_get_datasets(self) -> None:
        """Test get_datasets method."""
        config = RefinerExperimentConfig(
            name="test",
            datasets=["nq", "triviaqa"],
        )
        datasets = config.get_datasets()
        assert datasets == ["nq", "triviaqa"]

    def test_datasets_in_to_dict(self) -> None:
        """Test that datasets is included in to_dict output."""
        config = RefinerExperimentConfig(
            name="test",
            datasets=["nq", "hotpotqa"],
        )
        d = config.to_dict()
        assert "datasets" in d
        assert d["datasets"] == ["nq", "hotpotqa"]

    def test_datasets_from_dict(self) -> None:
        """Test creating config from dict with datasets."""
        d = {
            "name": "from_dict_test",
            "datasets": ["triviaqa", "asqa"],
            "algorithms": ["baseline"],
        }
        config = RefinerExperimentConfig.from_dict(d)
        assert config.datasets == ["triviaqa", "asqa"]

    def test_backwards_compatible_from_dict(self) -> None:
        """Test that old config format (without datasets) still works."""
        d = {
            "name": "old_format_test",
            "dataset": "nq",
            "algorithms": ["baseline"],
        }
        config = RefinerExperimentConfig.from_dict(d)
        # Should create datasets from dataset
        assert config.datasets == ["nq"]

    def test_validate_valid_datasets(self) -> None:
        """Test validation with valid datasets."""
        config = RefinerExperimentConfig(
            name="valid_test",
            datasets=["nq", "hotpotqa"],
            algorithms=["baseline"],
        )
        errors = config.validate()
        # Should have no dataset-related errors
        dataset_errors = [e for e in errors if "dataset" in e.lower()]
        assert len(dataset_errors) == 0

    def test_validate_invalid_datasets(self) -> None:
        """Test validation with invalid datasets."""
        config = RefinerExperimentConfig(
            name="invalid_test",
            datasets=["nq", "unknown_dataset", "another_unknown"],
            algorithms=["baseline"],
        )
        errors = config.validate()
        # Should have errors for unknown datasets
        assert any("unknown_dataset" in e for e in errors)
        assert any("another_unknown" in e for e in errors)

    def test_validate_empty_datasets(self) -> None:
        """Test validation with empty datasets list."""
        config = RefinerExperimentConfig(
            name="empty_ds_test",
            datasets=[],
            algorithms=["baseline"],
        )
        errors = config.validate()
        assert any("empty" in e.lower() for e in errors)

    def test_yaml_roundtrip_with_datasets(self) -> None:
        """Test YAML save/load preserves datasets."""
        original = RefinerExperimentConfig(
            name="yaml_test",
            datasets=["nq", "hotpotqa", "2wikimultihopqa"],
            algorithms=["baseline", "longrefiner"],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            original.save_yaml(f.name)
            loaded = RefinerExperimentConfig.from_yaml(f.name)

        assert loaded.datasets == original.datasets


# =============================================================================
# Tests for DatasetResult
# =============================================================================
class TestDatasetResult:
    """Tests for DatasetResult dataclass."""

    def test_default_creation(self) -> None:
        """Test default DatasetResult creation."""
        result = DatasetResult(dataset="nq")
        assert result.dataset == "nq"
        assert result.algorithm_metrics == {}
        assert result.raw_results == []
        assert result.success is True

    def test_with_metrics(self) -> None:
        """Test DatasetResult with algorithm metrics."""
        metrics = AlgorithmMetrics(algorithm="baseline", avg_f1=0.70)
        result = DatasetResult(
            dataset="hotpotqa",
            algorithm_metrics={"baseline": metrics},
        )
        assert result.dataset == "hotpotqa"
        assert "baseline" in result.algorithm_metrics
        assert result.algorithm_metrics["baseline"].avg_f1 == 0.70

    def test_to_dict(self) -> None:
        """Test DatasetResult serialization."""
        result = DatasetResult(
            dataset="nq",
            success=True,
        )
        d = result.to_dict()
        assert d["dataset"] == "nq"
        assert d["success"] is True
        assert "algorithm_metrics" in d


# =============================================================================
# Tests for MultiDatasetExperimentResult
# =============================================================================
class TestMultiDatasetExperimentResult:
    """Tests for MultiDatasetExperimentResult dataclass."""

    def test_default_creation(self) -> None:
        """Test default MultiDatasetExperimentResult creation."""
        result = MultiDatasetExperimentResult(
            experiment_id="test-001",
            config={"name": "test"},
        )
        assert result.experiment_id == "test-001"
        assert result.dataset_results == {}
        assert result.aggregated_metrics == {}
        assert result.success is True

    def test_with_dataset_results(self) -> None:
        """Test MultiDatasetExperimentResult with dataset results."""
        nq_result = DatasetResult(dataset="nq")
        hotpot_result = DatasetResult(dataset="hotpotqa")

        result = MultiDatasetExperimentResult(
            experiment_id="test-002",
            config={"name": "test"},
            dataset_results={"nq": nq_result, "hotpotqa": hotpot_result},
        )
        assert len(result.dataset_results) == 2
        assert "nq" in result.dataset_results
        assert "hotpotqa" in result.dataset_results

    def test_to_dict(self) -> None:
        """Test MultiDatasetExperimentResult serialization."""
        result = MultiDatasetExperimentResult(
            experiment_id="test-003",
            config={"name": "test"},
            best_f1_algorithm="longrefiner",
        )
        d = result.to_dict()

        assert d["experiment_id"] == "test-003"
        assert "datasets" in d
        assert "aggregated" in d
        assert d["summary"]["best_f1_algorithm"] == "longrefiner"

    def test_to_experiment_result(self) -> None:
        """Test conversion to standard ExperimentResult."""
        metrics = AlgorithmMetrics(algorithm="baseline", avg_f1=0.70)
        result = MultiDatasetExperimentResult(
            experiment_id="test-004",
            config={"name": "test"},
            aggregated_metrics={"baseline": metrics},
            best_f1_algorithm="baseline",
        )

        exp_result = result.to_experiment_result()

        assert isinstance(exp_result, ExperimentResult)
        assert exp_result.experiment_id == "test-004"
        assert "baseline" in exp_result.algorithm_metrics
        assert exp_result.best_f1_algorithm == "baseline"


# =============================================================================
# Tests for ComparisonExperiment with multiple datasets
# =============================================================================
class TestComparisonExperimentMultiDataset:
    """Tests for ComparisonExperiment with multiple datasets."""

    def test_multi_dataset_experiment_creation(self) -> None:
        """Test creating experiment with multiple datasets."""
        config = RefinerExperimentConfig(
            name="multi_ds_test",
            datasets=["nq", "hotpotqa"],
            algorithms=["baseline"],
            max_samples=5,
        )
        exp = ComparisonExperiment(config)
        assert exp.config.datasets == ["nq", "hotpotqa"]

    def test_run_multiple_datasets(self) -> None:
        """Test running experiment on multiple datasets (with mocked pipeline)."""

        def mock_execute_pipeline(
            self: Any, algorithm: str, dataset: str = ""
        ) -> list[dict[str, Any]]:
            """Mock pipeline execution returning fake results."""
            return [
                {
                    "sample_id": f"{dataset}_{algorithm}_{i}",
                    "f1": 0.7 + i * 0.01,
                    "compression_rate": 2.5,
                    "total_time": 1.0,
                }
                for i in range(5)
            ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = RefinerExperimentConfig(
                name="multi_ds_run_test",
                datasets=["nq", "hotpotqa"],
                algorithms=["baseline", "longrefiner"],
                max_samples=5,
                output_dir=tmpdir,
                verbose=False,
            )
            exp = ComparisonExperiment(config)

            # Mock _execute_pipeline to avoid real Pipeline calls
            with patch.object(ComparisonExperiment, "_execute_pipeline", mock_execute_pipeline):
                result = exp.run_full()

            # Should succeed
            assert result.success is True

            # Should have metrics for all algorithms
            assert "baseline" in result.algorithm_metrics
            assert "longrefiner" in result.algorithm_metrics

            # Multi-dataset result should be stored
            assert exp.multi_dataset_result is not None
            assert "nq" in exp.multi_dataset_result.dataset_results
            assert "hotpotqa" in exp.multi_dataset_result.dataset_results

    def test_aggregated_metrics(self) -> None:
        """Test that aggregated metrics are computed correctly (with mocked pipeline)."""

        def mock_execute_pipeline(
            self: Any, algorithm: str, dataset: str = ""
        ) -> list[dict[str, Any]]:
            """Mock pipeline execution returning fake results."""
            return [
                {
                    "sample_id": f"{dataset}_{algorithm}_{i}",
                    "f1": 0.7,
                    "compression_rate": 2.5,
                    "total_time": 1.0,
                }
                for i in range(5)
            ]

        with tempfile.TemporaryDirectory() as tmpdir:
            config = RefinerExperimentConfig(
                name="aggregation_test",
                datasets=["nq", "hotpotqa"],
                algorithms=["baseline"],
                max_samples=5,
                output_dir=tmpdir,
                verbose=False,
            )
            exp = ComparisonExperiment(config)

            with patch.object(ComparisonExperiment, "_execute_pipeline", mock_execute_pipeline):
                exp.run_full()

            assert exp.multi_dataset_result is not None
            assert "baseline" in exp.multi_dataset_result.aggregated_metrics

            # Aggregated samples should be sum of individual datasets
            agg_samples = exp.multi_dataset_result.aggregated_metrics["baseline"].num_samples
            ds_samples = sum(
                ds.algorithm_metrics.get("baseline", AlgorithmMetrics(algorithm="")).num_samples
                for ds in exp.multi_dataset_result.dataset_results.values()
            )
            assert agg_samples == ds_samples


# =============================================================================
# Tests for RefinerExperimentRunner with multiple datasets
# =============================================================================
class TestRunnerMultiDataset:
    """Tests for RefinerExperimentRunner with multiple datasets."""

    @staticmethod
    def _mock_execute_pipeline(
        self: Any, algorithm: str, dataset: str = ""
    ) -> list[dict[str, Any]]:
        """Mock pipeline execution returning fake results."""
        return [
            {
                "sample_id": f"{dataset}_{algorithm}_{i}",
                "f1": 0.7,
                "compression_rate": 2.5,
                "total_time": 1.0,
            }
            for i in range(5)
        ]

    def test_quick_compare_single_dataset(self) -> None:
        """Test quick_compare with single dataset (backwards compatible)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = RefinerExperimentRunner(verbose=False)

            with patch.object(
                ComparisonExperiment,
                "_execute_pipeline",
                TestRunnerMultiDataset._mock_execute_pipeline,
            ):
                result = runner.quick_compare(
                    algorithms=["baseline"],
                    datasets=["nq"],
                    max_samples=5,
                    output_dir=tmpdir,
                )
            assert result.success is True

    def test_quick_compare_multiple_datasets(self) -> None:
        """Test quick_compare with multiple datasets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = RefinerExperimentRunner(verbose=False)

            with patch.object(
                ComparisonExperiment,
                "_execute_pipeline",
                TestRunnerMultiDataset._mock_execute_pipeline,
            ):
                result = runner.quick_compare(
                    algorithms=["baseline", "longrefiner"],
                    datasets=["nq", "hotpotqa"],
                    max_samples=5,
                    output_dir=tmpdir,
                )
            assert result.success is True
            # Check that config includes datasets
            assert result.config.get("datasets") == ["nq", "hotpotqa"]

    def test_quick_compare_backwards_compatible_dataset(self) -> None:
        """Test quick_compare with old 'dataset' parameter still works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = RefinerExperimentRunner(verbose=False)

            with patch.object(
                ComparisonExperiment,
                "_execute_pipeline",
                TestRunnerMultiDataset._mock_execute_pipeline,
            ):
                # Using old 'dataset' parameter
                result = runner.quick_compare(
                    algorithms=["baseline"],
                    dataset="hotpotqa",  # Old parameter
                    max_samples=5,
                    output_dir=tmpdir,
                )
            assert result.success is True


# =============================================================================
# Tests for CLI --datasets argument
# =============================================================================
class TestCLIDatasets:
    """Tests for CLI --datasets argument parsing."""

    def test_parse_single_dataset(self) -> None:
        """Test parsing single dataset from CLI."""
        datasets_arg = "nq"
        datasets = [d.strip() for d in datasets_arg.split(",")]
        assert datasets == ["nq"]

    def test_parse_multiple_datasets(self) -> None:
        """Test parsing multiple datasets from CLI."""
        datasets_arg = "nq,hotpotqa,2wikimultihopqa"
        datasets = [d.strip() for d in datasets_arg.split(",")]
        assert datasets == ["nq", "hotpotqa", "2wikimultihopqa"]

    def test_parse_datasets_with_spaces(self) -> None:
        """Test parsing datasets with spaces around commas."""
        datasets_arg = "nq , hotpotqa , triviaqa"
        datasets = [d.strip() for d in datasets_arg.split(",")]
        assert datasets == ["nq", "hotpotqa", "triviaqa"]

    def test_validate_datasets_all_valid(self) -> None:
        """Test validation with all valid datasets."""
        datasets = ["nq", "hotpotqa", "triviaqa"]
        invalid = [d for d in datasets if d not in AVAILABLE_DATASETS]
        assert invalid == []

    def test_validate_datasets_some_invalid(self) -> None:
        """Test validation with some invalid datasets."""
        datasets = ["nq", "unknown_dataset", "hotpotqa"]
        invalid = [d for d in datasets if d not in AVAILABLE_DATASETS]
        assert "unknown_dataset" in invalid

    def test_all_keyword_expansion(self) -> None:
        """Test 'all' keyword expands to all available datasets."""
        datasets_arg = "all"
        if datasets_arg == "all":
            datasets = AVAILABLE_DATASETS.copy()
        else:
            datasets = [d.strip() for d in datasets_arg.split(",")]

        assert len(datasets) == len(AVAILABLE_DATASETS)
        assert "nq" in datasets
        assert "hotpotqa" in datasets
