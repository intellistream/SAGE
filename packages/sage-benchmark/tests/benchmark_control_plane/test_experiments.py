# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Unit tests for the experiments module.

Tests cover:
- BaseExperiment and ExperimentResult
- ThroughputExperiment
- LatencyExperiment
- SLOComplianceExperiment
- MixedRatioExperiment
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from sage.benchmark.benchmark_control_plane.common import ArrivalPattern, SchedulingPolicy
from sage.benchmark.benchmark_control_plane.experiments import (
    DEFAULT_LLM_RATIOS,
    DEFAULT_LOAD_LEVELS,
    DEFAULT_PERCENTILES,
    DEFAULT_REQUEST_RATES,
    ExperimentResult,
    LatencyExperiment,
    MixedRatioExperiment,
    SLOComplianceExperiment,
    ThroughputExperiment,
)


# =============================================================================
# Tests for ExperimentResult
# =============================================================================
class TestExperimentResult:
    """Tests for ExperimentResult dataclass."""

    def test_default_result(self) -> None:
        """Test default result creation."""
        result = ExperimentResult(
            experiment_name="test",
            experiment_type="throughput",
        )
        assert result.experiment_name == "test"
        assert result.experiment_type == "throughput"
        assert result.results == []
        assert result.summary == {}
        assert result.charts == []

    def test_result_with_data(self) -> None:
        """Test result with data."""
        result = ExperimentResult(
            experiment_name="test",
            experiment_type="latency",
            results=[{"policy": "fifo", "latency": 100}],
            summary={"best": "fifo"},
            charts=[Path("/path/to/chart.png")],
        )
        assert len(result.results) == 1
        assert result.summary["best"] == "fifo"
        assert len(result.charts) == 1

    def test_result_to_dict(self) -> None:
        """Test result serialization."""
        result = ExperimentResult(
            experiment_name="test",
            experiment_type="throughput",
            parameters={"rate": 100},
            results=[{"data": "value"}],
            summary={"key": "value"},
        )
        d = result.to_dict()

        assert d["experiment_name"] == "test"
        assert d["experiment_type"] == "throughput"
        assert d["parameters"]["rate"] == 100
        assert d["results"] == [{"data": "value"}]
        assert d["summary"]["key"] == "value"
        assert "start_time" in d
        assert "end_time" in d
        assert "charts" in d


# =============================================================================
# Tests for ThroughputExperiment
# =============================================================================
class TestThroughputExperiment:
    """Tests for ThroughputExperiment class."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        exp = ThroughputExperiment(name="test_throughput")

        assert exp.name == "test_throughput"
        assert exp.request_rates == DEFAULT_REQUEST_RATES
        assert exp.num_requests == 500
        assert exp.llm_ratio == 0.5
        assert len(exp.policies) == len(list(SchedulingPolicy))

    def test_custom_initialization(self) -> None:
        """Test custom initialization."""
        exp = ThroughputExperiment(
            name="custom_throughput",
            control_plane_url="http://custom:9000",
            request_rates=[10, 20, 30],
            num_requests=100,
            llm_ratio=0.7,
            policies=[SchedulingPolicy.FIFO, SchedulingPolicy.PRIORITY],
            arrival_pattern=ArrivalPattern.UNIFORM,
        )

        assert exp.control_plane_url == "http://custom:9000"
        assert exp.request_rates == [10, 20, 30]
        assert exp.num_requests == 100
        assert exp.llm_ratio == 0.7
        assert len(exp.policies) == 2
        assert exp.arrival_pattern == ArrivalPattern.UNIFORM

    def test_experiment_type(self) -> None:
        """Test experiment type property."""
        exp = ThroughputExperiment(name="test")
        assert exp.experiment_type == "throughput"

    def test_get_parameters(self) -> None:
        """Test getting experiment parameters."""
        exp = ThroughputExperiment(
            name="test",
            request_rates=[100, 200],
            num_requests=1000,
        )
        params = exp._get_parameters()

        assert params["request_rates"] == [100, 200]
        assert params["num_requests"] == 1000
        assert "policies" in params

    def test_prepare_creates_runners(self) -> None:
        """Test prepare creates runners for each rate."""
        exp = ThroughputExperiment(
            name="test",
            request_rates=[50, 100, 200],
        )
        exp._prepare_impl()

        assert len(exp._runners) == 3
        assert 50 in exp._runners
        assert 100 in exp._runners
        assert 200 in exp._runners

    def test_compute_summary(self) -> None:
        """Test summary computation."""
        exp = ThroughputExperiment(
            name="test",
            policies=[SchedulingPolicy.FIFO, SchedulingPolicy.PRIORITY],
        )

        results = [
            {
                "request_rate": 100,
                "policies": {
                    "fifo": {"throughput": 95.0},
                    "priority": {"throughput": 92.0},
                },
            },
            {
                "request_rate": 200,
                "policies": {
                    "fifo": {"throughput": 180.0},
                    "priority": {"throughput": 185.0},
                },
            },
        ]

        summary = exp._compute_summary(results)

        assert "policies" in summary
        assert "fifo" in summary["policies"]
        assert "priority" in summary["policies"]
        assert summary["policies"]["fifo"]["max_throughput"] == 180.0
        assert summary["policies"]["priority"]["max_throughput"] == 185.0


# =============================================================================
# Tests for LatencyExperiment
# =============================================================================
class TestLatencyExperiment:
    """Tests for LatencyExperiment class."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        exp = LatencyExperiment(name="test_latency")

        assert exp.name == "test_latency"
        assert exp.request_rate == 100
        assert exp.num_requests == 1000
        assert exp.percentiles == DEFAULT_PERCENTILES

    def test_custom_initialization(self) -> None:
        """Test custom initialization."""
        exp = LatencyExperiment(
            name="custom_latency",
            request_rate=50,
            num_requests=500,
            percentiles=[50, 95, 99],
        )

        assert exp.request_rate == 50
        assert exp.num_requests == 500
        assert exp.percentiles == [50, 95, 99]

    def test_experiment_type(self) -> None:
        """Test experiment type property."""
        exp = LatencyExperiment(name="test")
        assert exp.experiment_type == "latency"

    def test_compute_percentiles(self) -> None:
        """Test percentile computation."""
        exp = LatencyExperiment(name="test", percentiles=[50, 90, 99])

        latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        percentiles = exp._compute_percentiles(latencies)

        assert "p50" in percentiles
        assert "p90" in percentiles
        assert "p99" in percentiles

    def test_compute_percentiles_empty(self) -> None:
        """Test percentile computation with empty list."""
        exp = LatencyExperiment(name="test")
        percentiles = exp._compute_percentiles([])

        assert all(v == 0.0 for v in percentiles.values())

    def test_compute_std_dev(self) -> None:
        """Test standard deviation computation."""
        exp = LatencyExperiment(name="test")

        latencies = [100.0, 100.0, 100.0, 100.0]
        std_dev = exp._compute_std_dev(latencies)
        assert std_dev == 0.0

        latencies = [90.0, 100.0, 110.0]
        std_dev = exp._compute_std_dev(latencies)
        assert std_dev > 0

    def test_compute_std_dev_insufficient_data(self) -> None:
        """Test standard deviation with insufficient data."""
        exp = LatencyExperiment(name="test")

        assert exp._compute_std_dev([]) == 0.0
        assert exp._compute_std_dev([100.0]) == 0.0


# =============================================================================
# Tests for SLOComplianceExperiment
# =============================================================================
class TestSLOComplianceExperiment:
    """Tests for SLOComplianceExperiment class."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        exp = SLOComplianceExperiment(name="test_slo")

        assert exp.name == "test_slo"
        assert exp.load_levels == DEFAULT_LOAD_LEVELS
        assert exp.num_requests == 500

    def test_custom_initialization(self) -> None:
        """Test custom initialization."""
        exp = SLOComplianceExperiment(
            name="custom_slo",
            load_levels=[25, 50, 75],
            num_requests=200,
        )

        assert exp.load_levels == [25, 50, 75]
        assert exp.num_requests == 200

    def test_experiment_type(self) -> None:
        """Test experiment type property."""
        exp = SLOComplianceExperiment(name="test")
        assert exp.experiment_type == "slo_compliance"

    def test_prepare_creates_runners(self) -> None:
        """Test prepare creates runners for each load level."""
        exp = SLOComplianceExperiment(
            name="test",
            load_levels=[50, 100, 200],
        )
        exp._prepare_impl()

        assert len(exp._runners) == 3
        assert 50 in exp._runners
        assert 100 in exp._runners
        assert 200 in exp._runners

    def test_compute_slo_stats_empty(self) -> None:
        """Test SLO stats computation with empty results."""
        exp = SLOComplianceExperiment(name="test")

        stats = exp._compute_slo_stats([], MagicMock())

        assert stats["overall_compliance"] == 0.0
        assert stats["violation_count"] == 0
        assert stats["total_requests"] == 0


# =============================================================================
# Tests for MixedRatioExperiment
# =============================================================================
class TestMixedRatioExperiment:
    """Tests for MixedRatioExperiment class."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        exp = MixedRatioExperiment(name="test_mixed")

        assert exp.name == "test_mixed"
        assert exp.llm_ratios == DEFAULT_LLM_RATIOS
        assert exp.request_rate == 100

    def test_custom_initialization(self) -> None:
        """Test custom initialization."""
        exp = MixedRatioExperiment(
            name="custom_mixed",
            llm_ratios=[0.0, 0.5, 1.0],
            request_rate=50,
        )

        assert exp.llm_ratios == [0.0, 0.5, 1.0]
        assert exp.request_rate == 50

    def test_experiment_type(self) -> None:
        """Test experiment type property."""
        exp = MixedRatioExperiment(name="test")
        assert exp.experiment_type == "mixed_ratio"

    def test_prepare_creates_runners(self) -> None:
        """Test prepare creates runners for each ratio."""
        exp = MixedRatioExperiment(
            name="test",
            llm_ratios=[0.0, 0.5, 1.0],
        )
        exp._prepare_impl()

        assert len(exp._runners) == 3
        assert 0.0 in exp._runners
        assert 0.5 in exp._runners
        assert 1.0 in exp._runners

    def test_compute_type_stats_empty(self) -> None:
        """Test type stats computation with empty results."""
        exp = MixedRatioExperiment(name="test")

        llm_stats, emb_stats = exp._compute_type_stats([])

        assert llm_stats["count"] == 0
        assert emb_stats["count"] == 0

    def test_compute_slo_compliance_empty(self) -> None:
        """Test SLO compliance computation with empty results."""
        exp = MixedRatioExperiment(name="test")

        compliance = exp._compute_slo_compliance([])

        assert compliance == 0.0


# =============================================================================
# Tests for BaseExperiment (abstract class tests via concrete classes)
# =============================================================================
class TestBaseExperimentLifecycle:
    """Tests for BaseExperiment lifecycle methods."""

    def test_prepare_sets_state(self) -> None:
        """Test prepare sets correct state."""
        exp = ThroughputExperiment(name="test")
        exp.prepare()

        assert exp._prepared is True

    def test_finalize_saves_result(self) -> None:
        """Test finalize saves result to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp = ThroughputExperiment(name="test", output_dir=tmpdir)
            exp._result = ExperimentResult(
                experiment_name="test",
                experiment_type="throughput",
                results=[{"data": "value"}],
            )

            exp.finalize()

            result_file = Path(tmpdir) / "test_result.json"
            assert result_file.exists()

    def test_output_dir_creation(self) -> None:
        """Test output directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "experiments" / "results"
            exp = ThroughputExperiment(name="test", output_dir=output_dir)

            assert exp.output_dir == output_dir
            # Directory created on first use

    def test_verbose_logging(self) -> None:
        """Test verbose logging can be disabled."""
        exp = ThroughputExperiment(name="test", verbose=False)
        assert exp.verbose is False

        exp = ThroughputExperiment(name="test", verbose=True)
        assert exp.verbose is True


# =============================================================================
# Tests for default constants
# =============================================================================
class TestExperimentConstants:
    """Tests for experiment default constants."""

    def test_default_request_rates(self) -> None:
        """Test default request rates."""
        assert DEFAULT_REQUEST_RATES == [50, 100, 200, 500, 1000]

    def test_default_percentiles(self) -> None:
        """Test default percentiles."""
        assert DEFAULT_PERCENTILES == [50, 90, 95, 99, 99.9]

    def test_default_load_levels(self) -> None:
        """Test default load levels."""
        assert DEFAULT_LOAD_LEVELS == [50, 100, 200, 500]

    def test_default_llm_ratios(self) -> None:
        """Test default LLM ratios."""
        assert DEFAULT_LLM_RATIOS == [0.0, 0.25, 0.5, 0.75, 1.0]
